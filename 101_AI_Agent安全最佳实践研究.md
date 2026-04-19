# AI Agent 安全最佳实践研究

> 来源：Glean / Digital Applied / Noma Security
> 研究日期：2026-04-19

---

## 一、安全威胁全景

### 1.1 AI Agent 特有威胁

```
┌─────────────────────────────────────────────────────────┐
│               AI Agent 安全威胁分类                        │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  推理威胁 (Inference Threats)                        ││
│  │  • 提示注入 (Prompt Injection)                      ││
│  │  • 敏感数据泄露 (Data Exfiltration)                 ││
│  │  • 上下文窃取 (Context Leaking)                     ││
│  └─────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │  代理威胁 (Agentic Threats)                         ││
│  │  • 未经授权操作 (Unauthorized Actions)              ││
│  │  • 权限升级 (Privilege Escalation)                  ││
│  │  • 恶意工具调用 (Malicious Tool Use)               ││
│  └─────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │  供应链威胁 (Supply Chain)                          ││
│  │  • 恶意技能 (Malicious Skills)                      ││
│  │  • 污染工具 (Poisoned Tools)                        ││
│  │  • 依赖漏洞 (Dependency Vulnerabilities)            ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 1.2 威胁矩阵

| 威胁 | 严重性 | 影响 | 攻击面 |
|------|--------|------|--------|
| 提示注入 | 高 | 数据泄露/未授权操作 | 用户输入 |
| 工具投毒 | 高 | 恶意代码执行 | 技能/工具注册 |
| 权限过度 | 中 | 数据破坏/泄露 | 授权配置 |
| 上下文泄露 | 中 | 敏感信息暴露 | 记忆系统 |
| 审计缺失 | 中 | 合规问题 | 日志系统 |

---

## 二、零信任安全架构

### 2.1 核心原则

> **"AI agents should be treated as untrusted third parties with the same security controls applied to external contractors."**

**三大原则：**
1. **永不信任 (Never Trust)**：假设所有输入都是恶意的
2. **始终验证 (Always Verify)**：每次操作都需授权检查
3. **最小权限 (Least Privilege)**：只授予完成任务所需的最小权限

### 2.2 架构设计

```
┌─────────────────────────────────────────────────────────┐
│              AI Agent 零信任安全架构                     │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  身份层 (Identity)                                  ││
│  │  • Agent 身份认证                                    ││
│  │  • 短期凭证                                        ││
│  │  • 工作负载身份联合                                  ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  策略层 (Policy)                                    ││
│  │  • RBAC / ABAC 访问控制                            ││
│  │  • 实时策略评估                                     ││
│  │  • 动态权限调整                                     ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  执行层 (Enforcement)                               ││
│  │  • 输入清理                                         ││
│  │  • 输出验证                                         ││
│  │  • 沙箱执行                                        ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  审计层 (Audit)                                     ││
│  │  • 操作日志                                         ││
│  │  • 实时告警                                         ││
│  │  • 合规报告                                         ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 三、身份与认证

### 3.1 Agent 身份管理

```python
from datetime import datetime, timedelta

class AgentIdentity:
    """Agent 身份管理"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.certificate = None
        self.last_auth = None

    async def authenticate(self) -> AuthToken:
        """身份认证"""
        # 1. 获取短期证书
        cert = await self.pki.issue_certificate(
            subject=self.agent_id,
            validity=timedelta(hours=1)
        )

        # 2. 验证凭证
        token = await self.token_exchange.exchange(cert)

        self.certificate = cert
        self.last_auth = datetime.now()

        return AuthToken(
            token=token,
            expires_at=datetime.now() + timedelta(hours=1)
        )

    async def verify(self, token: str) -> bool:
        """验证令牌"""
        return await self.token_store.validate(token)
```

### 3.2 令牌委托机制

```python
class TokenDelegation:
    """令牌委托实现"""

    async def create_delegation_token(
        self,
        user_id: str,
        agent_id: str,
        permissions: list[str],
        ttl: timedelta
    ) -> DelegationToken:
        """创建委托令牌"""

        # 令牌包含：原始用户 + Agent + 权限 + TTL
        payload = {
            "sub": user_id,           # 原始用户
            "act": agent_id,          # 代理 Agent
            "perms": permissions,      # 授权权限
            "exp": datetime.now() + ttl,
            "iat": datetime.now()
        }

        # 签名防止篡改
        signature = self.sign(payload)

        return DelegationToken(
            payload=payload,
            signature=signature
        )

    def verify_delegation(self, token: DelegationToken) -> bool:
        """验证委托令牌"""
        # 1. 检查签名
        if not self.verify_signature(token):
            return False

        # 2. 检查过期
        if datetime.now() > token.exp:
            return False

        # 3. 检查权限
        return True
```

