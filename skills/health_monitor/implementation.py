import asyncio
import psutil
from core.event_bus import get_event_bus

class SkillHandler:
    async def check_health(self) -> dict:
        loop = asyncio.get_event_loop()
        # 使用线程池执行阻塞调用
        cpu = await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0))
        memory = await loop.run_in_executor(None, lambda: psutil.virtual_memory().percent)
        disk = await loop.run_in_executor(None, lambda: psutil.disk_usage('/').percent)
        status = "healthy" if (cpu < 80 and memory < 80 and disk < 80) else "degraded"

        # 发布 CloudEvents 格式的健康事件
        bus = get_event_bus()
        await bus.publish(f"health.{status}", {
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
        }, source="health_monitor")

        return {"cpu": cpu, "memory": memory, "disk": disk, "status": status}
