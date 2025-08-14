#!/usr/bin/env python3
"""
GitHub Search MCP 服务器启动脚本
用于快速启动GitHub搜索和分析服务
"""
import sys
import os
import subprocess

def main():
    """启动GitHub Search MCP服务器"""
    print("🚀 启动 GitHub Search MCP 服务器")
    print("=" * 50)
    
    # 检查依赖
    try:
        import requests
        import fastmcp
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install requests fastmcp fastapi uvicorn")
        return
    
    # 获取命令行参数
    port = 50003  # 默认端口，避免与其他服务冲突
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"❌ 无效端口号: {sys.argv[1]}")
            return
    
    print(f"📡 服务器将在端口 {port} 启动")
    print(f"🌐 访问地址: http://localhost:{port}")
    print("💡 按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    # 启动服务器
    try:
        from server import mcp
        print("🎯 GitHub Search MCP 服务器已启动!")
        print("\n📋 可用工具:")
        print("  • search_repositories - 搜索GitHub仓库")
        print("  • get_repository_info - 获取仓库详细信息")  
        print("  • get_repository_languages - 分析编程语言统计")
        print("\n📁 数据存储目录: ./repositories/")
        print("-" * 50)
        
        # 设置端口并启动
        mcp.port = port
        mcp.run()
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"\n❌ 服务器启动失败: {e}")

if __name__ == "__main__":
    main() 