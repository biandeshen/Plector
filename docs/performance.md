# Plector 性能优化文档

> 本文档描述 Plector 的性能优化策略、基准测试和最佳实践。

## 目录

1. [性能目标](#性能目标)
2. [基准测试](#基准测试)
3. [性能剖析](#性能剖析)
4. [可观测量](#可观测量)
5. [告警规则](#告警规则)
6. [最佳实践](#最佳实践)

---

## 性能目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| Agent Loop 延迟 P99 | < 50ms | 单次 agent cycle |
| 事件总线吞吐量 | > 10,000 events/s | 无阻塞处理 |
| LLM 调用延迟 | < 2s | 不含模型推理时间 |
| 内存占用 | < 512MB | 空闲状态 |
| CPU 空闲占用 | < 5% | 无负载时 |

---

## 基准测试

### 运行基准测试

```bash
# 运行所有基准测试
pytest tests/benchmarks/ -v --benchmark

# 运行特定测试
pytest tests/benchmarks/test_agent_loop.py -v

# 性能剖析
python -m pytest tests/benchmarks/ --profile
```

### Agent Loop 基准

```python
# tests/benchmarks/test_agent_loop.py
def test_agent_loop_100_iterations(benchmark_config):
    latencies = simulate_agent_loop(100)
    p99 = sorted(latencies)[98]
    assert p99 < 50, f"P99 latency too high: {p99:.2f}ms"
```

### 事件总线基准

```python
# tests/benchmarks/test_event_bus.py
def test_event_bus_throughput():
    events_per_sec = measure_event_bus_throughput(10000)
    assert events_per_sec > 10000, f"Throughput too low"
```

---

## 性能剖析

### 使用 Profiler

```python
from core.performance.profiler import profile, get_profiler

# 装饰器方式
@profile("my_function")
async def my_async_function():
    pass

# 上下文管理器
profiler = get_profiler()
with profiler.profile("critical_section"):
    # 执行代码
    pass

# 打印报告
profiler.print_report()
```

### 输出示例

```
======================================================================
Name                                     Calls    Total     Avg     Min     Max
----------------------------------------------------------------------
core.agent.process                       1000    150.23ms    0.15ms   0.10ms   0.45ms
core.llm.complete                         100   2500.00ms   25.00ms  20.00ms  35.00ms
======================================================================
```

---

## 可观测量

### 追踪 (Tracing)

```python
from core.observability import get_tracer, SpanKind

tracer = get_tracer()

# 装饰器方式
@tracer.trace("process_request", SpanKind.SERVER)
async def handle_request(data):
    pass

# 手动方式
span = tracer.start_span("operation", SpanKind.INTERNAL)
try:
    result = await do_work()
    span.set_attribute("result", "success")
except Exception as e:
    span.set_attribute("error", str(e))
finally:
    tracer.end_span(span)
```

### 日志 (Logging)

```python
from core.observability import get_logger, LogLevel

logger = get_logger("my_module", level=LogLevel.DEBUG)

logger.info("Operation completed", request_id="123")
logger.warning("Rate limit approaching", current=80, limit=100)
logger.error("Request failed", error=str(e))
```

### 指标 (Metrics)

```python
from core.observability import get_metrics

metrics = get_metrics()

# 计数器
counter = metrics.counter("requests_total", {"method": "POST"})
counter.inc()

# 仪表
gauge = metrics.gauge("queue_size")
gauge.set(42)

# 直方图
histogram = metrics.histogram("request_duration")
histogram.observe(0.123)

# 导出 Prometheus 格式
print(metrics.get_prometheus_format())
```

---

## 告警规则

### 配置文件

告警规则定义在 `config/alerts.yaml`:

```yaml
alerts:
  - id: cpu_high
    name: CPU 使用率过高
    severity: warning
    condition:
      metric: cpu_percent
      operator: ">"
      threshold: 80
      duration: 300
    actions:
      - type: log
        level: warning
    enabled: true
```

### 预定义告警

| ID | 名称 | 阈值 | 严重级别 |
|----|------|------|----------|
| cpu_high | CPU 使用率过高 | > 80% | warning |
| cpu_critical | CPU 危险 | > 95% | critical |
| memory_high | 内存过高 | > 85% | warning |
| memory_critical | 内存危险 | > 95% | critical |
| agent_latency_high | 延迟过高 | > 5s P95 | warning |
| workflow_timeout | 工作流超时 | > 5min | warning |

---

## 最佳实践

### 1. 减少 Agent Loop 开销

```python
# 不好：每次都创建新对象
for item in items:
    agent = Agent()
    await agent.process(item)

# 好：复用 agent 实例
agent = Agent()
for item in items:
    await agent.process(item)
```

### 2. 使用批量操作

```python
# 不好：逐个调用
for item in items:
    await llm.complete(item)

# 好：批量调用
results = await llm.batch_complete(items)
```

### 3. 合理设置缓存

```python
# LLM 响应缓存
cache = ResponseCache(ttl=3600)  # 1小时过期

async def get_cached_response(prompt):
    cache_key = hash(prompt)
    if cached := cache.get(cache_key):
        return cached
    result = await llm.complete(prompt)
    cache.set(cache_key, result)
    return result
```

### 4. 异步优先

```python
# 不好：同步调用阻塞事件循环
def sync_operation():
    result = blocking_call()

# 好：使用异步版本
async def async_operation():
    result = await async_call()
```

### 5. 监控关键指标

```python
# 在关键路径添加指标收集
@profile("critical_path")
async def critical_path(data):
    metrics = get_metrics()
    timer = metrics.histogram("critical_path_duration")
    
    start = time.perf_counter()
    try:
        result = await process(data)
        metrics.counter("critical_path_success").inc()
        return result
    except Exception as e:
        metrics.counter("critical_path_errors").inc()
        raise
    finally:
        timer.observe(time.perf_counter() - start)
```

---

## 监控仪表板

访问 `ui/dashboard/index.html` 查看实时监控：

```bash
# 本地启动
python -m http.server 8080 --directory ui/dashboard

# 访问
open http://localhost:8080
```

仪表板功能：
- 实时系统指标（CPU、内存、磁盘）
- 性能趋势图表
- 告警列表
- Agent 状态监控

---

## 性能回归检测

在 CI/CD 中集成性能测试：

```yaml
# .github/workflows/perf-test.yml
- name: Performance Tests
  run: |
    pytest tests/benchmarks/ \
      --benchmark-only \
      --benchmark-json=benchmark.json
    # 与 baseline 比较
    pip install benchmark-diff
    benchmark-diff benchmark.json baseline.json
```

---

*最后更新: 2024*
