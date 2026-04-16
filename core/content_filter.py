"""
内容过滤器 - 敏感信息检测与脱敏

使用方式:
    from core.content_filter import check_content, sanitize_output

    # 检查内容
    ok, msg = check_content("我的密码是 123456")
    if not ok:
        return {"error": msg}

    # 脱敏输出
    safe = sanitize_output(output)
"""

import re
from typing import tuple

# 敏感信息模式
SENSITIVE_PATTERNS = [
    # 密码类
    (r'\b(密码|password|passwd|pwd)\s*[:=]\s*\S+', "密码"),
    (r'\b(口令)\s*[:=]\s*\S+', "口令"),
    # API 密钥类
    (r'\b(api_key|apikey|api-key|secret_key|secretkey)\s*[:=]\s*\S+', "API 密钥"),
    (r'\b(token|TOKEN|auth_token)\s*[:=]\s*\S+', "Token"),
    # 银行卡/信用卡
    (r'\b(银行卡|信用卡|卡号)\s*[:=]?\s*\d{13,19}', "银行卡号"),
    # 身份证号
    (r'\b(身份证|身份证号|id_card)\s*[:=]\s*\d{15,18}[xX]?', "身份证号"),
    # 手机号
    (r'\b(手机|phone|mobile)\s*[:=]\s*1[3-9]\d{9}', "手机号"),
]


def check_content(text: str) -> tuple[bool, str]:
    """
    检查内容是否包含敏感信息

    返回:
        (是否通过, 原因消息)

    使用方式:
        ok, msg = check_content(user_input)
        if not ok:
            return {"error": msg}
    """
    for pattern, label in SENSITIVE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"检测到可能的{label}，请勿在对话中分享敏感信息"
    return True, ""


def sanitize_output(text: str) -> str:
    """
    脱敏输出中的敏感信息

    返回:
        脱敏后的文本
    """
    for pattern, label in SENSITIVE_PATTERNS:
        # 保留键名，隐藏值
        text = re.sub(pattern, lambda m: f"{m.group(1)}: [已隐藏]", text, flags=re.IGNORECASE)
    return text


def filter_html(text: str) -> str:
    """
    过滤 HTML 标签（防止 XSS）

    返回:
        过滤后的纯文本
    """
    # 移除 script 标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 移除事件处理器
    text = re.sub(r'on\w+\s*=\s*["\'].*?["\']', '', text, flags=re.IGNORECASE)
    return text


# 简易脏话/有害信息检测（生产环境应接外部服务）
HARMFUL_PATTERNS = [
    # 可以根据需要添加更多模式
]

def check_harmful(text: str) -> tuple[bool, str]:
    """
    检查是否有害信息

    返回:
        (是否通过, 原因消息)
    """
    for pattern in HARMFUL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "检测到不当内容，请文明交流"
    return True, ""
