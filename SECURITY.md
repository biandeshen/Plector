# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :white_check_mark: |

---

## Reporting a Vulnerability

We take security issues seriously. If you discover a vulnerability, please report it responsibly.

### How to Report

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Send an email to: `security@plector.dev`
3. Or use GitHub's [Private Vulnerability Reporting](https://github.com/biandeshen/Plector/security/advisories/new)

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Timeline**: Within 2 weeks for critical issues

---

## Security Features

Plector includes the following built-in security features:

### Input Validation

- All inputs are sanitized via `SecurityMiddleware`
- Prompt injection prevention
- Shell command validation

### Audit Logging

- All agent operations are logged via `AuditMiddleware`
- WORM (Write Once Read Many) storage for audit logs
- Hash chain for tamper evidence

### Tool Sandboxing

- Dangerous system calls are blocked
- Shell tools require user confirmation
- File operation permissions are scoped

### MCP Security

- MCP server authentication required
- Resource access validation
- Capability-based permissions

---

## Dependencies

We use `pip-audit` to scan for vulnerable dependencies:

```bash
# Install pip-audit
pip install pip-audit

# Scan dependencies
pip-audit -r requirements.txt
```

---

## Security Updates

Security updates are released as patch versions. We recommend:

1. Watch the repository for release announcements
2. Subscribe to notifications for security advisories
3. Keep your dependencies up to date

---

## Security Advisories

For past security issues, see our [Security Advisories](https://github.com/biandeshen/Plector/security/advisories).

---

## Best Practices for Users

1. **Keep API keys secure**: Never commit API keys to version control
2. **Use environment variables**: Store secrets in `.env` files
3. **Limit tool permissions**: Only grant necessary capabilities to skills
4. **Monitor audit logs**: Regularly review operation logs for anomalies
5. **Update regularly**: Keep Plector updated to receive security patches

---

## Responsible Disclosure

We follow responsible disclosure practices:
- We will credit reporters in the security advisory (with permission)
- We will not pursue legal action against good-faith security researchers
- We ask that you give us reasonable time to fix vulnerabilities before public disclosure
