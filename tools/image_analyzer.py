"""图片识别工具
使用 MiniMax MCP Server 进行图片理解
"""
import asyncio
import sys
import os
import json
import base64
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows UTF-8 输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

from core.mcp_manager import MCPManager


async def upload_and_analyze(image_path: str) -> dict:
    """上传并分析图片"""
    manager = MCPManager()
    
    print(f"📸 正在分析图片: {image_path}")
    
    try:
        # 检查文件是否存在
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")
        
        # 检查文件大小（MiniMax 限制 10MB）
        file_size = path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            raise ValueError(f"图片过大: {file_size / 1024 / 1024:.2f}MB（限制 10MB）")
        
        # 读取图片并转换为 base64
        print("📦 读取图片...")
        with open(image_path, 'rb') as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # 获取图片类型
        image_type = path.suffix.lower().replace('.', '')
        if image_type == 'jpg':
            image_type = 'jpeg'
        elif image_type not in ['png', 'jpeg', 'webp', 'gif']:
            raise ValueError(f"不支持的图片格式: {image_type}")
        
        # 加载 MCP 配置
        print("🔌 连接 MiniMax MCP Server...")
        await manager.load_config()
        
        # 调用 understand_image 工具
        print("🔍 分析图片中...")
        result = await manager.call_tool(
            'minimax',
            'understand_image',
            {
                'image_source': {
                    'type': 'base64',
                    'data': f'data:image/{image_type};base64,{image_base64}'
                },
                'prompt': '请详细描述这张图片的内容，包括主要元素、颜色、文字、场景等。'
            }
        )
        
        return result
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        raise


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python tools/image_analyzer.py <图片路径>")
        print("\n示例:")
        print("  python tools/image_analyzer.py test.jpg")
        print("  python tools/image_analyzer.py C:\\images\\photo.png")
        return
    
    image_path = sys.argv[1]
    
    try:
        result = await upload_and_analyze(image_path)
        
        print("\n" + "="*50)
        print("✅ 分析完成！")
        print("="*50)
        print("\n分析结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
