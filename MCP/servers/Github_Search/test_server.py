#!/usr/bin/env python3
"""
测试脚本用于验证 GitHub Search MCP 服务器功能
"""
import asyncio
import json
from server import search_repositories, get_repository_info, get_repository_languages

async def test_github_search():
    """测试GitHub搜索功能"""
    print("🧪 Testing GitHub Search MCP Server")
    print("=" * 50)
    
    # 测试1: 搜索仓库
    print("\n1️⃣ 测试搜索功能")
    try:
        results = search_repositories("python web framework", max_results=3, sort="stars")
        print(f"搜索结果: {results}")
        
        if results and not any("Error" in str(r) for r in results):
            test_repo = results[0]
            print(f"将使用 '{test_repo}' 进行后续测试")
            
            # 测试2: 获取仓库详细信息
            print("\n2️⃣ 测试获取仓库信息")
            repo_info = get_repository_info(test_repo)
            print(f"仓库信息长度: {len(repo_info)} 字符")
            
            # 解析并显示部分信息
            try:
                info_data = json.loads(repo_info)
                print(f"仓库名: {info_data.get('name', 'N/A')}")
                print(f"Stars: {info_data.get('stars', 'N/A')}")
                print(f"主要语言: {info_data.get('language', 'N/A')}")
            except json.JSONDecodeError:
                print(f"信息预览: {repo_info[:200]}...")
            
            # 测试3: 获取语言统计
            print("\n3️⃣ 测试语言统计功能")
            lang_stats = get_repository_languages(test_repo)
            print(f"语言统计长度: {len(lang_stats)} 字符")
            
            try:
                lang_data = json.loads(lang_stats)
                if 'languages' in lang_data:
                    print("主要编程语言:")
                    for lang, stats in list(lang_data['languages'].items())[:3]:
                        print(f"  - {lang}: {stats['percentage']}%")
            except json.JSONDecodeError:
                print(f"语言统计预览: {lang_stats[:200]}...")
                
        else:
            print("❌ 搜索失败，可能是网络问题或API限制")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_github_search()) 