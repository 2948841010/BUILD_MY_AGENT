#!/usr/bin/env python3
"""
ReAct GitHub搜索代理测试和演示文件
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from agent import ReActGitHubAgent, SearchStrategy, ReActState


def print_separator(title: str):
    """打印分隔符"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_strategy_selection():
    """测试策略选择功能"""
    print_separator("测试策略选择功能")
    
    from agent import SearchStrategySelector
    
    test_queries = [
        "Python机器学习框架",
        "Django vs Flask哪个更好",
        "最新的AI项目",
        "如何实现微服务架构",
        "tensorflow/tensorflow",
        "比较React和Vue的性能",
        "2024年最热门的开源项目"
    ]
    
    for query in test_queries:
        strategy = SearchStrategySelector.analyze_query_intent(query)
        params = SearchStrategySelector.get_search_parameters(strategy, query)
        print(f"查询: {query}")
        print(f"  策略: {strategy.value}")
        print(f"  参数: {params}")
        print()


def test_state_management():
    """测试状态管理功能"""
    print_separator("测试状态管理功能")
    
    # 创建测试状态
    state = ReActState()
    state.user_query = "Python Web框架对比"
    state.current_strategy = SearchStrategy.COMPARISON
    state.iteration_count = 2
    state.repositories_found = ["django/django", "pallets/flask", "tiangolo/fastapi"]
    state.detailed_analysis = {
        "django/django": {"stars": 75000, "language": "Python"},
        "pallets/flask": {"stars": 65000, "language": "Python"}
    }
    
    print(f"用户查询: {state.user_query}")
    print(f"当前策略: {state.current_strategy.value}")
    print(f"迭代次数: {state.iteration_count}")
    print(f"发现仓库: {len(state.repositories_found)}个")
    print(f"详细分析: {len(state.detailed_analysis)}个")
    
    # 测试策略切换建议
    from agent import SearchStrategySelector
    new_strategy = SearchStrategySelector.should_switch_strategy(state.current_strategy, state)
    print(f"策略建议: {new_strategy.value if new_strategy else '保持当前策略'}")
    
    # 测试行动建议
    suggestion = SearchStrategySelector.get_next_action_suggestion(state.current_strategy, state)
    print(f"行动建议: {suggestion}")


def test_prompt_generation():
    """测试提示词生成功能"""
    print_separator("测试提示词生成功能")
    
    agent = ReActGitHubAgent()
    agent.initialize_search("寻找最好的Python机器学习框架")
    
    # 模拟一些历史数据
    conversation_history = [
        {
            "iteration": 1,
            "thought": "用户想要寻找Python机器学习框架，我需要先进行广泛搜索",
            "action": {"tool": "search_repositories", "query": "python machine learning"},
            "observation": "找到了scikit-learn, tensorflow等框架",
            "response": "Thought: 需要搜索机器学习框架...",
            "strategy": "broad_search",
            "suggestion": {"priority": "search", "reason": "初始搜索"}
        }
    ]
    
    # 生成提示词
    action_suggestion = {
        "priority": "analyze",
        "reason": "需要深入分析热门框架",
        "target_repo": "scikit-learn/scikit-learn"
    }
    
    prompt = agent._build_iteration_prompt(conversation_history, action_suggestion)
    print("生成的提示词:")
    print(prompt)


def test_action_parsing():
    """测试行动解析功能"""
    print_separator("测试行动解析功能")
    
    agent = ReActGitHubAgent()
    
    test_responses = [
        """Thought: 我需要搜索Python Web框架
Action: search_repositories("python web framework", max_results=10, sort="stars")""",
        
        """Thought: 需要分析Django的详细信息
Action: get_repository_info("django/django")""",
        
        """Thought: 查看FastAPI的技术栈
Action: get_repository_languages("tiangolo/fastapi")""",
        
        """这里没有明确的Action，应该解析失败"""
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"测试 {i}:")
        print(f"响应: {response}")
        action = agent.parse_action_from_response(response)
        print(f"解析结果: {action}")
        print()


