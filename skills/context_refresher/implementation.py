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
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class GSDContext:
    """GSD 上下文结构"""
    session_id: str
    goal: str                    # 初始目标
    constraints: List[str]      # 约束条件
    completed: List[str]        # 已完成项
    in_progress: List[str]      # 进行中项
    turn_count: int             # 对话轮次
    last_refresh: float         # 上次保鲜时间戳
    goal_version: int           # 目标版本（重锚定时+1）


class ContextRefresher:
    """GSD 上下文保鲜器"""
    
    REFRESH_INTERVAL = 10  # 每 N 轮触发一次保鲜
    MAX_RECENT_TURNS = 5   # 注入时保留最近 N 轮
    
    def __init__(self, vector_memory, llm_client=None):
        self.vector_memory = vector_memory
        self.llm_client = llm_client
        self._context_cache: Dict[str, GSDContext] = {}
    
    def should_refresh(self, session_id: str, turn_count: int) -> bool:
        """判断是否需要触发保鲜"""
        return turn_count > 0 and turn_count % self.REFRESH_INTERVAL == 0
    
    def preserve(self, session_id: str, conversation_history: List[Dict], 
                 current_goal: Optional[str] = None) -> Dict[str, Any]:
        """保鲜：提取并存储上下文
        
        Args:
            session_id: 会话 ID
            conversation_history: 对话历史 [{"role": "user/assistant", "content": str}]
            current_goal: 可选的当前目标
            
        Returns:
            {"success": bool, "data": {"context_id": str}, "error": str}
        """
        try:
            # 1. 从缓存或创建上下文
            ctx = self._context_cache.get(session_id)
            if not ctx:
                ctx = GSDContext(
                    session_id=session_id,
                    goal=current_goal or "未定义目标",
                    constraints=[],
                    completed=[],
                    in_progress=[],
                    turn_count=0,
                    last_refresh=time.time(),
                    goal_version=1
                )
            
            # 2. LLM 提取结构化上下文（如果可用 LLM）
            if self.llm_client and len(conversation_history) > 0:
                extracted = self._extract_context_llm(conversation_history)
                if extracted:
                    ctx.goal = extracted.get("goal", ctx.goal)
                    ctx.constraints = extracted.get("constraints", [])
                    ctx.completed = extracted.get("completed", [])
                    ctx.in_progress = extracted.get("in_progress", [])
            
            ctx.turn_count = len(conversation_history)
            ctx.last_refresh = time.time()
            
            # 3. 存储到 vector_memory 单独 collection
            doc_id = f"context_{session_id}_{int(ctx.last_refresh)}"
            self.vector_memory.add(
                collection="context_saver",
                document_id=doc_id,
                content=json.dumps(asdict(ctx), ensure_ascii=False),
                metadata={"session_id": session_id, "type": "gsd_context"}
            )
            
            self._context_cache[session_id] = ctx
            
            return {
                "success": True,
                "data": {"context_id": doc_id, "turn_count": ctx.turn_count},
                "error": None
            }
            
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """获取最新保鲜上下文
        
        Returns:
            {"success": bool, "data": GSDContext, "error": str}
        """
        try:
            # 优先从缓存
            if session_id in self._context_cache:
                return {
                    "success": True,
                    "data": asdict(self._context_cache[session_id]),
                    "error": None
                }
            
            # 从 vector_memory 加载
            results = self.vector_memory.search(
                collection="context_saver",
                query=session_id,
                top_k=1
            )
            
            if results:
                ctx_data = json.loads(results[0]["content"])
                return {"success": True, "data": ctx_data, "error": None}
            
            return {"success": False, "data": None, "error": "上下文未找到"}
            
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
    
    def re_anchor(self, session_id: str, new_goal: str, 
                  new_constraints: Optional[List[str]] = None) -> Dict[str, Any]:
        """重锚定：用户明确修改目标时触发
        
        Args:
            session_id: 会话 ID
            new_goal: 新的目标
            new_constraints: 新的约束条件
            
        Returns:
            {"success": bool, "data": {"goal_version": int}, "error": str}
        """
        try:
            ctx = self._context_cache.get(session_id)
            if ctx:
                ctx.goal = new_goal
                ctx.constraints = new_constraints or []
                ctx.goal_version += 1
                ctx.completed = []  # 重置已完成项
                ctx.in_progress = []
                
                # 保存新版本
                doc_id = f"context_{session_id}_{int(time.time())}"
                self.vector_memory.add(
                    collection="context_saver",
                    document_id=doc_id,
                    content=json.dumps(asdict(ctx), ensure_ascii=False),
                    metadata={"session_id": session_id, "type": "gsd_context", 
                             "version": ctx.goal_version}
                )
            else:
                ctx = GSDContext(
                    session_id=session_id,
                    goal=new_goal,
                    constraints=new_constraints or [],
                    completed=[],
                    in_progress=[],
                    turn_count=0,
                    last_refresh=time.time(),
                    goal_version=1
                )
                self._context_cache[session_id] = ctx
            
            return {
                "success": True,
                "data": {"goal_version": ctx.goal_version},
                "error": None
            }
            
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
    
    def inject_context(self, session_id: str, 
                       recent_turns: List[Dict]) -> str:
        """注入上下文：拼接保鲜上下文 + 最近 N 轮
        
        Args:
            session_id: 会话 ID
            recent_turns: 最近 N 轮对话 [{"role": "user/assistant", "content": str}]
            
        Returns:
            拼接后的上下文字符串
        """
        gsd_ctx = self.get_context(session_id)
        
        if not gsd_ctx["success"]:
            return self._format_recent_only(recent_turns)
        
        ctx_data = gsd_ctx["data"]
        
        # 构建保鲜上下文
        context_parts = [
            "=== GSD 上下文保鲜 ===",
            f"当前目标（v{ctx_data['goal_version']}）：{ctx_data['goal']}",
            f"约束条件：{', '.join(ctx_data['constraints']) if ctx_data['constraints'] else '无'}",
            f"已完成：{', '.join(ctx_data['completed']) if ctx_data['completed'] else '无'}",
            f"进行中：{', '.join(ctx_data['in_progress']) if ctx_data['in_progress'] else '无'}",
            "=== 最近对话 ==="
        ]
        
        # 追加最近 N 轮
        for turn in recent_turns[-self.MAX_RECENT_TURNS:]:
            role = "用户" if turn.get("role") == "user" else "助手"
            context_parts.append(f"[{role}] {turn.get('content', '')[:200]}")
        
        return "\n".join(context_parts)
    
    def _extract_context_llm(self, history: List[Dict]) -> Optional[Dict]:
        """使用 LLM 提取结构化上下文"""
        if not self.llm_client:
            return None
        
        try:
            # 构建提取 prompt
            recent = history[-20:]  # 取最近 20 轮
            prompt = f"""从以下对话历史中提取 GSD 上下文：
{f json.dumps(recent, ensure_ascii=False, indent=2)}

请提取：
- goal: 用户的核心目标
- constraints: 约束条件列表
- completed: 已完成的工作
- in_progress: 正在进行的工作

返回 JSON 格式。"""
            
            response = self.llm_client.complete(prompt)
            return json.loads(response)
            
        except Exception:
            return None
    
    def _format_recent_only(self, recent_turns: List[Dict]) -> str:
        """仅格式化最近对话（无保鲜上下文时）"""
        parts = ["=== 最近对话 ==="]
        for turn in recent_turns[-self.MAX_RECENT_TURNS:]:
            role = "用户" if turn.get("role") == "user" else "助手"
            parts.append(f"[{role}] {turn.get('content', '')[:200]}")
        return "\n".join(parts)


