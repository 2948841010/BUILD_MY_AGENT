import os
import asyncio
import ssl
import httpx
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool


class SearchStrategy(Enum):
    """搜索策略枚举"""
    BROAD_SEARCH = "broad_search"           # 广泛搜索
    DEEP_ANALYSIS = "deep_analysis"         # 深度分析  
    COMPARISON = "comparison"               # 对比分析
    TREND_ANALYSIS = "trend_analysis"       # 趋势分析
    SOLUTION_FOCUSED = "solution_focused"   # 解决方案导向


class ModelRole(Enum):
    """模型角色枚举"""
    PLANNER = "planner"      # 规划模型
    EXECUTOR = "executor"    # 执行模型


@dataclass
class SearchPlan:
    """搜索计划数据结构"""
    user_query: str
    strategy: SearchStrategy
    planned_steps: List[Dict[str, Any]] = None
    success_criteria: List[str] = None
    expected_results: Dict[str, Any] = None
    priority_actions: List[str] = None
    
    def __post_init__(self):
        if self.planned_steps is None:
            self.planned_steps = []
        if self.success_criteria is None:
            self.success_criteria = []
        if self.expected_results is None:
            self.expected_results = {}
        if self.priority_actions is None:
            self.priority_actions = []


@dataclass 
class ExecutionResult:
    """执行结果数据结构"""
    step_id: str
    tool_used: str
    success: bool
    result_data: Any
    observations: str
    next_recommendations: List[str] = None
    
    def __post_init__(self):
        if self.next_recommendations is None:
            self.next_recommendations = []


@dataclass
class ReActState:
    """ReAct状态管理"""
    user_query: str = ""
    current_thought: str = ""
    planned_actions: List[str] = None
    search_history: List[Dict] = None
    repositories_found: List[str] = None
    detailed_analysis: Dict[str, Any] = None
    current_strategy: SearchStrategy = SearchStrategy.BROAD_SEARCH
    iteration_count: int = 0
    max_iterations: int = 5
    
    def __post_init__(self):
        if self.planned_actions is None:
            self.planned_actions = []
        if self.search_history is None:
            self.search_history = []
        if self.repositories_found is None:
            self.repositories_found = []
        if self.detailed_analysis is None:
            self.detailed_analysis = {}


class PlanningAgent:
    """规划代理 - 负责分析用户查询并制定详细的搜索计划"""
    
    def __init__(self, model_name: str = "deepseek/deepseek-chat"):
        """初始化规划代理"""
        self.model = LiteLlm(model=model_name)
        self.agent = None
        self._setup_agent()
    
    def _setup_agent(self):
        """设置规划代理"""
        system_prompt = self._get_planning_system_prompt()
        self.agent = Agent(
            name="planning_agent",
            model=self.model,
            instruction=system_prompt,
            tools=[]  # 规划阶段不需要工具
        )
    
    def _get_planning_system_prompt(self) -> str:
        """获取规划代理的系统提示词"""
        return """你是一个GitHub仓库搜索规划专家。你的任务是分析用户查询，制定详细的搜索和分析计划。

核心职责：
1. 深度理解用户的真实需求和目标
2. 选择最合适的搜索策略 
3. 制定具体的执行步骤序列
4. 定义成功标准和预期结果

可选搜索策略：
- BROAD_SEARCH: 广泛搜索，发现多个相关项目
- DEEP_ANALYSIS: 深度分析特定仓库的技术细节
- COMPARISON: 对比多个同类项目的优劣
- TREND_ANALYSIS: 分析技术趋势和流行度
- SOLUTION_FOCUSED: 解决方案导向的精准搜索

可用工具（供执行阶段使用）：
- search_repositories: 搜索GitHub仓库
- get_repository_info: 获取仓库详细信息
- get_repository_languages: 获取编程语言统计
- get_repository_tree: 获取仓库目录结构  
- get_repository_file_content: 获取仓库文件内容

输出格式要求：
请以JSON格式返回详细计划，包含：
1. strategy: 选择的搜索策略
2. planned_steps: 具体执行步骤列表
3. success_criteria: 成功标准
4. expected_results: 预期结果描述
5. priority_actions: 优先级行动列表

示例：
{
  "strategy": "BROAD_SEARCH",
  "planned_steps": [
    {"step": 1, "action": "search_repositories", "query": "spring boot vue", "max_results": 10},
    {"step": 2, "action": "get_repository_info", "target": "top_3_repos"},
    {"step": 3, "action": "get_repository_languages", "target": "analyzed_repos"}
  ],
  "success_criteria": ["找到至少5个相关项目", "获得详细的技术栈信息"],
  "expected_results": {"repo_count": 5, "analysis_depth": "medium"},
  "priority_actions": ["优先分析star数最高的项目", "关注最近更新的项目"]
}
"""
    
    async def create_plan(self, user_query: str) -> SearchPlan:
        """创建搜索计划"""
        try:
            # 构建规划提示
            planning_prompt = f"""
用户查询: {user_query}

请分析这个查询的核心需求，制定详细的GitHub仓库搜索和分析计划。
考虑用户可能的真实目标，选择最合适的策略，并给出具体的执行步骤。
"""
            
            # 调用规划模型
            runner = InMemoryRunner(agent=self.agent)
            session_service = InMemorySessionService()
            
            # 创建session的正确方式
            try:
                session = await session_service.start_session()
            except AttributeError:
                # 如果start_session方法不存在，使用create_session
                session = session_service.create_session()
            
            response = await runner.run(
                session=session,
                user_message=planning_prompt
            )
            
            # 解析响应并创建计划
            plan_data = self._parse_plan_response(response.content if hasattr(response, 'content') else str(response))
            
            return SearchPlan(
                user_query=user_query,
                strategy=SearchStrategy(plan_data.get('strategy', 'BROAD_SEARCH')),
                planned_steps=plan_data.get('planned_steps', []),
                success_criteria=plan_data.get('success_criteria', []),
                expected_results=plan_data.get('expected_results', {}),
                priority_actions=plan_data.get('priority_actions', [])
            )
            
        except Exception as e:
            print(f"规划创建失败: {str(e)}")
            # 返回默认计划
            return self._create_fallback_plan(user_query)
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """解析规划响应"""
        try:
            # 尝试提取JSON
            import json
            
            # 查找JSON块
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
                return plan_data
        except:
            pass
        
        # 如果无法解析JSON，使用文本解析
        return self._parse_plan_text(response)
    
    def _parse_plan_text(self, response: str) -> Dict[str, Any]:
        """从文本中解析计划信息"""
        plan_data = {
            'strategy': 'BROAD_SEARCH',
            'planned_steps': [],
            'success_criteria': [],
            'expected_results': {},
            'priority_actions': []
        }
        
        # 简单的文本解析逻辑
        if '对比' in response or '比较' in response:
            plan_data['strategy'] = 'COMPARISON'
        elif '深度' in response or '详细' in response:
            plan_data['strategy'] = 'DEEP_ANALYSIS'
        elif '趋势' in response or '流行' in response:
            plan_data['strategy'] = 'TREND_ANALYSIS'
        elif '解决' in response or '方案' in response:
            plan_data['strategy'] = 'SOLUTION_FOCUSED'
        
        return plan_data
    
    def _create_fallback_plan(self, user_query: str) -> SearchPlan:
        """创建备用计划"""
        # 基于查询内容的简单策略选择
        strategy = SearchStrategySelector.analyze_query_intent(user_query)
        
        return SearchPlan(
            user_query=user_query,
            strategy=strategy,
            planned_steps=[
                {"step": 1, "action": "search_repositories", "query": user_query, "max_results": 8},
                {"step": 2, "action": "get_repository_info", "target": "top_repos"},
            ],
            success_criteria=["找到相关仓库", "获取基本信息"],
            expected_results={"repo_count": 5},
            priority_actions=["优先分析高star项目"]
        )


