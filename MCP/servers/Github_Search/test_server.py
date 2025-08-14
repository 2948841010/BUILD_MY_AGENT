#!/usr/bin/env python3
"""
测试脚本用于验证 GitHub Search MCP 服务器功能
"""
import asyncio
import json
from server import search_repositories, get_repository_info, get_repository_languages, get_repository_tree, get_repository_file_content

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
            
            # 测试4: 高级搜索功能
            print("\n4️⃣ 测试高级搜索功能")
            try:
                advanced_results = search_repositories("springboot AND vue", max_results=2, search_mode="advanced")
                print(f"高级搜索结果: {advanced_results}")
            except Exception as e:
                print(f"高级搜索测试失败: {e}")
            
            # 测试5: 获取目录结构
            print("\n5️⃣ 测试目录结构功能")
            try:
                tree_result = get_repository_tree(test_repo)
                tree_data = json.loads(tree_result)
                print(f"根目录包含 {tree_data.get('total_items', 0)} 个项目")
                
                # 显示前几个项目
                if 'items' in tree_data:
                    print("根目录内容:")
                    for item in tree_data['items'][:5]:
                        print(f"  - {item['name']} ({item['type']})")
                    
                    # 尝试查看一个文件内容（选择一个较小的文件）
                    test_file = None
                    for item in tree_data['items']:
                        if item['name'].lower() in ['.gitignore', 'contributing.md', 'citation.cff']:
                            test_file = item['path']
                            break
                    
                    # 如果没有找到小文件，尝试README但增加大小限制
                    if not test_file:
                        for item in tree_data['items']:
                            if item['name'].lower() in ['readme.md', 'readme.txt', 'readme']:
                                test_file = item['path']
                                break
                    
                    if test_file:
                        # 根据文件类型设置合适的大小限制
                        max_size = 50000 if test_file.lower().endswith('.md') else 5000
                        print(f"\n6️⃣ 测试文件内容功能 - 查看 {test_file}")
                        try:
                            file_content = get_repository_file_content(test_repo, test_file, max_size=max_size)
                            if file_content.startswith('{'):
                                content_data = json.loads(file_content)
                                content_preview = content_data.get('content', '')[:300]
                                print(f"文件大小: {content_data.get('size', 0)} 字节")
                                print(f"内容预览: {content_preview}...")
                            else:
                                print(f"非JSON响应: {file_content[:200]}...")
                        except Exception as e:
                            print(f"文件内容读取失败: {e}")
                            print(f"返回内容: {file_content[:200] if 'file_content' in locals() else 'N/A'}")
                            
            except Exception as e:
                print(f"目录结构测试失败: {e}")
                
        else:
            print("❌ 搜索失败，可能是网络问题或API限制")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_github_search()) 