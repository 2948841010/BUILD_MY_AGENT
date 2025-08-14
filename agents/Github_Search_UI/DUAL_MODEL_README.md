# 双模型Plan and Execute GitHub搜索代理

## 🚀 架构概述

我们成功将原来的单模型ReAct架构升级为更智能的**双模型Plan and Execute架构**。

### 🔧 核心组件

#### 1. **PlanningAgent (规划代理)**
- 🎯 **职责**: 分析用户查询，制定详细的搜索策略和执行计划
- 🧠 **智能**: 专门优化的提示词，专注于策略规划和任务分解
- 📋 **输出**: 结构化的搜索计划，包括步骤序列、成功标准等

#### 2. **ExecutionAgent (执行代理)**  
- ⚡ **职责**: 根据计划精确执行搜索和分析任务
- 🔗 **工具**: 连接MCP工具集，进行实际的GitHub API调用
- 📊 **特长**: 结果解析、状态跟踪、质量评估

#### 3. **PlanAndExecuteGitHubAgent (主协调代理)**
- 🎼 **职责**: 协调两个专业代理，管理完整的工作流程
- 🔄 **流程**: Planning → Execution → Analysis 三阶段
- 🛡️ **智能**: 错误处理、成功标准检查、动态调整

## 🎯 架构优势

### vs 单模型ReAct架构
| 特性 | 单模型ReAct | 双模型Plan&Execute |
|------|-------------|-------------------|
| **分工** | 一个模型处理所有任务 | 专业化分工，各司其职 |
| **策略** | 实时策略调整 | 预先制定完整计划 |
| **执行** | 边思考边执行 | 专注精确执行 |
| **质量** | 容易偏离目标 | 目标导向，结果可控 |
| **扩展性** | 修改困难 | 可独立优化各模块 |

## 📚 使用方式

### 1. 推荐方式：直接使用双模型代理
```python
from agent import plan_execute_agent

# 异步使用
result = await plan_execute_agent.search("spring boot vue 项目")

# 同步使用  
from agent import search_github
result = search_github("spring boot vue 项目")
```

### 2. 便捷接口
```python
# 异步便捷接口
from agent import async_search_github
result = await async_search_github("python web framework")

# 同步便捷接口 (自动处理事件循环)
from agent import search_github  
result = search_github("react typescript ui组件库")
```

### 3. 创建自定义实例
```python
from agent import PlanAndExecuteGitHubAgent

# 可指定不同的模型
agent = PlanAndExecuteGitHubAgent(
    planner_model="deepseek/deepseek-chat",
    executor_model="deepseek/deepseek-chat"
)

result = await agent.search("你的查询")
```

## 📊 结果格式

```json
{
  "user_query": "用户查询",
  "plan": {
    "strategy": "选择的策略",
    "total_steps": "计划步骤数",
    "success_criteria": ["成功标准列表"],
    "expected_results": {"预期结果"}
  },
  "execution": {
    "completed_steps": "完成的步骤数",
    "successful_steps": "成功的步骤数", 
    "discovered_repos": "发现的仓库数",
    "analyzed_repos": "分析的仓库数",
    "execution_time": "执行时间"
  },
  "results": {
    "summary": "分析摘要",
    "discovered_repositories": ["仓库列表"],
    "detailed_analysis": {"仓库": "分析数据"},
    "success_rate": "成功率",
    "key_findings": ["关键发现"]
  },
  "recommendation": ["建议列表"]
}
```

## 🔍 搜索策略

系统会根据用户查询自动选择最合适的策略：

- **BROAD_SEARCH**: 广泛搜索，发现多个相关项目
- **DEEP_ANALYSIS**: 深度分析特定仓库的技术细节  
- **COMPARISON**: 对比多个同类项目的优劣
- **TREND_ANALYSIS**: 分析技术趋势和流行度
- **SOLUTION_FOCUSED**: 解决方案导向的精准搜索

## 🛠️ 向后兼容性

原有的ReAct代理仍然可用：
```python
from agent import react_agent

# 原有方式仍然支持
result = react_agent.search("查询内容")
```

## 🎉 测试验证

运行测试脚本验证功能：
```bash
python test_dual_model.py
```

预期看到：
```
🎯 总体结果: 4/4 个测试通过
🎉 所有测试通过! 双模型架构工作正常
```

## 📈 性能特点

- ✅ **智能规划**: 专业规划模型制定合理策略
- ✅ **精确执行**: 专业执行模型确保工具调用准确
- ✅ **错误恢复**: 智能的错误处理和备用机制
- ✅ **成功标准**: 自动检测是否达成目标
- ✅ **动态调整**: 根据执行情况调整策略
- ✅ **兼容性强**: 无缝集成到现有ADK系统

双模型架构代表了AI代理设计的最佳实践，将规划与执行分离，实现更智能、更可控的GitHub仓库搜索体验！ 