class ExecutionAgent:
    """执行代理 - 负责根据计划执行具体的搜索和分析任务"""
    
    def __init__(self, model_name: str = "deepseek/deepseek-chat"):
        """初始化执行代理"""
        self.model = LiteLlm(model=model_name)
        self.agent = None
        self.toolset = None
        self._setup_ssl()
        self._setup_agent()
        
        # 执行状态跟踪
        self.execution_history: List[ExecutionResult] = []
        self.discovered_repos: List[str] = []
        self.repo_analysis: Dict[str, Any] = {}
    
    def _setup_ssl(self):
        """设置SSL配置"""
        os.environ['DEEPSEEK_API_KEY'] = os.getenv('DEEPSEEK_API_KEY', 'sk-86bc0ca023294b4d94596861c70c6f45')
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        except Exception as e:
            print(f"SSL配置警告: {e}")
    
    def _setup_agent(self):
        """设置执行代理"""
        # 配置MCP工具集
        self.toolset = MCPToolset(
            connection_params=SseServerParams(
                url="https://github-search1111-uuid1754995527.app-space.dplink.cc/sse?token=5bf79bd1192f4d109b079b15907f28ae",
            ),
        )
        
        system_prompt = self._get_execution_system_prompt()
        self.agent = Agent(
            name="execution_agent",
            model=self.model,
            instruction=system_prompt,
            tools=[self.toolset]
        )
    
    def _get_execution_system_prompt(self) -> str:
        """获取执行代理的系统提示词"""
        return """你是一个GitHub仓库搜索执行专家。你的任务是根据制定的计划，精确执行每个搜索和分析步骤。

核心职责：
1. 严格按照计划执行每个步骤
2. 使用合适的工具获取高质量数据
3. 对结果进行客观分析和观察
4. 提供下一步行动建议

执行原则：
- 精确性：严格按照计划参数执行
- 高效性：避免重复搜索，最大化信息获取
- 观察性：深入分析每个结果的价值
- 建议性：基于结果提供优化建议

可用工具：
- search_repositories(query, max_results, sort, search_mode): 搜索GitHub仓库
- get_repository_info(full_name): 获取仓库详细信息
- get_repository_languages(full_name): 获取编程语言统计
- get_repository_tree(full_name, path): 获取仓库目录结构
- get_repository_file_content(full_name, file_path, max_size): 获取仓库文件内容

输出格式：
对于每个执行步骤，请提供：
1. 明确的工具调用
2. 详细的结果观察
3. 数据质量评估
4. 下一步建议

保持客观和准确，专注于数据收集和分析。
"""
    
    async def execute_step(self, step: Dict[str, Any], plan: SearchPlan) -> ExecutionResult:
        """执行单个计划步骤"""
        step_id = f"step_{step.get('step', len(self.execution_history) + 1)}"
        action = step.get('action', '')
        
        print(f"🔧 执行步骤 {step_id}: {action}")
        
        try:
            # 构建执行提示
            execution_prompt = self._build_execution_prompt(step, plan)
            
            # 调用执行模型
            runner = InMemoryRunner(agent=self.agent)
            session_service = InMemorySessionService()
            
            # 创建session的正确方式
            try:
                session = await session_service.start_session()
            except AttributeError:
                # 如果start_session方法不存在，使用create_session
                session = session_service.create_session()
            
            response = await runner.run(
                session=session,
                user_message=execution_prompt
            )
            
            # 解析执行结果
            result_data = self._parse_execution_response(response.content if hasattr(response, 'content') else str(response))
            
            # 更新状态
            self._update_execution_state(step, result_data)
            
            # 创建执行结果
            execution_result = ExecutionResult(
                step_id=step_id,
                tool_used=action,
                success=True,
                result_data=result_data,
                observations=result_data.get('observations', ''),
                next_recommendations=result_data.get('next_recommendations', [])
            )
            
            self.execution_history.append(execution_result)
            return execution_result
            
        except Exception as e:
            print(f"❌ 执行步骤失败: {str(e)}")
            
            # 创建失败结果
            failure_result = ExecutionResult(
                step_id=step_id,
                tool_used=action,
                success=False,
                result_data={"error": str(e)},
                observations=f"执行失败: {str(e)}",
                next_recommendations=["检查网络连接", "尝试简化查询"]
            )
            
            self.execution_history.append(failure_result)
            return failure_result
    
    def _build_execution_prompt(self, step: Dict[str, Any], plan: SearchPlan) -> str:
        """构建执行提示"""
        action = step.get('action', '')
        step_num = step.get('step', 1)
        
        prompt_parts = [
            f"执行计划第 {step_num} 步",
            f"策略: {plan.strategy.value}",
            f"行动: {action}",
            f"用户原始查询: {plan.user_query}",
        ]
        
        # 添加具体参数
        if action == 'search_repositories':
            query = step.get('query', plan.user_query)
            max_results = step.get('max_results', 8)
            prompt_parts.extend([
                f"搜索查询: {query}",
                f"最大结果数: {max_results}",
                "请执行仓库搜索，分析结果质量和相关性。"
            ])
        
        elif action == 'get_repository_info':
            target = step.get('target', 'top_repos')
            if target == 'top_repos' and self.discovered_repos:
                target_repo = self.discovered_repos[0]
                prompt_parts.extend([
                    f"目标仓库: {target_repo}",
                    "请获取详细信息，包括stars、语言、描述等。"
                ])
            elif target in self.discovered_repos:
                prompt_parts.extend([
                    f"目标仓库: {target}",
                    "请获取详细信息。"
                ])
        
        elif action == 'get_repository_languages':
            if self.discovered_repos:
                target_repo = self.discovered_repos[0]
                prompt_parts.extend([
                    f"目标仓库: {target_repo}",
                    "请分析技术栈和编程语言分布。"
                ])
        
        # 添加执行历史上下文
        if self.execution_history:
            prompt_parts.append("\n📜 之前执行结果:")
            for result in self.execution_history[-2:]:  # 最近2次执行
                prompt_parts.append(f"- {result.step_id}: {result.tool_used} -> {result.success}")
        
        prompt_parts.append("\n请使用合适的工具执行这个步骤，并提供详细的观察和分析。")
        
        return "\n".join(prompt_parts)
    
    def _parse_execution_response(self, response: str) -> Dict[str, Any]:
        """解析执行响应"""
        # 模拟解析MCP工具的返回结果
        # 在实际实现中，这里会解析真正的工具调用结果
        
        result_data = {
            'observations': '',
            'data': {},
            'next_recommendations': []
        }
        
        # 提取观察部分
        if '观察' in response or 'Observation' in response:
            obs_match = re.search(r'(?:观察|Observation)[：:]\s*([^\n]+(?:\n(?!下一步|Next)[^\n]+)*)', response, re.IGNORECASE)
            if obs_match:
                result_data['observations'] = obs_match.group(1).strip()
        
        # 提取建议部分
        if '建议' in response or 'recommendation' in response.lower():
            rec_match = re.search(r'(?:建议|recommendation)[：:]\s*([^\n]+(?:\n(?![\-\*])[^\n]+)*)', response, re.IGNORECASE)
            if rec_match:
                recommendations = rec_match.group(1).strip().split('\n')
                result_data['next_recommendations'] = [r.strip('- ') for r in recommendations if r.strip()]
        
        return result_data
    
    def _update_execution_state(self, step: Dict[str, Any], result_data: Dict[str, Any]):
        """更新执行状态"""
        action = step.get('action', '')
        
        if action == 'search_repositories':
            # 模拟添加发现的仓库
            mock_repos = [f"example/repo{i}" for i in range(1, step.get('max_results', 8) + 1)]
            self.discovered_repos.extend(mock_repos)
        
        elif action == 'get_repository_info':
            # 模拟添加仓库分析
            if self.discovered_repos:
                repo = self.discovered_repos[0]
                self.repo_analysis[repo] = {
                    'stars': 1500,
                    'language': 'Python',
                    'description': '示例仓库描述',
                    'analyzed': True
                }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            'total_steps': len(self.execution_history),
            'successful_steps': len([r for r in self.execution_history if r.success]),
            'discovered_repos': len(self.discovered_repos),
            'analyzed_repos': len(self.repo_analysis),
            'execution_history': self.execution_history
        }


