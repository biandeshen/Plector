"""
图片处理配置常量
"""

# 支持的图片格式
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# 最大文件大小 (20MB)
MAX_FILE_SIZE = 20 * 1024 * 1024

# HTTP 配置
REQUEST_TIMEOUT = 5
STREAM_CHUNK_SIZE = 8192
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}

# DNS 缓存配置
DNS_CACHE_TTL = 300  # 秒
DNS_CACHE_MAX_SIZE = 1000

# 图片命令映射
IMAGE_COMMANDS = {
    "分析图片": "详细描述这张图片的内容",
    "识别图片": "识别图片中的文字和内容",
    "看看这张图": "描述这张图片",
    "图片代码": "如果图片中有代码，请提取并解释代码的功能和逻辑",
    "图片架构": "分析这张架构图的设计思路和组件关系",
    "图片UI": "分析这个UI界面的设计，包括布局、配色、交互元素",
    "图片错误": "分析这张错误截图，说明错误原因和解决方案",
}

# 默认后端配置
IMAGE_BACKENDS: dict[str, dict] = {
    "minimax": {
        "type": "mcp",
        "server": "minimax",
        "skill": None,
        "tool": "understand_image",
        "priority": 10,
        "enabled": True,
    },
}
