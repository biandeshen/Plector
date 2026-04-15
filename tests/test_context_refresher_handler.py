"""验证 context_refresher SkillHandler 标准接口"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.context_refresher.implementation import SkillHandler


class TestSkillHandler:
    """验证 SkillHandler 类存在且符合标准接口"""

    def test_skill_handler_exists(self):
        """验证 SkillHandler 类存在"""
        handler = SkillHandler()
        assert handler is not None

    def test_skill_handler_has_name(self):
        """验证 SkillHandler 有 name 属性"""
        handler = SkillHandler()
        assert hasattr(handler, 'name')
        assert handler.name == "context_refresher"

    def test_skill_handler_has_preserve_method(self):
        """验证 SkillHandler 有 preserve 方法"""
        handler = SkillHandler()
        assert hasattr(handler, 'preserve')
        assert callable(handler.preserve)

    def test_skill_handler_has_re_anchor_method(self):
        """验证 SkillHandler 有 re_anchor 方法"""
        handler = SkillHandler()
        assert hasattr(handler, 're_anchor')
        assert callable(handler.re_anchor)

    def test_skill_handler_has_get_context_method(self):
        """验证 SkillHandler 有 get_context 方法"""
        handler = SkillHandler()
        assert hasattr(handler, 'get_context')
        assert callable(handler.get_context)

    def test_skill_handler_has_build_injected_context_method(self):
        """验证 SkillHandler 有 build_injected_context 方法"""
        handler = SkillHandler()
        assert hasattr(handler, 'build_injected_context')
        assert callable(handler.build_injected_context)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
