import logging

from .context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class MemoryLoader:
    """记忆加载与系统提示词组裝"""

    def __init__(self, context_builder: ContextBuilder):
        self.context_builder = context_builder

    async def load(self, session_id: str) -> str:
        try:
            from core.vector_memory import VectorMemory

            memory_parts = []
            vm = VectorMemory()

            pref_results = await vm.search(
                query=session_id,
                collection="preferences",
                n_results=20,
            )
            if pref_results:
                memory_parts.append("## 用户偏好")
                for r in pref_results:
                    memory_parts.append(f"- {r['text']}")

            conv_results = await vm.search(
                query="最近的对话内容",
                collection="conversations",
                n_results=5,
                session_id=session_id,
            )
            if conv_results:
                memory_parts.append("")
                memory_parts.append("## 最近对话")
                for r in conv_results:
                    content = r["text"]
                    if len(content) > 100:
                        content = content[:100] + "..."
                    memory_parts.append(f"- {r['metadata'].get('role', 'unknown')}: {content}")

            return "\n".join(memory_parts) if memory_parts else ""

        except Exception as e:
            logger.warning(f"加载记忆失败（降级为空）: {e}")
            return ""

    def build_system_prompt(self, memory_context: str = "") -> str:
        prompt = self.context_builder.build_system_prompt()
        if memory_context:
            prompt += "\n\n" + memory_context
        return prompt