class ReActPromptEngine:
    """ReAct提示词引擎"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示词"""
        return """你是一个GitHub仓库研究专家，使用ReAct（Reasoning + Acting）方法进行深度分析。

ReAct工作流程：
1. **Thought**: 分析当前情况，制定下一步策略
2. **Action**: 选择合适的工具执行操作
3. **Observation**: 分析操作结果
4. **Reflection**: 评估是否需要进一步行动

可用工具：
- search_repositories(query, max_results, sort, search_mode): 搜索GitHub仓库，支持高级搜索模式
- get_repository_info(full_name): 获取仓库详细信息
- get_repository_languages(full_name): 获取编程语言统计
- get_repository_tree(full_name, path): 获取仓库目录结构
- get_repository_file_content(full_name, file_path, max_size): 获取仓库文件内容

搜索策略：
- BROAD_SEARCH: 广泛搜索，了解整体情况
- DEEP_ANALYSIS: 深度分析特定仓库
- COMPARISON: 对比分析多个仓库
- TREND_ANALYSIS: 分析趋势和流行度
- SOLUTION_FOCUSED: 解决方案导向搜索

思考框架：
- 用户的核心需求是什么？
- 我已有哪些信息？还缺少什么？
- 当前最合适的搜索策略是什么？
- 下一步应该采取什么行动？

格式要求：
- 必须在每次回应中明确标出：Thought、Action、Observation
- 如果信息足够，最后给出 Final Answer
- 保持逻辑清晰，循序渐进
"""

    @staticmethod
    def get_thought_template(state: ReActState) -> str:
        """获取思考提示模板"""
        return f"""
当前状态分析：
- 用户查询: {state.user_query}
- 当前策略: {state.current_strategy.value}
- 迭代次数: {state.iteration_count}/{state.max_iterations}
- 已找到仓库: {len(state.repositories_found)}个
- 已分析仓库: {len(state.detailed_analysis)}个

请进行思考分析：
Thought: [分析当前状况，思考下一步策略]
- 用户的核心需求是什么？
- 我已有哪些有用信息？
- 还缺少什么关键信息？
- 应该使用什么搜索策略？
- 最佳的下一步行动是什么？
"""

    @staticmethod
    def get_action_template() -> str:
        """获取行动提示模板"""
        return """
Action: [选择工具和参数，格式：工具名(参数)]
可选工具：
1. search_repositories(query="搜索关键词", max_results=数量, sort="排序方式", search_mode="simple/advanced")
   - 高级搜索: search_repositories(query="springboot AND vue", search_mode="advanced")
2. get_repository_info(full_name="owner/repo")
3. get_repository_languages(full_name="owner/repo")
4. get_repository_tree(full_name="owner/repo", path="") # 查看目录结构
5. get_repository_file_content(full_name="owner/repo", file_path="README.md")
"""

    @staticmethod
    def get_reflection_template(observation: str) -> str:
        """获取反思提示模板"""
        return f"""
Observation: {observation}

Reflection: [评估观察结果]
- 这个结果对回答用户问题有帮助吗？
- 信息是否足够完整？
- 是否需要进一步搜索？
- 如果需要，下一步应该怎么做？
"""


