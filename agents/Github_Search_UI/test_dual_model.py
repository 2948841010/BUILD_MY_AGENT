#!/usr/bin/env python3
"""
测试双模型Plan and Execute GitHub搜索代理
"""

import asyncio
import sys
import os

# 添加路径以便导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import (
    plan_execute_agent,
    search_github,
    plan_and_execute_search,
    PlanAndExecuteGitHubAgent
)

async def test_dual_model_async():
    """测试异步双模型搜索"""
    print("🧪 测试异步双模型搜索")
    print("=" * 50)
    
    query = "spring boot vue 前后端分离项目"
    
    try:
        result = await plan_execute_agent.search(query)
        
        print(f"✅ 搜索完成!")
        print(f"📝 查询: {result['user_query']}")
        print(f"🎯 策略: {result['plan']['strategy']}")
        print(f"📊 执行统计: {result['execution']}")
        print(f"🔍 发现仓库数: {result['execution']['discovered_repos']}")
        
        return True
    except Exception as e:
        print(f"❌ 异步测试失败: {str(e)}")
        return False

def test_dual_model_sync():
    """测试同步双模型搜索"""
    print("\n🧪 测试同步双模型搜索")
    print("=" * 50)
    
    query = "python web framework"
    
    try:
        result = search_github(query)
        
        print(f"✅ 同步搜索完成!")
        print(f"📝 查询: {result['user_query']}")
        print(f"🎯 策略: {result['plan']['strategy']}")
        
        return True
    except Exception as e:
        print(f"❌ 同步测试失败: {str(e)}")
        return False

def test_tool_function():
    """测试工具函数"""
    print("\n🧪 测试工具函数")
    print("=" * 50)
    
    query = "react typescript ui组件库"
    
    try:
        result = plan_and_execute_search(query)
        
        print("✅ 工具函数测试完成!")
        print("📄 格式化结果:")
        print(result[:200] + "..." if len(result) > 200 else result)
        
        return True
    except Exception as e:
        print(f"❌ 工具函数测试失败: {str(e)}")
        return False

def test_agent_creation():
    """测试代理创建"""
    print("\n🧪 测试代理创建")
    print("=" * 50)
    
    try:
        # 测试创建新的代理实例
        new_agent = PlanAndExecuteGitHubAgent()
        
        print("✅ Planning Agent创建成功")
        print(f"📋 Planning Agent: {type(new_agent.planner)}")
        print(f"⚡ Execution Agent: {type(new_agent.executor)}")
        
        # 测试状态
        status = new_agent.get_current_status()
        print(f"📊 初始状态: {status}")
        
        return True
    except Exception as e:
        print(f"❌ 代理创建测试失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    print("🚀 双模型Plan and Execute GitHub搜索代理测试")
    print("=" * 60)
    
    tests = [
        ("代理创建", test_agent_creation),
        ("工具函数", test_tool_function),
        ("同步搜索", test_dual_model_sync),
        ("异步搜索", test_dual_model_async),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔄 运行测试: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {str(e)}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过! 双模型架构工作正常")
    else:
        print("⚠️ 部分测试失败，请检查配置")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main()) 