# === 导出工具函数 ===

def preserve_context(session_id: str, conversation_history: List[Dict],
                     current_goal: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：保鲜上下文"""
    refresher = ContextRefresher(
        vector_memory=_get_vector_memory(),
        llm_client=_get_llm_client()
    )
    return refresher.preserve(session_id, conversation_history, current_goal)


def get_gsd_context(session_id: str) -> Dict[str, Any]:
    """便捷函数：获取保鲜上下文"""
    refresher = ContextRefresher(vector_memory=_get_vector_memory())
    return refresher.get_context(session_id)


def re_anchor_context(session_id: str, new_goal: str,
                      new_constraints: Optional[List[str]] = None) -> Dict[str, Any]:
    """便捷函数：重锚定上下文"""
    refresher = ContextRefresher(vector_memory=_get_vector_memory())
    return refresher.re_anchor(session_id, new_goal, new_constraints)


def inject_gsd_context(session_id: str, recent_turns: List[Dict]) -> str:
    """便捷函数：注入上下文"""
    refresher = ContextRefresher(vector_memory=_get_vector_memory())
    return refresher.inject_context(session_id, recent_turns)


# === 内部依赖注入（实际使用时由 core 注入） ===

_vector_memory = None
_llm_client = None

def _get_vector_memory():
    global _vector_memory
    if _vector_memory is None:
        from core.memory import VectorMemory
        _vector_memory = VectorMemory()
    return _vector_memory

def _get_llm_client():
    global _llm_client
    if _llm_client is None:
        from core.llm_client import get_llm_client
        _llm_client = get_llm_client()
    return _llm_client

def set_dependencies(vector_memory, llm_client=None):
    """设置依赖（用于测试或外部注入）"""
    global _vector_memory, _llm_client
    _vector_memory = vector_memory
    _llm_client = llm_client