class SearchStrategySelector:
    """搜索策略选择器"""
    
    @staticmethod
    def analyze_query_intent(query: str) -> SearchStrategy:
        """分析查询意图，选择合适的搜索策略"""
        query_lower = query.lower()
        
        # 对比类查询
        comparison_keywords = ['比较', '对比', '哪个更好', 'vs', '差异', '选择', '推荐']
        if any(keyword in query_lower for keyword in comparison_keywords):
            return SearchStrategy.COMPARISON
            
        # 趋势分析类查询
        trend_keywords = ['最新', '热门', '流行', '趋势', '最佳', '2024', '2025', 'trending']
        if any(keyword in query_lower for keyword in trend_keywords):
            return SearchStrategy.TREND_ANALYSIS
            
        # 解决方案导向查询
        solution_keywords = ['如何', '怎么', '实现', '解决', '方法', 'how to', 'solution']
        if any(keyword in query_lower for keyword in solution_keywords):
            return SearchStrategy.SOLUTION_FOCUSED
            
        # 深度分析查询（包含特定项目名）
        if '/' in query or len(query.split()) <= 2:
            return SearchStrategy.DEEP_ANALYSIS
            
        # 默认使用广泛搜索
        return SearchStrategy.BROAD_SEARCH
    
    @staticmethod
    def get_search_parameters(strategy: SearchStrategy, query: str) -> Dict[str, Any]:
        """根据策略获取搜索参数"""
        params = {
            SearchStrategy.BROAD_SEARCH: {
                "max_results": 8,
                "sort": "stars"
            },
            SearchStrategy.DEEP_ANALYSIS: {
                "max_results": 3,
                "sort": "stars"
            },
            SearchStrategy.COMPARISON: {
                "max_results": 10,
                "sort": "stars"
            },
            SearchStrategy.TREND_ANALYSIS: {
                "max_results": 15,
                "sort": "updated"
            },
            SearchStrategy.SOLUTION_FOCUSED: {
                "max_results": 12,
                "sort": "stars"
            }
        }
        return params.get(strategy, params[SearchStrategy.BROAD_SEARCH])
    
    @staticmethod
    def should_switch_strategy(current_strategy: SearchStrategy, state: 'ReActState') -> Optional[SearchStrategy]:
        """动态策略切换判断"""
        iteration = state.iteration_count
        found_repos = len(state.repositories_found)
        analyzed_repos = len(state.detailed_analysis)
        
        # 如果广泛搜索没找到足够的仓库，切换到解决方案导向
        if (current_strategy == SearchStrategy.BROAD_SEARCH and 
            iteration >= 2 and found_repos < 3):
            return SearchStrategy.SOLUTION_FOCUSED
        
        # 如果找到很多仓库但缺乏深度分析，切换到深度分析
        if (found_repos >= 5 and analyzed_repos < 2 and 
            current_strategy != SearchStrategy.DEEP_ANALYSIS):
            return SearchStrategy.DEEP_ANALYSIS
        
        # 如果是对比策略但找到的仓库不够，切换到广泛搜索
        if (current_strategy == SearchStrategy.COMPARISON and 
            iteration >= 2 and found_repos < 3):
            return SearchStrategy.BROAD_SEARCH
        
        return None
    
    @staticmethod
    def get_next_action_suggestion(strategy: SearchStrategy, state: 'ReActState') -> Dict[str, Any]:
        """根据策略和状态建议下一步行动"""
        found_repos = len(state.repositories_found)
        analyzed_repos = len(state.detailed_analysis)
        
        if strategy == SearchStrategy.BROAD_SEARCH:
            if found_repos == 0:
                return {
                    "priority": "search",
                    "reason": "首先需要发现相关仓库",
                    "suggested_query": state.user_query
                }
            elif analyzed_repos < min(3, found_repos):
                return {
                    "priority": "analyze",
                    "reason": "需要深入分析已发现的仓库",
                    "target_repo": state.repositories_found[analyzed_repos]
                }
        
        elif strategy == SearchStrategy.COMPARISON:
            if found_repos < 3:
                return {
                    "priority": "search",
                    "reason": "对比分析需要更多候选仓库",
                    "suggested_query": state.user_query
                }
            elif analyzed_repos < min(3, found_repos):
                return {
                    "priority": "analyze",
                    "reason": "需要获取对比数据",
                    "target_repo": state.repositories_found[analyzed_repos]
                }
        
        elif strategy == SearchStrategy.DEEP_ANALYSIS:
            if found_repos == 0:
                return {
                    "priority": "search",
                    "reason": "需要先找到目标仓库",
                    "suggested_query": state.user_query
                }
            elif analyzed_repos == 0:
                return {
                    "priority": "analyze",
                    "reason": "进行深度分析",
                    "target_repo": state.repositories_found[0]
                }
            elif analyzed_repos < 2:
                return {
                    "priority": "language_analysis",
                    "reason": "分析技术栈",
                    "target_repo": state.repositories_found[0]
                }
        
        elif strategy == SearchStrategy.TREND_ANALYSIS:
            if found_repos < 10:
                return {
                    "priority": "search",
                    "reason": "趋势分析需要更多样本",
                    "suggested_query": state.user_query
                }
            elif analyzed_repos < 5:
                return {
                    "priority": "analyze",
                    "reason": "分析热门项目特征",
                    "target_repo": state.repositories_found[analyzed_repos]
                }
        
        elif strategy == SearchStrategy.SOLUTION_FOCUSED:
            if found_repos < 5:
                return {
                    "priority": "search",
                    "reason": "寻找更多解决方案",
                    "suggested_query": f"{state.user_query} solution implementation"
                }
            elif analyzed_repos < 3:
                return {
                    "priority": "analyze",
                    "reason": "评估解决方案质量",
                    "target_repo": state.repositories_found[analyzed_repos]
                }
        
        return {
            "priority": "conclude",
            "reason": "已收集足够信息，可以总结",
        }


