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
- search_repositories(query, max_results, sort): 搜索GitHub仓库
- get_repository_info(full_name): 获取仓库详细信息
- get_repository_languages(full_name): 获取编程语言统计

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
1. search_repositories(query="搜索关键词", max_results=数量, sort="排序方式")
2. get_repository_info(full_name="owner/repo")
3. get_repository_languages(full_name="owner/repo")
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
        # 配置MCP工具集
        toolset = MCPToolset(
            connection_params=SseServerParams(
                url="https://03593ce517feac573fdaafa6dcedef61.app-space.dplink.cc/sse?token=fdd0d45a3f224eaf8a3b56d706b61fed",
            ),
        )
        
        # 创建模型
        model = LiteLlm(model="deepseek/deepseek-chat")
        
        # 创建代理
        self.agent = Agent(
            name="react_github_search_agent",
            model=model,
            instruction=self.prompt_engine.get_system_prompt(),
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
            # 这里应该是异步调用，但当前的ADK接口可能不支持
            # 所以我们用同步方式模拟
            response = "模拟代理响应 - 实际应该调用self.agent"
            return response
        except Exception as e:
            return f"代理调用失败: {str(e)}"
    
    async def _execute_action(self, action: Dict[str, Any]) -> str:
        """执行具体的行动"""
        try:
            # 模拟工具调用 - 实际应该调用MCP工具
            tool_name = action['tool']
            
            if tool_name == 'search_repositories':
                # 模拟搜索结果
                query = action['query']
                max_results = action.get('max_results', 8)
                result = f"找到{max_results}个相关仓库: repo1/example, repo2/sample, ..."
                
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
            r'search_repositories\s*\(\s*["\']([^"\']+)["\'](?:,\s*max_results\s*=\s*(\d+))?(?:,\s*sort\s*=\s*["\']([^"\']+)["\'])?\s*\)',
            r'get_repository_info\s*\(\s*["\']([^"\']+)["\']\s*\)',
            r'get_repository_languages\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ]
        
        for pattern in tool_patterns:
            match = re.search(pattern, action_text, re.IGNORECASE)
            if match:
                if 'search_repositories' in pattern:
                    return {
                        'tool': 'search_repositories',
                        'query': match.group(1),
                        'max_results': int(match.group(2)) if match.group(2) else 8,
                        'sort': match.group(3) if match.group(3) else 'stars'
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


# 创建全局代理实例
react_agent = ReActGitHubAgent()

# 向后兼容的根代理
root_agent = react_agent.agent

# 导出主要组件
__all__ = ['react_agent', 'root_agent', 'ReActGitHubAgent', 'SearchStrategy']