---

## 四、访问控制

### 4.1 RBAC 实现

```python
from enum import Enum
from typing import Set

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"

class Role(Enum):
    USER = "user"
    DEVELOPER = "developer"
    ADMIN = "admin"
    AGENT = "agent"

ROLE_PERMISSIONS = {
    Role.USER: {Permission.READ},
    Role.DEVELOPER: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
    Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN},
    Role.AGENT: {Permission.READ, Permission.EXECUTE},  # Agent 最小权限
}

class RBAC:
    """基于角色的访问控制"""

    def __init__(self):
        self.user_roles: dict[str, Set[Role]] = {}
        self.agent_permissions: dict[str, Set[Permission]] = {}

    async def check_permission(
        self,
        subject: str,
        permission: Permission,
        resource: str
    ) -> bool:
        """检查权限"""

        # 1. 获取角色
        roles = self.user_roles.get(subject, set())

        # 2. 检查角色权限
        for role in roles:
            if permission in ROLE_PERMISSIONS.get(role, set()):
                # 3. 检查资源策略
                return await self.check_resource_policy(
                    subject, permission, resource
                )

        return False

    async def check_resource_policy(
        self,
        subject: str,
        permission: Permission,
        resource: str
    ) -> bool:
        """检查资源级策略"""
        policy = self.policies.get(resource)

        if not policy:
            # 默认拒绝
            return False

        return policy.evaluate(subject, permission)
```

### 4.2 ABAC 实现

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Attribute:
    """属性定义"""
    key: str
    value: any
    attributes: dict[str, any]

class ABACPolicy:
    """基于属性的访问控制"""

    def __init__(self):
        self.policies: list[Policy] = []

    async def evaluate(
        self,
        subject: Attribute,
        action: str,
        resource: Attribute,
        environment: Attribute
    ) -> bool:
        """评估访问请求"""

        for policy in self.policies:
            if policy.matches(subject, action, resource, environment):
                return policy.effect == "permit"

        return False  # 默认拒绝

class DynamicPermission:
    """动态权限 - JIT 访问"""

    async def grant_just_in_time(
        self,
        user_id: str,
        permission: Permission,
        resource: str,
        duration: timedelta
    ) -> Grant:
        """JIT 权限授予"""
        grant = Grant(
            user_id=user_id,
            permission=permission,
            resource=resource,
            granted_at=datetime.now(),
            expires_at=datetime.now() + duration
        )

        await self.grant_store.save(grant)
        return grant
```

---

## 五、输入输出安全

### 5.1 输入清理

```python
import re

class InputSanitizer:
    """输入清理器"""

    def __init__(self):
        self.dangerous_patterns = [
            r'<script.*?>.*?</script>',  # XSS
            r'\$\{.*?\}',               # 变量注入
            r'\{\{.*?\}\}',             # 模板注入
            r'exec\(|eval\(',           # 代码执行
        ]

    def sanitize(self, user_input: str) -> SanitizedInput:
        """清理用户输入"""

        cleaned = user_input

        # 1. 移除危险模式
        for pattern in self.dangerous_patterns:
            cleaned = re.sub(pattern, '[REDACTED]', cleaned)

        # 2. 转义特殊字符
        cleaned = self.escape_special_chars(cleaned)

        # 3. 长度限制
        if len(cleaned) > MAX_INPUT_LENGTH:
            cleaned = cleaned[:MAX_INPUT_LENGTH]

        # 4. 标记清理
        markers = self.detect_injection_markers(cleaned)

        return SanitizedInput(
            content=cleaned,
            markers=markers,
            is_clean=len(markers) == 0
        )

    def detect_injection_markers(self, content: str) -> list[InjectionMarker]:
        """检测注入标记"""
        markers = []

        # 检测提示注入
        injection_phrases = [
            "ignore previous instructions",
            "disregard all rules",
            "you are now",
            "system prompt",
            "admin mode"
        ]

        for phrase in injection_phrases:
            if phrase.lower() in content.lower():
                markers.append(InjectionMarker(
                    type="prompt_injection",
                    phrase=phrase,
                    position=content.lower().find(phrase.lower())
                ))

        return markers
