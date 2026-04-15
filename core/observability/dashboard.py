"""监控仪表板 API - FastAPI 风格"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time


@dataclass
class DashboardData:
    """仪表板数据"""
    timestamp: float
    metrics: Dict[str, Any]
    traces: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]


class DashboardAPI:
    """监控仪表板 API"""

    def __init__(self):
        self.data: List[DashboardData] = []

    def collect(self, metrics: Dict, traces: List, logs: List) -> DashboardData:
        """收集当前状态数据"""
        data = DashboardData(
            timestamp=time.time(),
            metrics=metrics,
            traces=traces,
            logs=logs,
            alerts=self._check_alerts(metrics)
        )
        self.data.append(data)
        return data

    def _check_alerts(self, metrics: Dict) -> List[Dict]:
        """检查告警条件"""
        alerts = []

        # CPU 告警
        if "cpu_percent" in metrics and metrics["cpu_percent"] > 90:
            alerts.append({
                "level": "warning",
                "metric": "cpu_percent",
                "message": f"CPU 使用率过高: {metrics['cpu_percent']}%"
            })

        # 内存告警
        if "memory_percent" in metrics and metrics["memory_percent"] > 85:
            alerts.append({
                "level": "warning",
                "metric": "memory_percent",
                "message": f"内存使用率过高: {metrics['memory_percent']}%"
            })

        return alerts

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总统计"""
        if not self.data:
            return {}

        latest = self.data[-1]
        return {
            "timestamp": latest.timestamp,
            "metrics": latest.metrics,
            "active_alerts": len(latest.alerts),
            "trace_count": len(latest.traces),
            "log_count": len(latest.logs),
        }

    def get_metrics_history(self, metric_name: str, limit: int = 100) -> List[Dict]:
        """获取指标历史"""
        history = []
        for d in self.data[-limit:]:
            if metric_name in d.metrics:
                history.append({
                    "timestamp": d.timestamp,
                    "value": d.metrics[metric_name]
                })
        return history

    def export_prometheus(self, metrics) -> str:
        """导出 Prometheus 格式"""
        if hasattr(metrics, "get_prometheus_format"):
            return metrics.get_prometheus_format()
        return ""


# 全局实例
_dashboard = DashboardAPI()


def get_dashboard() -> DashboardAPI:
    return _dashboard
