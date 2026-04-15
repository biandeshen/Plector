"""context_refresher 技能单元测试"""

import pytest
from unittest.mock import MagicMock, patch
from skills.context_refresher.implementation import (
    ContextRefresher,
    GSDContext,
)


class TestGSDContextExtraction:
    """测试 GSD 上下文提取"""
    
    def setup_method(self):
        """每个测试前创建 mock"""
        self.mock_vm = MagicMock()
        self.refresher = ContextRefresher(vector_memory=self.mock_vm)
    
    def test_extract_goal_from_first_user_message(self):
        """测试从首条用户消息提取目标"""
        history = [
            {"role": "user", "content": "帮我实现一个用户注册功能"},
            {"role": "assistant", "content": "好的，我来帮你实现"},
        ]
        
        result = self.refresher._extract_from_history(history)
        
        assert result is not None
        assert "用户注册功能" in result["goal"]
    
    def test_extract_constraints_from_text(self):
        """测试约束条件提取"""
        text = "帮我实现功能，但不要使用第三方库，必须使用原生 Python"
        
        constraints = self.refresher._extract_constraints(text)
        
        assert len(constraints) >= 1
        assert any("第三方库" in c for c in constraints)
    
    def test_extract_completed_milestone(self):
        """测试完成状态检测"""
        text = "用户注册功能完成了，现在开始做登录功能"
        
        milestone = self.refresher._extract_milestone(text, "completed")
        
        assert milestone is not None
        assert "注册功能" in milestone or "完成了" in milestone
    
    def test_extract_in_progress_milestone(self):
        """测试进行中状态检测"""
        text = "正在做登录功能的实现"
        
        milestone = self.refresher._extract_milestone(text, "in_progress")
        
        assert milestone is not None
    
    def test_empty_history_returns_none(self):
        """测试空历史返回 None"""
        result = self.refresher._extract_from_history([])
        
        assert result is None


class TestContextRefresher:
    """测试上下文保鲜器"""
    
    def setup_method(self):
        self.mock_vm = MagicMock()
        self.refresher = ContextRefresher(vector_memory=self.mock_vm)
    
    def test_should_refresh_at_interval(self):
        """测试刷新触发条件"""
        assert self.refresher.should_refresh(10) is True
        assert self.refresher.should_refresh(20) is True
        assert self.refresher.should_refresh(5) is False
        assert self.refresher.should_refresh(0) is False
    
    def test_preserve_creates_context(self):
        """测试保鲜创建上下文"""
        history = [
            {"role": "user", "content": "帮我实现功能"},
            {"role": "assistant", "content": "好的"},
        ]
        
        result = self.refresher.preserve("session1", history)
        
        assert result["success"] is True
        assert result["data"]["turn_count"] == 2
        self.mock_vm.context_saver.add.assert_called_once()
    
    def test_preserve_extracts_goal(self):
        """测试保鲜提取目标"""
        history = [
            {"role": "user", "content": "这是一个重要任务"},
        ]
        
        self.refresher.preserve("session1", history)
        
        # 验证目标被提取
        cached = self.refresher._cache.get("session1")
        assert cached is not None
        assert "重要任务" in cached.goal
    
    def test_re_anchor_updates_goal_version(self):
        """测试重锚定更新版本"""
        # 先创建上下文
        self.refresher._cache["session1"] = GSDContext(
            session_id="session1",
            goal="旧目标",
            goal_version=1
        )
        
        result = self.refresher.re_anchor("session1", "新目标")
        
        assert result["success"] is True
        assert result["data"]["goal_version"] == 2
        assert self.refresher._cache["session1"].goal == "新目标"
    
    def test_get_context_from_cache(self):
        """测试从缓存获取上下文"""
        ctx = GSDContext(session_id="session1", goal="测试目标")
        self.refresher._cache["session1"] = ctx
        
        result = self.refresher.get_context("session1")
        
        assert result["success"] is True
        assert result["data"]["goal"] == "测试目标"
    
    def test_inject_context_formats_output(self):
        """测试注入上下文格式化"""
        ctx = GSDContext(
            session_id="session1",
            goal="测试目标",
            constraints=["约束1"],
            completed=["任务1"],
            in_progress=["任务2"],
            goal_version=2
        )
        self.refresher._cache["session1"] = ctx
        
        recent = [{"role": "user", "content": "继续"}]
        output = self.refresher.inject_context("session1", recent)
        
        assert "GSD 上下文保鲜" in output
        assert "测试目标" in output
        assert "v2" in output
        assert "约束1" in output
        assert "任务1" in output


class TestConstraintExtraction:
    """测试约束提取"""
    
    def setup_method(self):
        self.mock_vm = MagicMock()
        self.refresher = ContextRefresher(vector_memory=self.mock_vm)
    
    def test_extract_multiple_constraints(self):
        """测试提取多个约束"""
        text = "必须使用 Python，不能用 Java，不要用第三方库"
        
        constraints = self.refresher._extract_constraints(text)
        
        assert len(constraints) >= 3
    
    def test_no_constraints(self):
        """测试无约束情况"""
        text = "帮我实现一个简单的功能"
        
        constraints = self.refresher._extract_constraints(text)
        
        assert len(constraints) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