```

### 5.2 输出验证

```python
class OutputValidator:
    """输出验证器"""

    def __init__(self):
        self.validators: list[Validator] = []

    async def validate(self, output: AgentOutput) -> ValidationResult:
        """验证 Agent 输出"""

        results = []

        # 1. 格式验证
        results.append(await self.validate_format(output))

        # 2. 安全验证
        results.append(await self.validate_security(output))

        # 3. 事实性验证
        results.append(await self.validate_facts(output))

        # 4. 代码安全验证
        if output.code:
            results.append(await self.validate_code_safety(output.code))

        return ValidationResult(
            passed=all(r.passed for r in results),
            details=results
        )

    async def validate_code_safety(self, code: str) -> ValidationResult:
        """代码安全验证"""

        dangerous_patterns = [
            r'os\.system\(',
            r'subprocess\.",
            r'exec\(',
            r'eval\(',
            r'__import__\(',
            r'requests\.(get|post)\(',  # 网络请求需审查
        ]

        violations = []
        for pattern in dangerous_patterns:
            matches = re.findall(pattern, code)
            if matches:
                violations.append(f"Dangerous pattern: {pattern}")

        return ValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            action="BLOCK" if violations else "ALLOW"
        )
```

---

## 六、沙箱执行

### 6.1 沙箱架构

```python
class SandboxManager:
    """沙箱管理器"""

    def __init__(self):
        self.pools: dict[str, SandboxPool] = {}

    async def acquire(
        self,
        sandbox_type: str,
        timeout: timedelta
    ) -> Sandbox:
        """获取沙箱实例"""

        pool = self.pools.get(sandbox_type)

        if not pool:
            pool = self.create_pool(sandbox_type)
            self.pools[sandbox_type] = pool

        sandbox = await pool.acquire(timeout)

        return sandbox

    def create_pool(self, sandbox_type: str) -> SandboxPool:
        """创建沙箱池"""
        if sandbox_type == "docker":
            return DockerSandboxPool()
        elif sandbox_type == "kubernetes":
            return K8sSandboxPool()
        else:
            return ProcessSandboxPool()

class DockerSandboxPool:
    """Docker 沙箱池"""

    def __init__(self):
        self.available: deque = deque()
        self.max_size = 10

    async def acquire(self, timeout: timedelta) -> Sandbox:
        """获取 Docker 沙箱"""
        if self.available:
            return self.available.popleft()

        # 创建新沙箱
        container = await self.docker_client.containers.run(
            "sandbox-image:latest",
            detach=True,
            network_disabled=True,
            read_only=True,
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000  # 50% CPU
        )

        return DockerSandbox(container)
```

### 6.2 网络隔离

```yaml
# Docker 网络策略
version: "3"
services:
  sandbox:
    image: sandbox-image
    networks:
      - isolated
    dns:
      - 8.8.8.8  # 只允许 DNS

networks:
  isolated:
    driver: bridge
    internal: true  # 禁止出站流量
```

### 6.3 文件系统限制

```python
import os

class FilesystemPolicy:
    """文件系统策略"""

    # 允许的路径
    ALLOWED_PATHS = [
        "/workspace",
        "/tmp",
        "/home/user/project"
    ]

    # 只读路径
    READONLY_PATHS = [
        "/etc",
        "/usr",
        "/bin"
    ]

    # 禁止的路径
    BLOCKED_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/root",
        "/.ssh"
    ]

    def check_path(self, path: str, operation: str) -> bool:
        """检查路径访问"""

        real_path = os.path.realpath(path)

        # 检查是否在允许列表
        if not any(real_path.startswith(p) for p in self.ALLOWED_PATHS):
            return False

        # 检查是否在禁止列表
        if any(real_path.startswith(p) for p in self.BLOCKED_PATHS):
            return False

        # 检查只读
        if operation == "write":
            if any(real_path.startswith(p) for p in self.READONLY_PATHS):
                return False

        return True
