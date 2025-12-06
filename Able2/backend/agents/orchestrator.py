"""
Orchestrator Agent for Able2.

The orchestrator is the main intelligence that:
1. Analyzes user intent
2. Plans action sequences
3. Delegates to specialized agents
4. Synthesizes results
5. Controls autonomy level
"""

from typing import Dict, Any, List, Optional
from backend.schemas import (
    AgentType, AgentMessage, AgentResponse, ActionType,
    AutonomyLevel, ActionPlan, requires_confirmation
)
from backend.core import orchestrator_logger
from .base_agent import BaseAgent
from .memory_agent import MemoryAgent
from .context_agent import ContextAgent
from .execution_agent import ExecutionAgent


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - main intelligence and coordinator.

    Routes user requests to appropriate agents and synthesizes responses.
    """

    def __init__(self, autonomy_level: AutonomyLevel = AutonomyLevel.MODERATE):
        """
        Initialize Orchestrator Agent.

        Args:
            autonomy_level: User's preferred autonomy level
        """
        super().__init__(
            agent_type=AgentType.ORCHESTRATOR,
            model_provider="anthropic"  # Use Claude for orchestration
        )

        self.autonomy_level = autonomy_level

        # Initialize sub-agents
        self.memory_agent = MemoryAgent()
        self.context_agent = ContextAgent()
        self.execution_agent = ExecutionAgent()

        self.logger.info(f"Orchestrator initialized (autonomy={autonomy_level.value})")

    async def process(self, message: AgentMessage) -> AgentResponse:
        """
        Process user message through orchestration pipeline.

        Pipeline:
        1. Analyze intent
        2. Plan actions
        3. Execute actions (delegate to agents)
        4. Synthesize results
        5. Return response

        Args:
            message: User message

        Returns:
            Synthesized response
        """
        user_query = message.content

        self.logger.info(f"Orchestrator processing: '{user_query[:50]}...'")

        try:
            # Step 1: Analyze intent
            intent_analysis = await self.analyze_intent(user_query)

            # Step 2: Plan actions
            action_plan = await self.plan_actions(user_query, intent_analysis)

            # Check if plan requires confirmation
            if action_plan.requires_confirmation:
                return self.create_response(
                    success=True,
                    data={
                        "intent": intent_analysis,
                        "plan": action_plan.to_dict(),
                        "query": user_query
                    },
                    reasoning=f"I've analyzed your request and created a plan. {action_plan.intent}",
                    requires_confirmation=True,
                    next_action="execute_plan"
                )

            # Step 3: Execute actions
            execution_results = await self.execute_plan(action_plan, user_query)

            # Step 4: Synthesize results
            final_response = await self.synthesize_results(
                user_query,
                intent_analysis,
                execution_results
            )

            self.log_action("orchestrate", success=True, details="Completed orchestration pipeline")

            return final_response

        except Exception as e:
            self.logger.error(f"Orchestration failed: {str(e)}")
            self.log_action("orchestrate", success=False, details=str(e))

            return self.create_response(
                success=False,
                data={},
                error=f"Orchestration failed: {str(e)}"
            )

    async def analyze_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user intent using LLM.

        Args:
            query: User query

        Returns:
            Intent analysis
        """
        self.logger.debug("Analyzing intent")

        system_prompt = """You are an intent analyzer for an AI assistant.
Analyze the user's query and determine:
1. Primary intent (search, question, action, etc.)
2. Required information sources (documents, emails, calendar, web)
3. Whether this requires actions with side effects (email, calendar, code execution)

Respond in this format:
INTENT: <one word intent>
SOURCES: <comma-separated sources>
REQUIRES_ACTION: <yes/no>
EXPLANATION: <brief explanation>"""

        try:
            response = self.call_llm(
                prompt=query,
                system_prompt=system_prompt,
                max_tokens=200
            )

            # Parse response
            intent_data = self._parse_intent_response(response)

            self.logger.debug(f"Intent: {intent_data}")

            return intent_data

        except Exception as e:
            self.logger.warning(f"Intent analysis failed, using fallback: {str(e)}")

            # Fallback to simple heuristics
            return {
                "intent": "search",
                "sources": ["documents"],
                "requires_action": False,
                "explanation": "Treating as document search"
            }

    async def plan_actions(self, query: str, intent: Dict[str, Any]) -> ActionPlan:
        """
        Create action plan based on intent.

        Args:
            query: User query
            intent: Intent analysis

        Returns:
            Action plan
        """
        self.logger.debug("Planning actions")

        intent_type = intent.get("intent", "search")
        sources = intent.get("sources", ["documents"])
        requires_action = intent.get("requires_action", False)

        # Build action sequence
        actions = []
        action_sequence = []

        if intent_type in ["search", "question", "find"]:
            # Check if web search is requested
            if "web" in sources or intent_type == "web_search":
                # Web search via Execution Agent
                actions.append(ActionType.BROWSE_WEB)

                action_sequence.append({
                    "agent": AgentType.EXECUTION.value,
                    "action": ActionType.BROWSE_WEB.value,
                    "parameters": {
                        "query": query,
                        "max_results": 10,
                        "summarize": True
                    }
                })
            else:
                # Document search via Memory Agent
                actions.append(ActionType.SEARCH_DOCUMENTS)

                action_sequence.append({
                    "agent": AgentType.MEMORY.value,
                    "action": ActionType.SEARCH_DOCUMENTS.value,
                    "parameters": {
                        "query": query,
                        "sources": sources,
                        "top_k": 10
                    }
                })

        elif intent_type == "breakdown" or intent_type == "task":
            # Task breakdown via Execution Agent
            actions.append(ActionType.BREAK_DOWN_TASK)

            action_sequence.append({
                "agent": AgentType.EXECUTION.value,
                "action": ActionType.BREAK_DOWN_TASK.value,
                "parameters": {
                    "task": query
                }
            })

        # Determine if confirmation required
        needs_confirmation = False

        for action in actions:
            if requires_confirmation(action, self.autonomy_level):
                needs_confirmation = True
                break

        plan = ActionPlan(
            intent=intent.get("explanation", ""),
            actions=actions,
            action_sequence=action_sequence,
            requires_confirmation=needs_confirmation,
            autonomy_level=self.autonomy_level
        )

        self.logger.debug(f"Action plan created: {len(actions)} actions, confirmation={needs_confirmation}")

        return plan

    async def execute_plan(self, plan: ActionPlan, query: str) -> List[AgentResponse]:
        """
        Execute action plan by delegating to agents.

        Args:
            plan: Action plan to execute
            query: Original user query

        Returns:
            List of agent responses
        """
        self.logger.info(f"Executing plan: {len(plan.action_sequence)} actions")

        results = []

        for action_spec in plan.action_sequence:
            agent_type = AgentType(action_spec["agent"])
            action_type = ActionType(action_spec["action"])
            parameters = action_spec["parameters"]

            self.logger.debug(f"Executing: {agent_type.value}.{action_type.value}")

            # Create message for agent
            message = AgentMessage(
                from_agent=AgentType.ORCHESTRATOR,
                to_agent=agent_type,
                content=query,
                metadata={
                    "action_type": action_type,
                    **parameters
                }
            )

            # Route to appropriate agent
            if agent_type == AgentType.MEMORY:
                response = await self.memory_agent.process(message)
            elif agent_type == AgentType.CONTEXT:
                response = await self.context_agent.process(message)
            elif agent_type == AgentType.EXECUTION:
                response = await self.execution_agent.process(message)
            else:
                response = self.create_response(
                    success=False,
                    data={},
                    error=f"Unknown agent: {agent_type}"
                )

            results.append(response)

        return results

    async def synthesize_results(
        self,
        query: str,
        intent: Dict[str, Any],
        results: List[AgentResponse]
    ) -> AgentResponse:
        """
        Synthesize agent results into final response.

        Args:
            query: Original query
            intent: Intent analysis
            results: Agent responses

        Returns:
            Synthesized response
        """
        self.logger.debug("Synthesizing results")

        # Collect all successful results
        successful_results = [r for r in results if r.success]

        if not successful_results:
            # All agents failed
            errors = [r.error for r in results if r.error]
            return self.create_response(
                success=False,
                data={},
                error=f"All actions failed: {'; '.join(errors)}"
            )

        # For Phase 1, focus on Memory Agent search results
        memory_result = successful_results[0]  # First result is typically memory search

        if memory_result.agent_type == AgentType.MEMORY:
            # Get search results
            search_results = memory_result.data.get("results", [])

            if not search_results:
                return self.create_response(
                    success=True,
                    data={
                        "message": "I searched but couldn't find relevant information.",
                        "query": query,
                        "sources": []
                    },
                    reasoning="No relevant results found in memory."
                )

            # Use LLM to synthesize answer from search results
            answer = await self.generate_answer(query, search_results)

            return self.create_response(
                success=True,
                data={
                    "message": answer,
                    "sources": search_results,
                    "query": query,
                    "num_sources": len(search_results)
                },
                reasoning=f"Synthesized answer from {len(search_results)} sources using hybrid retrieval."
            )

        # Fallback
        return self.create_response(
            success=True,
            data={"results": [r.data for r in successful_results]},
            reasoning="Executed actions successfully."
        )

    async def generate_answer(self, query: str, sources: List[Dict[str, Any]]) -> str:
        """
        Generate answer using LLM based on retrieved sources.

        Args:
            query: User query
            sources: Retrieved source documents

        Returns:
            Generated answer
        """
        self.logger.debug("Generating answer from sources")

        # Build context from sources
        context_parts = []
        for i, source in enumerate(sources[:5], 1):  # Use top 5
            text = source.get("text", "")
            metadata = source.get("metadata", {})
            filename = metadata.get("filename", "Unknown")

            context_parts.append(f"[Source {i} from {filename}]\n{text}\n")

        context = "\n".join(context_parts)

        system_prompt = """You are a helpful AI assistant. Answer the user's question based on the provided sources.

Rules:
- Be concise and accurate
- Cite sources when possible
- If sources don't contain the answer, say so
- Don't make up information"""

        prompt = f"""Question: {query}

Sources:
{context}

Answer:"""

        try:
            answer = self.call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=1000
            )

            return answer.strip()

        except Exception as e:
            self.logger.error(f"Answer generation failed: {str(e)}")

            # Fallback to simple summary
            return f"I found {len(sources)} relevant sources. Here's what I found: {sources[0].get('text', '')[:200]}..."

    def _parse_intent_response(self, response: str) -> Dict[str, Any]:
        """Parse intent analysis response from LLM."""
        lines = response.strip().split("\n")

        intent_data = {
            "intent": "search",
            "sources": ["documents"],
            "requires_action": False,
            "explanation": ""
        }

        for line in lines:
            if line.startswith("INTENT:"):
                intent_data["intent"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("SOURCES:"):
                sources_str = line.split(":", 1)[1].strip()
                intent_data["sources"] = [s.strip() for s in sources_str.split(",")]
            elif line.startswith("REQUIRES_ACTION:"):
                action_str = line.split(":", 1)[1].strip().lower()
                intent_data["requires_action"] = action_str in ["yes", "true"]
            elif line.startswith("EXPLANATION:"):
                intent_data["explanation"] = line.split(":", 1)[1].strip()

        return intent_data
