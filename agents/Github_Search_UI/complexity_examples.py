#!/usr/bin/env python3
"""
搜索复杂度判断示例演示
展示智能路由器如何分析不同查询的复杂度并选择合适的代理模式
"""

from typing import Dict, Any
from enum import Enum

class AgentMode(Enum):
    PLAN_EXECUTE = "plan_execute"
    REACT = "react"

def analyze_query_complexity_demo(query: str) -> Dict[str, Any]:
    """演示版本的复杂度分析"""
    query_lower = query.lower()
    
    # 复杂度指标
    complexity_score = 0
    features = {
        "is_comparison": False,
        "is_multi_step": False,
        "is_complex_analysis": False,
        "is_simple_search": False,
        "has_specific_requirements": False,
        "word_count": len(query.split()),
        "complexity_keywords": 0
    }
    
    analysis_log = []
    
    # 对比分析关键词 (+3分)
    comparison_keywords = ['vs', '对比', '比较', '哪个更好', '差异', '选择', '推荐']
    if any(keyword in query_lower for keyword in comparison_keywords):
        features["is_comparison"] = True
        complexity_score += 3
        analysis_log.append("✅ 检测到对比分析需求 (+3分)")
    
    # 多步骤分析关键词 (+2分)
    multi_step_keywords = ['分析', '研究', '深入', '详细', '全面', '系统性']
    if any(keyword in query_lower for keyword in multi_step_keywords):
        features["is_multi_step"] = True
        complexity_score += 2
        analysis_log.append("✅ 检测到多步骤分析需求 (+2分)")
    
    # 复杂分析关键词 (每个+2分)
    complex_keywords = ['架构', '设计模式', '技术栈', '最佳实践', '性能对比', '技术选型']
    complex_count = sum(1 for keyword in complex_keywords if keyword in query_lower)
    if complex_count > 0:
        features["is_complex_analysis"] = True
        features["complexity_keywords"] = complex_count
        complexity_score += complex_count * 2
        analysis_log.append(f"✅ 检测到{complex_count}个复杂技术关键词 (+{complex_count * 2}分)")
    
    # 特定需求关键词 (+1分)
    requirement_keywords = ['如何', '怎么', '实现', '解决', '方案', '教程']
    if any(keyword in query_lower for keyword in requirement_keywords):
        features["has_specific_requirements"] = True
        complexity_score += 1
        analysis_log.append("✅ 检测到特定需求表达 (+1分)")
    
    # 简单搜索判断
    if features["word_count"] <= 3 and complexity_score == 0:
        features["is_simple_search"] = True
        analysis_log.append("✅ 识别为简单搜索查询")
    
    # 基于词数的复杂度 (+1分)
    if features["word_count"] > 8:
        complexity_score += 1
        analysis_log.append(f"✅ 查询较长({features['word_count']}词) (+1分)")
    
    return {
        "complexity_score": complexity_score,
        "features": features,
        "analysis_log": analysis_log
    }

def decide_agent_mode_demo(query: str) -> Dict[str, Any]:
    """演示版本的模式决策"""
    analysis = analyze_query_complexity_demo(query)
    complexity_score = analysis["complexity_score"]
    features = analysis["features"]
    
    decision_reasons = []
    selected_mode = None
    
    # 推荐Plan and Execute的情况
    if complexity_score >= 4:
        selected_mode = AgentMode.PLAN_EXECUTE
        decision_reasons.append(f"🎯 高复杂度查询 (分数: {complexity_score} ≥ 4)")
    
    elif features["is_comparison"] and features["is_multi_step"]:
        selected_mode = AgentMode.PLAN_EXECUTE
        decision_reasons.append("🎯 需要对比分析 + 多步骤处理")
    
    elif features["is_complex_analysis"] and features["complexity_keywords"] >= 2:
        selected_mode = AgentMode.PLAN_EXECUTE
        decision_reasons.append(f"🎯 复杂技术分析 ({features['complexity_keywords']}个关键词)")
    
    elif features["word_count"] > 10:
        selected_mode = AgentMode.PLAN_EXECUTE
        decision_reasons.append(f"🎯 查询描述复杂 ({features['word_count']}词 > 10)")
    
    # 推荐ReAct的情况
    elif features["is_simple_search"] or complexity_score <= 1:
        selected_mode = AgentMode.REACT
        decision_reasons.append("⚡ 简单搜索，ReAct更高效")
    
    # 默认使用Plan and Execute
    else:
        selected_mode = AgentMode.PLAN_EXECUTE
        decision_reasons.append("🛡️ 默认选择Plan and Execute (更稳定)")
    
    return {
        "query": query,
        "analysis": analysis,
        "selected_mode": selected_mode.value,
        "decision_reasons": decision_reasons
    }

# 🧪 测试用例
test_queries = [
    # 简单搜索 - 应该选择ReAct
    "Vue组件库",
    "Python爬虫",
    "JWT认证",
    
    # 中等复杂度 - 可能选择Plan&Execute
    "如何实现微服务架构",
    "Spring Boot最佳实践",
    "前端技术栈选型方案",
    
    # 高复杂度 - 应该选择Plan&Execute  
    "Django vs Flask vs FastAPI性能对比分析",
    "基于React和Node.js的全栈开发架构设计模式研究",
    "深入分析微服务架构中的服务发现和负载均衡最佳实践",
]

def run_complexity_demo():
    """运行复杂度分析演示"""
    print("🧠 搜索复杂度判断机制演示")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 示例 {i}: {query}")
        print("-" * 50)
        
        result = decide_agent_mode_demo(query)
        analysis = result["analysis"]
        
        # 显示分析过程
        print(f"📊 词数统计: {analysis['features']['word_count']}个词")
        print(f"🔍 分析过程:")
        for log in analysis["analysis_log"]:
            print(f"   {log}")
        
        # 显示最终结果
        print(f"📈 复杂度分数: {analysis['complexity_score']}")
        print(f"🎯 选择模式: {result['selected_mode'].upper()}")
        print(f"💡 决策依据: {', '.join(result['decision_reasons'])}")
        
        # 特征总结
        features = analysis['features']
        feature_summary = []
        if features['is_comparison']: feature_summary.append("对比分析")
        if features['is_multi_step']: feature_summary.append("多步骤")
        if features['is_complex_analysis']: feature_summary.append("复杂技术")
        if features['has_specific_requirements']: feature_summary.append("特定需求")
        if features['is_simple_search']: feature_summary.append("简单搜索")
        
        if feature_summary:
            print(f"🏷️ 查询特征: {', '.join(feature_summary)}")
        
        print()

if __name__ == "__main__":
    run_complexity_demo()
    
    print("\n📋 复杂度评估规则总结:")
    print("=" * 60)
    print("🎯 Plan and Execute 适用于:")
    print("   • 复杂度分数 ≥ 4")
    print("   • 对比分析 + 多步骤处理")
    print("   • 复杂技术关键词 ≥ 2个")  
    print("   • 查询描述 > 10个词")
    print()
    print("⚡ ReAct 适用于:")
    print("   • 简单搜索 (≤3词且无复杂关键词)")
    print("   • 复杂度分数 ≤ 1")
    print()
    print("🛡️ 默认情况: Plan and Execute (更稳定)") 