```

---

## 七、审计日志

### 7.1 审计事件定义

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class AuditEventType(Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    TOOL_EXECUTION = "tool_execution"
    POLICY_VIOLATION = "policy_violation"
    SECURITY_ALERT = "security_alert"

@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    subject_id: str  # 谁
    subject_type: str  # user / agent
    action: str  # 做了什么
    resource: str  # 访问什么资源
    result: str  # 结果：success / failure
    metadata: dict
    ip_address: str | None = None
    user_agent: str | None = None

class AuditLogger:
    """审计日志记录器"""

    async def log(self, event: AuditEvent):
        """记录审计事件"""

        # 1. 写入数据库
        await self.db.insert("audit_logs", event.to_dict())

        # 2. 发送告警（如需要）
        if self._is_alert_needed(event):
            await self.send_alert(event)

        # 3. 发送到 SIEM
        await self.siem.send(event)

    def _is_alert_needed(self, event: AuditEvent) -> bool:
        """判断是否需要告警"""
        alert_types = {
            AuditEventType.POLICY_VIOLATION,
            AuditEventType.SECURITY_ALERT,
            AuditEventType.AUTHORIZATION,
        }
        return event.event_type in alert_types and event.result == "failure"
```

### 7.2 合规报告

```python
class ComplianceReporter:
    """合规报告生成"""

    def generate_soc2_report(self, start: datetime, end: datetime) -> Report:
        """生成 SOC 2 报告"""

        events = await self.audit_store.query(
            start=start,
            end=end,
            types=[
                AuditEventType.AUTHENTICATION,
                AuditEventType.AUTHORIZATION,
                AuditEventType.DATA_ACCESS
            ]
        )

        return Report(
            title="SOC 2 Type II Compliance Report",
            period=f"{start} to {end}",
            sections=[
                Section(
                    title="Access Control",
                    metrics=self.calculate_access_metrics(events),
                    findings=self.identify_findings(events)
                ),
                Section(
                    title="Data Protection",
                    metrics=self.calculate_data_metrics(events),
                    findings=[]
                ),
                Section(
                    title="Incident Response",
                    metrics=self.calculate_incident_metrics(events),
                    findings=[]
                )
            ]
        )
```

---

## 八、Plector 安全加固方案

### 8.1 实施优先级

| 阶段 | 任务 | 优先级 | 工作量 |
|------|------|--------|--------|
| P0 | 输入清理和验证 | 必须 | 1周 |
| P0 | 权限控制 (RBAC) | 必须 | 1周 |
| P0 | 审计日志 | 必须 | 1周 |
| P1 | 沙箱执行 | 重要 | 2周 |
| P1 | 输出验证 | 重要 | 1周 |
| P2 | JIT 权限 | 增强 | 2周 |
| P2 | 合规报告 | 增强 | 1周 |

### 8.2 快速加固清单

```python
# security_checklist.py
SECURITY_CHECKLIST = [
    {
        "id": "AUTH_001",
        "title": "Agent 身份认证",
        "description": "所有 Agent 必须有唯一身份标识",
        "status": "pending"
    },
    {
        "id": "AUTH_002",
        "title": "短期凭证",
        "description": "使用短期证书而非长期密钥",
        "status": "pending"
    },
    {
        "id": "PERM_001",
        "title": "最小权限原则",
        "description": "Agent 只能访问必要的资源和工具",
        "status": "pending"
    },
    {
        "id": "INPUT_001",
        "title": "输入清理",
        "description": "清理所有用户输入中的恶意内容",
        "status": "pending"
    },
    {
        "id": "OUTPUT_001",
        "title": "输出验证",
        "description": "验证 Agent 生成的代码和命令",
        "status": "pending"
    },
    {
        "id": "SANDBOX_001",
        "title": "沙箱执行",
        "description": "危险操作在隔离环境中执行",
        "status": "pending"
    },
    {
        "id": "AUDIT_001",
        "title": "审计日志",
        "description": "记录所有安全相关事件",
        "status": "pending"
    }
]
```

---

## 九、参考资源

- [AI Agent Security Best Practices](https://www.digitalapplied.com/blog/ai-agent-security-best-practices-2025)
- [Noma Security Access Control](https://noma.security/resources/access-control-for-ai-agents/)
- [Glean AI Agent Security](https://www.glean.com/perspectives/best-practices-for-ai-agent-security-in-2025)
- [OWASP LLM Top 10](https://owasp.org/www-project-llm-applications/)

#安全 #零信任 #RBAC #审计 #AI-Agent
