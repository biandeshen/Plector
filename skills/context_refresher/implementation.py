"""GSD 上下文保鲜技能实现

问题：长对话 AI 遗忘初始目标
机制：
1. 对话轮次 % N（N=10）触发"保鲜"
2. LLM 提取 {goal, constraints, completed[], in_progress[]}
3. 存入 vector_memory 单独 collection: "context_saver"
4. 新消息注入时拼接 {保鲜上下文 + 最近 5 轮} 而非全量历史
5. 初始目标变化时（用户明确修改）触发"重锚定"
"""

import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from core.vector_memory import VectorMemory


@dataclass
class GSDContext:
    """GSD 上下文结构"""
    session_id: str
    goal: str = ""
    constraints: List[str] = field(default_factory=list)
    completed: List[str] = field(default_factory=list)
    in_progress: List[str] = field(default_factory=list)
    turn_count: int = 0
    last_refresh: float = 0.0
    goal_version: int = 1


class ContextRefresher:
    """GSD 上下文保鲜器"""
    
    REFRESH_INTERVAL = 10
    MAX_RECENT_TURNS = 5
    
    def __init__(self, vector_memory: Optional[VectorMemory] = None):
        self.vm = vector_memory or VectorMemory()
        self._cache: Dict[str, GSDContext] = {}
    
    def should_refresh(self, turn_count: int) -> bool:
        """判断是否需要触发保鲜"""
        return turn_count > 0 and turn_count % self.REFRESH_INTERVAL == 0
    
    def preserve(
        self,
        session_id: str,
        conversation_history: List[Dict],
        current_goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """保鲜：从对话历史提取并存储 GSD 上下文"""
        try:
            ctx = self._cache.get(session_id) or GSDContext(
                session_id=session_id,
                goal=current_goal or "未定义目标"
            )
            
            if conversation_history:
                extracted = self._extract_from_history(conversation_history[-20:])
                if extracted:
                    ctx.goal = extracted.get("goal", ctx.goal)
                    ctx.constraints = extracted.get("constraints", [])
                    ctx.completed = extracted.get("completed", [])
                    ctx.in_progress = extracted.get("in_progress", [])
            
            ctx.turn_count = len(conversation_history)
            ctx.last_refresh = time.time()
            
            doc_id = f"context_{session_id}_{int(ctx.last_refresh)}"
            self.vm.context_saver.add(
                ids=[doc_id],
                documents=[json.dumps(asdict(ctx), ensure_ascii=False)],
                metadatas=[{
                    "session_id": session_id,
                    "type": "gsd_context",
                    "version": ctx.goal_version
                }]
            )
            
            self._cache[session_id] = ctx
            return {
                "success": True,
                "data": {"context_id": doc_id, "turn_count": ctx.turn_count},
                "error": None
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """获取最新保鲜上下文"""
        try:
            if session_id in self._cache:
                return {
                    "success": True,
                    "data": asdict(self._cache[session_id]),
                    "error": None
                }
            
            results = self.vm.context_saver.get(
                where={"session_id": session_id}
            )
            
            if results and results.get("documents"):
                ctx_data = json.loads(results["documents"][-1])
                self._cache[session_id] = GSDContext(**ctx_data)
                return {"success": True, "data": ctx_data, "error": None}
            
            return {"success": False, "data": None, "error": "上下文未找到"}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
    
    def re_anchor(
        self,
        session_id: str,
        new_goal: str,
        new_constraints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """重锚定：用户明确修改目标时触发"""
        try:
            ctx = self._cache.get(session_id)
            if ctx:
                ctx.goal = new_goal
                ctx.constraints = new_constraints or []
                ctx.goal_version += 1
                ctx.completed = []
                ctx.in_progress = []
            else:
                ctx = GSDContext(
                    session_id=session_id,
                    goal=new_goal,
                    constraints=new_constraints or []
                )
            
            doc_id = f"context_{session_id}_{int(time.time())}"
            self.vm.context_saver.add(
                ids=[doc_id],
                documents=[json.dumps(asdict(ctx), ensure_ascii=False)],
                metadatas=[{
                    "session_id": session_id,
                    "type": "gsd_context",
                    "version": ctx.goal_version
                }]
            )
            
            self._cache[session_id] = ctx
            return {"success": True, "data": {"goal_version": ctx.goal_version}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
    
    def inject_context(self, session_id: str, recent_turns: List[Dict]) -> str:
        """注入上下文：拼接保鲜上下文 + 最近 N 轮"""
        result = self.get_context(session_id)
        
        if not result["success"]:
            return self._format_recent_only(recent_turns)
        
        ctx = result["data"]
        parts = [
            "=== GSD 上下文保鲜 ===",
            f"当前目标（v{ctx['goal_version']}）：{ctx['goal']}",
            f"约束条件：{', '.join(ctx['constraints']) or '无'}",
            f"已完成：{', '.join(ctx['completed']) or '无'}",
            f"进行中：{', '.join(ctx['in_progress']) or '无'}",
            "=== 最近对话 ==="
        ]
        
        for turn in recent_turns[-self.MAX_RECENT_TURNS:]:
            role = "用户" if turn.get("role") == "user" else "助手"
            parts.append(f"[{role}] {turn.get('content', '')[:200]}")
        
        return "\n".join(parts)
    
    def _extract_from_history(self, history: List[Dict]) -> Optional[Dict]:
        """
        从对话历史提取 GSD 上下文
        策略：
        1. 首条用户消息 → goal
        2. 检测约束关键词（不要、必须、只能等）
        3. 分析完成状态（完成了、成功了等）
        4. 检测进行中任务（正在做、处理中等）
        """
        if not history:
            return None
        
        result = {
            "goal": "",
            "constraints": [],
            "completed": [],
            "in_progress": []
        }
        
        # 1. 提取目标（首条用户消息）
        for turn in history:
            if turn.get("role") == "user":
                content = turn.get("content", "")[:500]
                result["goal"] = content
                result["constraints"] = self._extract_constraints(content)
                break
        
        # 2. 分析完成和进行中的任务
        for turn in history:
            content = turn.get("content", "")
            role = turn.get("role", "")
            
            # 检测完成状态
            if any(kw in content for kw in ["完成了", "成功了", "已创建", "已删除", "已修复"]):
                milestone = self._extract_milestone(content, "completed")
                if milestone and milestone not in result["completed"]:
                    result["completed"].append(milestone)
            
            # 检测进行中
            if any(kw in content for kw in ["正在做", "处理中", "执行中", "准备", "开始"]):
                milestone = self._extract_milestone(content, "in_progress")
                if milestone and milestone not in result["in_progress"]:
                    result["in_progress"].append(milestone)
        
        # 如果没有提取到任何内容，返回 None
        if not result["goal"] and not result["completed"] and not result["in_progress"]:
            return None
        
        return result
    
    def _extract_constraints(self, text: str) -> List[str]:
        """提取约束条件"""
        constraints = []
        patterns = [
            r"不要[^\n，。！？，。！？]+",
            r"必须[^\n，。！？，。！？]+",
            r"只能[^\n，。！？，。！？]+",
            r"禁止[^\n，。！？，。！？]+",
            r"不能[^\n，。！？，。！？]+",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            constraints.extend([m[:100] for m in matches])
        return list(set(constraints))[:5]
    
    def _extract_milestone(self, text: str, mtype: str) -> Optional[str]:
        """提取里程碑"""
        keywords = {
            "completed": ["完成了", "成功了", "已创建", "已删除", "已修复", "已添加", "已配置"],
            "in_progress": ["正在做", "处理中", "执行中", "准备", "开始", "正在"]
        }
        
        for kw in keywords.get(mtype, []):
            if kw in text:
                idx = text.index(kw)
                start = max(0, idx - 20)
                end = min(len(text), idx + 50)
                snippet = text[start:end].replace("\n", " ").strip()
                return snippet if len(snippet) > 5 else None
        return None
    
    def _format_recent_only(self, recent_turns: List[Dict]) -> str:
        """仅格式化最近对话"""
        parts = ["=== 最近对话 ==="]
        for turn in recent_turns[-self.MAX_RECENT_TURNS:]:
            role = "用户" if turn.get("role") == "user" else "助手"
            parts.append(f"[{role}] {turn.get('content', '')[:200]}")
        return "\n".join(parts)


# === 导出工具函数 ===

_refresher: Optional[ContextRefresher] = None


def _get_refresher() -> ContextRefresher:
    """获取单例"""
    global _refresher
    if _refresher is None:
        _refresher = ContextRefresher()
    return _refresher


def preserve_context(
    session_id: str,
    conversation_history: List[Dict],
    current_goal: Optional[str] = None
) -> Dict[str, Any]:
    """工具：保鲜上下文"""
    return _get_refresher().preserve(session_id, conversation_history, current_goal)


def get_gsd_context(session_id: str) -> Dict[str, Any]:
    """工具：获取保鲜上下文"""
    return _get_refresher().get_context(session_id)


def re_anchor_context(
    session_id: str,
    new_goal: str,
    new_constraints: Optional[List[str]] = None
) -> Dict[str, Any]:
    """工具：重锚定上下文"""
    return _get_refresher().re_anchor(session_id, new_goal, new_constraints)


def inject_gsd_context(session_id: str, recent_turns: List[Dict]) -> str:
    """工具：注入上下文"""
    return _get_refresher().inject_context(session_id, recent_turns)
