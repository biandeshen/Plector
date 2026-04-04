import asyncio
import psutil

class SkillHandler:
    async def check_health(self) -> dict:
        loop = asyncio.get_event_loop()
        # 使用线程池执行阻塞调用
        cpu = await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0))
        memory = await loop.run_in_executor(None, lambda: psutil.virtual_memory().percent)
        disk = await loop.run_in_executor(None, lambda: psutil.disk_usage('/').percent)
        status = "healthy" if (cpu < 80 and memory < 80 and disk < 80) else "degraded"
        return {"cpu": cpu, "memory": memory, "disk": disk, "status": status}