class PlanAndExecuteGitHubAgent:
    """Plan and Execute GitHub搜索代理 - 双模型协作架构"""
    
    def __init__(self, planner_model: str = "deepseek/deepseek-chat", executor_model: str = "deepseek/deepseek-chat"):
        """初始化双模型代理"""
        self.planner = PlanningAgent(planner_model)
        self.executor = ExecutionAgent(executor_model)
        
        # 协作状态
        self.current_plan: Optional[SearchPlan] = None
        self.plan_execution_status: Dict[str, Any] = {}
        
    async def search(self, user_query: str) -> Dict[str, Any]:
        """执行完整的Plan and Execute搜索流程"""
        print(f"🚀 启动Plan and Execute GitHub搜索")
        print(f"📝 用户查询: {user_query}")
        print("=" * 60)
        
        try:
            # Phase 1: Planning - 制定搜索计划
            print("\n📋 阶段一：计划制定 (Planning)")
            print("-" * 30)
            
            plan_start_time = asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0
            self.current_plan = await self.planner.create_plan(user_query)
            plan_duration = (asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0) - plan_start_time
            
            print(f"✅ 计划制定完成 (耗时: {plan_duration:.2f}s)")
            print(f"🎯 选择策略: {self.current_plan.strategy.value}")
            print(f"📊 计划步骤: {len(self.current_plan.planned_steps)}个")
            print(f"🎯 成功标准: {', '.join(self.current_plan.success_criteria)}")
            
            # Phase 2: Execution - 执行计划步骤
            print(f"\n⚡ 阶段二：计划执行 (Execution)")
            print("-" * 30)
            
            execution_results = []
            execution_start_time = asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0
            
            for i, step in enumerate(self.current_plan.planned_steps, 1):
                print(f"\n🔧 执行步骤 {i}/{len(self.current_plan.planned_steps)}")
                
                result = await self.executor.execute_step(step, self.current_plan)
                execution_results.append(result)
                
                print(f"   ✅ 状态: {'成功' if result.success else '失败'}")
                print(f"   📝 观察: {result.observations[:100]}...")
                
                # 检查是否需要提前终止
                if not result.success and self._should_abort_execution(execution_results):
                    print(f"⚠️ 检测到关键失败，提前终止执行")
                    break
                
                # 检查是否满足成功标准
                if self._check_success_criteria(self.current_plan, execution_results):
                    print(f"🎉 达成成功标准，提前完成")
                    break
            
            execution_duration = (asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0) - execution_start_time
            
            # Phase 3: Analysis and Summary - 分析和总结
            print(f"\n📊 阶段三：结果分析 (Analysis)")
            print("-" * 30)
            
            analysis_result = await self._analyze_results(self.current_plan, execution_results)
            
            print(f"✅ 执行完成 (耗时: {execution_duration:.2f}s)")
            print(f"📈 成功率: {len([r for r in execution_results if r.success])}/{len(execution_results)}")
            
            # 构建最终结果
            final_result = {
                'user_query': user_query,
                'plan': {
                    'strategy': self.current_plan.strategy.value,
                    'total_steps': len(self.current_plan.planned_steps),
                    'success_criteria': self.current_plan.success_criteria,
                    'expected_results': self.current_plan.expected_results
                },
                'execution': {
                    'completed_steps': len(execution_results),
                    'successful_steps': len([r for r in execution_results if r.success]),
                    'discovered_repos': len(self.executor.discovered_repos),
                    'analyzed_repos': len(self.executor.repo_analysis),
                    'execution_time': execution_duration
                },
                'results': analysis_result,
                'recommendation': self._generate_recommendations(execution_results)
            }
            
            print(f"\n🎯 最终结果已生成")
            return final_result
            
        except Exception as e:
            print(f"❌ Plan and Execute执行失败: {str(e)}")
            return {
                'error': str(e),
                'user_query': user_query,
                'status': 'failed'
            }
    
    def _should_abort_execution(self, execution_results: List[ExecutionResult]) -> bool:
        """判断是否应该中止执行"""
        if len(execution_results) < 2:
            return False
        
        # 如果连续2个步骤失败，中止执行
        recent_failures = [not r.success for r in execution_results[-2:]]
        if all(recent_failures):
            return True
        
        # 如果关键的第一步失败，中止执行
        if execution_results[0].tool_used == 'search_repositories' and not execution_results[0].success:
            return True
        
        return False
    
    def _check_success_criteria(self, plan: SearchPlan, execution_results: List[ExecutionResult]) -> bool:
        """检查是否满足成功标准"""
        if not plan.success_criteria:
            return False
        
        discovered_count = len(self.executor.discovered_repos)
        analyzed_count = len(self.executor.repo_analysis)
        
        # 检查各种成功标准
        for criteria in plan.success_criteria:
            if '找到' in criteria and '5' in criteria and discovered_count >= 5:
                return True
            if '分析' in criteria and '3' in criteria and analyzed_count >= 3:
                return True
        
        return False
    
    async def _analyze_results(self, plan: SearchPlan, execution_results: List[ExecutionResult]) -> Dict[str, Any]:
        """分析执行结果"""
        # 汇总发现的仓库
        discovered_repos = self.executor.discovered_repos[:10]  # 最多显示10个
        analyzed_repos = dict(list(self.executor.repo_analysis.items())[:5])  # 最多显示5个
        
        # 构建分析结果
        analysis = {
            'summary': f"使用{plan.strategy.value}策略，执行了{len(execution_results)}个步骤",
            'discovered_repositories': discovered_repos,
            'detailed_analysis': analyzed_repos,
            'success_rate': len([r for r in execution_results if r.success]) / len(execution_results) if execution_results else 0,
            'key_findings': self._extract_key_findings(execution_results),
            'recommendations': [r.next_recommendations for r in execution_results if r.next_recommendations]
        }
        
        return analysis
    
    def _extract_key_findings(self, execution_results: List[ExecutionResult]) -> List[str]:
        """提取关键发现"""
        findings = []
        
        for result in execution_results:
            if result.success and result.observations:
                # 简化的关键信息提取
                if 'star' in result.observations.lower():
                    findings.append("发现了高星级项目")
                if 'python' in result.observations.lower():
                    findings.append("主要使用Python技术栈")
                if 'active' in result.observations.lower() or '活跃' in result.observations:
                    findings.append("项目保持活跃更新")
        
        return list(set(findings))  # 去重
    
    def _generate_recommendations(self, execution_results: List[ExecutionResult]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        successful_steps = [r for r in execution_results if r.success]
        failed_steps = [r for r in execution_results if not r.success]
        
        if len(successful_steps) >= 3:
            recommendations.append("✅ 搜索执行良好，建议深入分析推荐的仓库")
        
        if len(failed_steps) > 0:
            recommendations.append("⚠️ 部分步骤执行失败，建议检查网络连接或简化查询")
        
        if len(self.executor.discovered_repos) > 10:
            recommendations.append("📊 发现大量相关仓库，建议设置更精确的筛选条件")
        
        if len(self.executor.repo_analysis) < 3:
            recommendations.append("🔍 建议获取更多仓库的详细信息以便对比")
        
        return recommendations
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        status = {
            'has_plan': self.current_plan is not None,
            'execution_summary': self.executor.get_execution_summary() if self.executor else {}
        }
        
        if self.current_plan:
            status['plan_info'] = {
                'strategy': self.current_plan.strategy.value,
                'total_steps': len(self.current_plan.planned_steps),
                'success_criteria': self.current_plan.success_criteria
            }
        
        return status


# 为ADK系统创建工具函数（需要提前定义，供ReActGitHubAgent使用）
def plan_and_execute_search(query: str) -> str:
    """
    使用双模型Plan and Execute架构进行GitHub仓库搜索
    
    Args:
        query: 搜索查询，例如 "spring boot vue 项目"
    
    Returns:
        详细的搜索结果和分析报告
    """
    try:
        # 延迟导入，避免循环引用
        global plan_execute_agent
        if 'plan_execute_agent' not in globals():
            # 如果全局实例还没创建，创建临时实例
            temp_agent = PlanAndExecuteGitHubAgent()
        else:
            temp_agent = plan_execute_agent
        
        # 运行同步搜索
        try:
            # 检查是否在事件循环中运行
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，创建新线程运行
            import threading
            import concurrent.futures
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(temp_agent.search(query))
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                result = future.result()
                
        except RuntimeError:
            # 没有运行中的事件循环，可以直接创建
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(temp_agent.search(query))
            finally:
                loop.close()
        
        # 格式化输出
        output_parts = [
            f"🎯 双模型GitHub搜索结果",
            f"📝 查询: {result['user_query']}",
            f"🎯 策略: {result['plan']['strategy']}",
            f"📊 执行统计: {result['execution']['successful_steps']}/{result['execution']['completed_steps']} 步骤成功",
            f"🔍 发现仓库: {result['execution']['discovered_repos']}个",
            f"📋 详细分析: {result['execution']['analyzed_repos']}个",
            "",
            "📈 分析结果:",
            result['results']['summary'],
            ""
        ]
        
        if result['results']['discovered_repositories']:
            output_parts.append("🎯 推荐仓库:")
            for i, repo in enumerate(result['results']['discovered_repositories'][:5], 1):
                output_parts.append(f"{i}. {repo}")
            output_parts.append("")
        
        if result['results']['detailed_analysis']:
            output_parts.append("🔬 详细分析:")
            for repo, analysis in result['results']['detailed_analysis'].items():
                output_parts.append(f"- {repo}: ⭐{analysis.get('stars', 'N/A')} | {analysis.get('language', 'N/A')}")
            output_parts.append("")
        
        if result['recommendation']:
            output_parts.append("💡 建议:")
            for rec in result['recommendation']:
                output_parts.append(f"- {rec}")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        return f"❌ 双模型搜索失败: {str(e)}"

# 工具创建暂时注释（等待FunctionTool正确用法确认）
# plan_execute_tool = FunctionTool(
#     function=plan_and_execute_search,
#     description="使用双模型Plan and Execute架构进行GitHub仓库搜索和分析"
# )


class ReActGitHubAgent:
    """ReAct GitHub搜索代理"""
    
    def __init__(self):
        self.state = ReActState()
        self.prompt_engine = ReActPromptEngine()
        self.strategy_selector = SearchStrategySelector()
        self._setup_ssl()
        self._setup_agent()
    
    def _setup_ssl(self):
        """设置SSL配置"""
        # 从环境变量读取API密钥
        os.environ['DEEPSEEK_API_KEY'] = os.getenv('DEEPSEEK_API_KEY', 'sk-86bc0ca023294b4d94596861c70c6f45')
        
        # 解决SSL证书问题
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        except Exception as e:
            print(f"SSL配置警告: {e}")
    
    def _setup_agent(self):
        """设置代理"""
        # 配置MCP工具集 - 连接到本地增强版GitHub Search服务
        toolset = MCPToolset(
            connection_params=SseServerParams(
                url="https://github-search1111-uuid1754995527.app-space.dplink.cc/sse?token=5bf79bd1192f4d109b079b15907f28ae",  # 本地增强版MCP服务器
            ),
        )
        
        # 创建模型
        model = LiteLlm(model="deepseek/deepseek-chat")
        
        # 创建代理 - 暂时移除自定义工具
        self.agent = Agent(
            name="react_github_search_agent",
            model=model,
            instruction=self.prompt_engine.get_system_prompt() + "\n\n💡 提示：现在系统支持更先进的双模型Plan and Execute搜索模式，可以更智能地规划和执行搜索任务。",
            tools=[toolset]
        )
    
    def initialize_search(self, user_query: str) -> None:
        """初始化搜索状态"""
        self.state = ReActState()
        self.state.user_query = user_query
        self.state.current_strategy = self.strategy_selector.analyze_query_intent(user_query)
        
        print(f"🧠 ReAct GitHub搜索代理已启动")
        print(f"📝 用户查询: {user_query}")
        print(f"🎯 选择策略: {self.state.current_strategy.value}")
        print("=" * 50)
    
    def get_enhanced_prompt(self) -> str:
        """获取增强的提示词"""
        base_prompt = f"""
用户查询: {self.state.user_query}

{self.prompt_engine.get_thought_template(self.state)}

请按照ReAct框架进行分析，每步都要明确标出Thought、Action、Observation。
"""
        return base_prompt
    
    async def execute_react_cycle(self, user_query: str) -> str:
        """执行完整的ReAct循环"""
        self.initialize_search(user_query)
        
        final_answer = ""
        conversation_history = []
        
        while self.should_continue_search():
            self.state.iteration_count += 1
            print(f"\n🔄 开始第 {self.state.iteration_count} 轮ReAct循环")
            
            try:
                # Step 0: 动态策略调整
                new_strategy = self.strategy_selector.should_switch_strategy(
                    self.state.current_strategy, self.state
                )
                if new_strategy and new_strategy != self.state.current_strategy:
                    print(f"🔄 策略切换: {self.state.current_strategy.value} → {new_strategy.value}")
                    self.state.current_strategy = new_strategy
                
                # Step 1: 获取智能行动建议
                action_suggestion = self.strategy_selector.get_next_action_suggestion(
                    self.state.current_strategy, self.state
                )
                print(f"💡 策略建议: {action_suggestion['priority']} - {action_suggestion['reason']}")
                
                # Step 2: 生成思考和行动计划
                current_prompt = self._build_iteration_prompt(conversation_history, action_suggestion)
                
                print("💭 Thought阶段: 分析情况并制定计划...")
                
                # 调用代理进行思考
                response = await self._call_agent(current_prompt)
                print(f"🤖 代理响应: {response[:200]}...")
                
                # Step 3: 解析并执行行动
                action = self.parse_action_from_response(response)
                
                # 如果没有解析到行动，使用策略建议生成行动
                if not action:
                    action = self._generate_action_from_suggestion(action_suggestion)
                
                if action:
                    print(f"⚡ Action阶段: 执行 {action['tool']}")
                    observation = await self._execute_action(action)
                    print(f"👁️ Observation阶段: 获得结果")
                    
                    # Step 4: 更新状态
                    self._update_state(action, observation)
                    
                    # 构建对话历史
                    conversation_history.append({
                        "iteration": self.state.iteration_count,
                        "thought": self._extract_thought(response),
                        "action": action,
                        "observation": observation,
                        "response": response,
                        "strategy": self.state.current_strategy.value,
                        "suggestion": action_suggestion
                    })
                    
                    print(f"📊 当前状态: 找到{len(self.state.repositories_found)}个仓库, 分析了{len(self.state.detailed_analysis)}个")
                    
                else:
                    print("⚠️ 无法解析行动，可能是最终回答")
                    final_answer = response
                    break
                    
            except Exception as e:
                print(f"❌ 执行出错: {str(e)}")
                break
        
        # Step 5: 生成最终答案
        if not final_answer:
            final_answer = await self._generate_final_answer(conversation_history)
        
        print("\n🎯 ReAct循环完成!")
        return final_answer
    
    def _build_iteration_prompt(self, conversation_history: List[Dict], action_suggestion: Dict[str, Any] = None) -> str:
        """构建当前迭代的提示词"""
        prompt_parts = [
            f"用户查询: {self.state.user_query}",
            f"当前策略: {self.state.current_strategy.value}",
            f"迭代进度: {self.state.iteration_count}/{self.state.max_iterations}",
        ]
        
        # 添加策略建议
        if action_suggestion:
            prompt_parts.extend([
                f"\n🎯 智能建议:",
                f"- 推荐行动: {action_suggestion['priority']}",
                f"- 原因: {action_suggestion['reason']}",
            ])
            
            if 'target_repo' in action_suggestion:
                prompt_parts.append(f"- 目标仓库: {action_suggestion['target_repo']}")
            if 'suggested_query' in action_suggestion:
                prompt_parts.append(f"- 建议查询: {action_suggestion['suggested_query']}")
        
        # 添加历史信息
        if conversation_history:
            prompt_parts.append("\n📜 最近执行记录:")
            for record in conversation_history[-2:]:  # 只保留最近2轮
                prompt_parts.append(f"轮次{record['iteration']} ({record['strategy']}):")
                prompt_parts.append(f"- Thought: {record['thought'][:100]}...")
                prompt_parts.append(f"- Action: {record['action']['tool']}")
                prompt_parts.append(f"- Result: {str(record['observation'])[:100]}...")
        
        # 添加当前状态
        prompt_parts.extend([
            f"\n📊 当前状态:",
            f"- 已发现仓库: {len(self.state.repositories_found)}个",
            f"- 已详细分析: {len(self.state.detailed_analysis)}个",
            f"- 搜索历史: {len(self.state.search_history)}次",
        ])
        
        # 添加发现的仓库列表
        if self.state.repositories_found:
            prompt_parts.append(f"\n🔍 已发现仓库:")
            for i, repo in enumerate(self.state.repositories_found[:5], 1):
                analysis_status = "已分析" if repo in self.state.detailed_analysis else "待分析"
                prompt_parts.append(f"{i}. {repo} ({analysis_status})")
        
        prompt_parts.append("\n" + self.prompt_engine.get_thought_template(self.state))
        
        return "\n".join(prompt_parts)
    
    async def _call_agent(self, prompt: str) -> str:
        """调用代理"""
        try:
            # 使用同步方式调用agent
            runner = InMemoryRunner()
            session_service = InMemorySessionService()
            
            # 创建会话并运行
            session = await session_service.start_session()
            response = await runner.run(
                agent=self.agent,
                session=session,
                user_message=prompt
            )
            
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"代理调用失败: {str(e)}"
    
    async def _execute_action(self, action: Dict[str, Any]) -> str:
        """执行具体的行动"""
        try:
            # 模拟工具调用 - 实际应该调用MCP工具
            tool_name = action['tool']
            
            if tool_name == 'search_repositories':
                # 模拟搜索结果（增强版支持新参数）
                query = action['query']
                max_results = action.get('max_results', 8)
                search_mode = action.get('search_mode', 'simple')
                result = f"使用{search_mode}模式找到{max_results}个相关仓库: repo1/example, repo2/sample, ..."
                
                # 更新发现的仓库列表
                mock_repos = [f"repo{i}/example" for i in range(1, max_results + 1)]
                self.state.repositories_found.extend(mock_repos)
                
            elif tool_name == 'get_repository_info':
                full_name = action['full_name']
                result = f"获取{full_name}的详细信息: stars: 1000, language: Python, ..."
                
                # 更新详细分析
                self.state.detailed_analysis[full_name] = {
                    "stars": 1000,
                    "language": "Python",
                    "description": "示例仓库描述"
                }
                
            elif tool_name == 'get_repository_languages':
                full_name = action['full_name']
                result = f"获取{full_name}的语言统计: Python 80%, JavaScript 20%"
                
            elif tool_name == 'get_repository_tree':
                full_name = action['full_name']
                path = action.get('path', '')
                result = f"获取{full_name}的目录结构 (路径: {path}): 包含 src/, docs/, README.md 等"
                
            elif tool_name == 'get_repository_file_content':
                full_name = action['full_name']
                file_path = action['file_path']
                max_size = action.get('max_size', 50000)
                result = f"获取{full_name}中{file_path}的内容 (最大{max_size}字节): 文件内容..."
                
            else:
                result = f"未知工具: {tool_name}"
            
            return result
            
        except Exception as e:
            return f"执行行动失败: {str(e)}"
    
    def _extract_thought(self, response: str) -> str:
        """从响应中提取思考部分"""
        thought_match = re.search(r'Thought:\s*([^\n]+(?:\n(?!Action:)[^\n]+)*)', response, re.IGNORECASE)
        if thought_match:
            return thought_match.group(1).strip()
        return "无法提取思考内容"
    
    def _update_state(self, action: Dict[str, Any], observation: str) -> None:
        """更新状态"""
        # 记录搜索历史
        self.state.search_history.append({
            "iteration": self.state.iteration_count,
            "action": action,
            "observation": observation,
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0
        })
    
    async def _generate_final_answer(self, conversation_history: List[Dict]) -> str:
        """生成最终答案"""
        if not conversation_history:
            return "抱歉，没有找到相关信息。"
        
        # 汇总所有发现
        summary_parts = [
            f"基于ReAct分析，针对您的查询 '{self.state.user_query}'，我找到了以下信息:",
            f"\n📊 搜索统计:",
            f"- 执行了 {self.state.iteration_count} 轮分析",
            f"- 发现了 {len(self.state.repositories_found)} 个相关仓库", 
            f"- 深度分析了 {len(self.state.detailed_analysis)} 个项目",
            f"- 使用策略: {self.state.current_strategy.value}"
        ]
        
        if self.state.repositories_found:
            summary_parts.append(f"\n🎯 推荐仓库:")
            for i, repo in enumerate(self.state.repositories_found[:5], 1):
                analysis = self.state.detailed_analysis.get(repo, {})
                stars = analysis.get('stars', '未知')
                language = analysis.get('language', '未知')
                summary_parts.append(f"{i}. {repo} (⭐{stars}, 语言: {language})")
        
        summary_parts.append(f"\n💡 基于{self.state.current_strategy.value}策略的分析完成。")
        
        return "\n".join(summary_parts)
    
    def parse_action_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """从代理响应中解析行动"""
        # 提取Action部分
        action_match = re.search(r'Action:\s*([^\n]+)', response, re.IGNORECASE)
        if not action_match:
            return None
            
        action_text = action_match.group(1).strip()
        
        # 解析工具调用
        tool_patterns = [
            r'search_repositories\s*\(\s*["\']([^"\']+)["\'](?:,\s*max_results\s*=\s*(\d+))?(?:,\s*sort\s*=\s*["\']([^"\']+)["\'])?(?:,\s*search_mode\s*=\s*["\']([^"\']+)["\'])?\s*\)',
            r'get_repository_info\s*\(\s*["\']([^"\']+)["\']\s*\)',
            r'get_repository_languages\s*\(\s*["\']([^"\']+)["\']\s*\)',
            r'get_repository_tree\s*\(\s*["\']([^"\']+)["\'](?:,\s*path\s*=\s*["\']([^"\']*)["\'])?\s*\)',
            r'get_repository_file_content\s*\(\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\'](?:,\s*max_size\s*=\s*(\d+))?\s*\)'
        ]
        
        for pattern in tool_patterns:
            match = re.search(pattern, action_text, re.IGNORECASE)
            if match:
                if 'search_repositories' in pattern:
                    return {
                        'tool': 'search_repositories',
                        'query': match.group(1),
                        'max_results': int(match.group(2)) if match.group(2) else 8,
                        'sort': match.group(3) if match.group(3) else 'stars',
                        'search_mode': match.group(4) if match.group(4) else 'simple'
                    }
                elif 'get_repository_info' in pattern:
                    return {
                        'tool': 'get_repository_info',
                        'full_name': match.group(1)
                    }
                elif 'get_repository_languages' in pattern:
                    return {
                        'tool': 'get_repository_languages',
                        'full_name': match.group(1)
                    }
                elif 'get_repository_tree' in pattern:
                    return {
                        'tool': 'get_repository_tree',
                        'full_name': match.group(1),
                        'path': match.group(2) if match.group(2) else ''
                    }
                elif 'get_repository_file_content' in pattern:
                    return {
                        'tool': 'get_repository_file_content',
                        'full_name': match.group(1),
                        'file_path': match.group(2),
                        'max_size': int(match.group(3)) if match.group(3) else 50000
                    }
        
        return None
    
    def _generate_action_from_suggestion(self, suggestion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """根据策略建议生成具体行动"""
        priority = suggestion.get('priority')
        
        if priority == 'search':
            query = suggestion.get('suggested_query', self.state.user_query)
            params = self.strategy_selector.get_search_parameters(
                self.state.current_strategy, query
            )
            return {
                'tool': 'search_repositories',
                'query': query,
                'max_results': params['max_results'],
                'sort': params['sort']
            }
        
        elif priority == 'analyze':
            target_repo = suggestion.get('target_repo')
            if target_repo:
                return {
                    'tool': 'get_repository_info',
                    'full_name': target_repo
                }
        
        elif priority == 'language_analysis':
            target_repo = suggestion.get('target_repo')
            if target_repo:
                return {
                    'tool': 'get_repository_languages',
                    'full_name': target_repo
                }
        
        elif priority == 'conclude':
            # 返回None，触发最终答案生成
            return None
        
        return None
    
    def should_continue_search(self) -> bool:
        """判断是否应该继续搜索"""
        if self.state.iteration_count >= self.state.max_iterations:
            print(f"⏰ 达到最大迭代次数 {self.state.max_iterations}")
            return False
        
        # 获取策略建议
        suggestion = self.strategy_selector.get_next_action_suggestion(
            self.state.current_strategy, self.state
        )
        
        # 如果建议是总结，则停止搜索
        if suggestion.get('priority') == 'conclude':
            print("✅ 策略建议: 信息已够充分，可以总结")
            return False
            
        # 如果还没有找到任何仓库，继续搜索
        if not self.state.repositories_found:
            print("🔍 尚未发现任何仓库，继续搜索")
            return True
            
        # 根据策略判断是否需要更多信息
        if self.state.current_strategy == SearchStrategy.COMPARISON:
            needed = min(3, len(self.state.repositories_found))
            current = len(self.state.detailed_analysis)
            if current < needed:
                print(f"📊 对比策略需要分析更多仓库 ({current}/{needed})")
                return True
                
        elif self.state.current_strategy == SearchStrategy.DEEP_ANALYSIS:
            if len(self.state.detailed_analysis) < 1:
                print("🔬 深度分析策略需要至少分析1个仓库")
                return True
                
        elif self.state.current_strategy == SearchStrategy.TREND_ANALYSIS:
            if len(self.state.repositories_found) < 10:
                print(f"📈 趋势分析需要更多样本 ({len(self.state.repositories_found)}/10)")
                return True
        
        # 默认情况：如果分析数量不足，继续
        if len(self.state.detailed_analysis) < 2:
            print(f"📋 需要更多详细分析 ({len(self.state.detailed_analysis)}/2)")
            return True
            
        print("✅ 搜索目标已达成")
        return False
    
    # 便捷方法
    def search(self, query: str) -> str:
        """同步搜索接口"""
        # 创建事件循环来运行异步方法
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.execute_react_cycle(query))


# 创建双模型代理实例 (推荐使用)
plan_execute_agent = PlanAndExecuteGitHubAgent()

# 创建兼容的ReAct代理实例 (向后兼容)
react_agent = ReActGitHubAgent()

# 根代理 - 为了兼容ADK系统，使用Agent实例
root_agent = react_agent.agent

# 便捷同步接口
def search_github(query: str) -> Dict[str, Any]:
    """同步搜索接口 - 使用双模型Plan and Execute模式"""
    try:
        # 检查是否在事件循环中运行
        loop = asyncio.get_running_loop()
        # 如果已经在事件循环中，创建新线程运行
        import threading
        import concurrent.futures
        
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(plan_execute_agent.search(query))
            finally:
                new_loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
            
    except RuntimeError:
        # 没有运行中的事件循环，可以直接创建
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(plan_execute_agent.search(query))
        finally:
            loop.close()

# 便捷异步接口  
async def async_search_github(query: str) -> Dict[str, Any]:
    """异步搜索接口 - 使用双模型Plan and Execute模式"""
    return await plan_execute_agent.search(query)



# 导出主要组件
__all__ = [
    # 双模型代理 (推荐)
    'plan_execute_agent', 'PlanAndExecuteGitHubAgent',
    'search_github', 'async_search_github', 'plan_and_execute_search',
    
    # 单模型代理 (向后兼容)
    'react_agent', 'ReActGitHubAgent',
    
    # 核心组件
    'PlanningAgent', 'ExecutionAgent',
    'SearchStrategy', 'ModelRole', 'SearchPlan', 'ExecutionResult',
    
    # 工具 (暂时注释)
    # 'plan_execute_tool',
    
    # 兼容性
    'root_agent'
]