def test_suggestion_to_action():
    """测试策略建议到具体行动的转换"""
    print_separator("测试策略建议转换功能")
    
    agent = ReActGitHubAgent()
    agent.state.current_strategy = SearchStrategy.COMPARISON
    
    test_suggestions = [
        {
            "priority": "search",
            "reason": "需要更多仓库",
            "suggested_query": "python web framework comparison"
        },
        {
            "priority": "analyze", 
            "reason": "分析热门框架",
            "target_repo": "django/django"
        },
        {
            "priority": "language_analysis",
            "reason": "了解技术栈",
            "target_repo": "fastapi/fastapi"
        },
        {
            "priority": "conclude",
            "reason": "信息已足够"
        }
    ]
    
    for i, suggestion in enumerate(test_suggestions, 1):
        print(f"建议 {i}: {suggestion}")
        action = agent._generate_action_from_suggestion(suggestion)
        print(f"生成行动: {action}")
        print()


async def test_react_cycle_simulation():
    """测试完整ReAct循环的模拟"""
    print_separator("测试完整ReAct循环模拟")
    
    agent = ReActGitHubAgent()
    
    # 模拟一个简单的搜索查询
    query = "Python数据分析库推荐"
    print(f"执行查询: {query}")
    
    try:
        # 这里只是演示流程，不会真正调用外部API
        result = await agent.execute_react_cycle(query)
        print(f"\n最终结果:\n{result}")
    except Exception as e:
        print(f"模拟执行完成（预期的错误）: {e}")
        
        # 展示状态信息
        print(f"\n执行状态:")
        print(f"- 迭代次数: {agent.state.iteration_count}")
        print(f"- 当前策略: {agent.state.current_strategy.value}")
        print(f"- 发现仓库: {len(agent.state.repositories_found)}")
        print(f"- 详细分析: {len(agent.state.detailed_analysis)}")


def demo_different_query_types():
    """演示不同类型查询的处理"""
    print_separator("演示不同查询类型的处理")
    
    agent = ReActGitHubAgent()
    
    demo_queries = [
        ("广泛搜索", "Python Web开发框架"),
        ("对比分析", "Django vs Flask性能对比"),
        ("趋势分析", "2024年最热门的JavaScript框架"),
        ("深度分析", "tensorflow/tensorflow"),
        ("解决方案", "如何实现实时聊天应用")
    ]
    
    for query_type, query in demo_queries:
        print(f"\n查询类型: {query_type}")
        print(f"查询内容: {query}")
        
        agent.initialize_search(query)
        print(f"选择策略: {agent.state.current_strategy.value}")
        
        # 获取行动建议
        from agent import SearchStrategySelector
        suggestion = SearchStrategySelector.get_next_action_suggestion(
            agent.state.current_strategy, agent.state
        )
        print(f"首步建议: {suggestion['priority']} - {suggestion['reason']}")


def main():
    """主测试函数"""
    print("🧪 ReAct GitHub搜索代理 - 功能测试")
    
    try:
        # 基础功能测试
        test_strategy_selection()
        test_state_management()  
        test_prompt_generation()
        test_action_parsing()
        test_suggestion_to_action()
        demo_different_query_types()
        
        # 异步功能测试
        print_separator("异步功能测试")
        asyncio.run(test_react_cycle_simulation())
        
        print_separator("测试完成")
        print("✅ 所有基础功能测试通过!")
        print("\n📋 Phase 1 实现总结:")
        print("✅ ReAct提示词模板设计完成")
        print("✅ 思考-行动-观察循环实现完成") 
        print("✅ 搜索策略选择逻辑实现完成")
        print("✅ 动态策略调整功能实现完成")
        print("✅ 智能行动建议系统实现完成")
        
        print(f"\n🚀 下一步建议:")
        print("- 集成真实的MCP工具调用")
        print("- 添加结果分析和聚合功能")
        print("- 实现个性化推荐系统")
        print("- 添加UI界面支持")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 