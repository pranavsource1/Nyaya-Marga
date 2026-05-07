"""LangChain-based action plan generation using Ollama and local Llama 3.1.

Generates structured administrative strategies with RAG context augmentation.
Falls back to NVIDIA NIM API if Ollama fails.
"""
import logging
import json
from typing import List, Dict, Any, Optional
import time
import httpx

from langchain_community.llms import Ollama
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from app.schemas.llm_schemas import ActionPlanResponse
from app.services.rag_service import FAISSRetrieverService
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisThrottler:
    """Redis-based rate limiter to throttle API requests across workers."""
    def __init__(self, redis_url: str, limit: int, window: int, key: str = "nvidia_nim_api_throttle"):
        self.client = redis.from_url(redis_url)
        self.limit = limit
        self.window = window
        self.key = key
        
    def wait(self):
        while True:
            current_time = int(time.time())
            # Use a rolling window of 10 seconds for more granular throttling
            window_key = f"{self.key}:{current_time // self.window}"
            
            try:
                count = self.client.incr(window_key)
                if count == 1:
                    self.client.expire(window_key, self.window * 2)
                    
                if count <= self.limit:
                    return
                    
                # Over limit, sleep until next window
                sleep_time = self.window - (current_time % self.window)
                logger.info(f"API throttled. Waiting {sleep_time}s...")
                time.sleep(sleep_time + 0.1)
            except Exception as e:
                logger.warning(f"Throttler Redis connection failed: {e}. Bypassing throttle.")
                return

# Initialize a global throttler instance for NVIDIA NIM API (30 requests per 60 seconds on Free Tier)
# We use 1 request per 3 seconds to be very safe and smooth out traffic across workers
nvidia_nim_throttler = RedisThrottler(redis_url=settings.redis_url, limit=1, window=3)


class ActionPlanGenerator:
    """Generates structured action plans using Ollama Llama 3.1 with RAG context.

    Combines extracted entities from Phase 2, historical precedents from RAG,
    and domain expertise to generate implementation strategies for administrative bodies.

    Falls back to NVIDIA NIM API if Ollama becomes unavailable.
    """

    def __init__(
        self,
        ollama_base_url: str = "http://ollama:11434",
        model_name: str = "llama3.1:8b",
        temperature: float = 0.1,
        max_retries: int = 3,
        nvidia_nim_api_key: Optional[str] = None,
        nvidia_nim_model: str = "llama-3.1-8b-instant",
        use_nvidia_nim: bool = True,
    ):
        """Initialize the action plan generator.

        Args:
            ollama_base_url: Base URL for Ollama service
            model_name: Model identifier (e.g., 'llama3.1:8b')
            temperature: Temperature for LLM sampling (0.0-1.0)
            max_retries: Maximum retry attempts for JSON parsing
            nvidia_nim_api_key: API key for NVIDIA NIM fallback
            nvidia_nim_model: NVIDIA NIM model name (e.g., 'llama-3.1-8b-instant')
            use_nvidia_nim: Whether to use NVIDIA NIM as fallback if Ollama fails
        """
        self.ollama_base_url = ollama_base_url
        self.model_name = model_name
        self.temperature = temperature
        self.max_retries = max_retries
        self.nvidia_nim_api_key = nvidia_nim_api_key
        self.nvidia_nim_model = nvidia_nim_model
        self.use_nvidia_nim = use_nvidia_nim and nvidia_nim_api_key

        self.llm = None
        self.parser = PydanticOutputParser(pydantic_object=ActionPlanResponse)
        self.rag_service = None  # Disabled: sentence-transformer slows extraction

        logger.info(f"Initializing ActionPlanGenerator with model: {model_name}")
        if self.use_nvidia_nim:
            logger.info("NVIDIA NIM API fallback enabled")

    def _initialize_llm(self):
        """Lazy initialize Ollama LLM connection."""
        if self.llm is not None:
            return

        try:
            logger.info(f"Connecting to Ollama at {self.ollama_base_url}")
            self.llm = Ollama(
                base_url=self.ollama_base_url,
                model=self.model_name,
                temperature=self.temperature,
                format="json",  # Force JSON output format
            )
            logger.info("Ollama LLM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM: {e}", exc_info=True)
            raise

    def _build_system_prompt(self) -> str:
        """Build strict extraction-only system prompt.

        Returns:
            System prompt string with concrete JSON example (no raw schema)
        """
        # NOTE: We intentionally do NOT use PydanticOutputParser.get_format_instructions()
        # because it emits a raw JSON schema with $defs, which:
        #   (a) confuses NVIDIA NIM into returning the schema itself instead of data
        #   (b) contains curly braces that break LangChain's ChatPromptTemplate f-string parser
        # Instead, we provide a concrete filled-in example that the LLM can follow.
        return """You are a legal document EXPERT. Your task is to generate a comprehensive administrative action plan.

YOUR SOURCE OF TRUTH: The provided court judgment text and extracted entities.

You MUST output ONLY valid JSON with EXACTLY this structure (fill in real values based on the case):

{{
  "compliance_assessment": {{
    "recommendation": "<recommended compliance action, 10-500 chars>",
    "reasoning": "<detailed reasoning, 20-1000 chars>"
  }},
  "litigation_roi": {{
    "estimated_compliance_cost": <number in INR>,
    "estimated_litigation_cost": <number in INR>,
    "financial_recommendation": "<cost-benefit recommendation, 20-500 chars>"
  }},
  "statutory_timeline": {{
    "explicit_deadline": "<explicit deadline from the judgment, 5-300 chars>",
    "limitation_act_inference": "<inferred limitation period, 5-300 chars>"
  }},
  "action_directives": [
    {{
      "department_name": "<responsible department>",
      "task_description": "<specific actionable task, 10-500 chars>",
      "urgency_level": "HIGH"
    }}
  ]
}}

urgency_level must be exactly one of: "HIGH", "MEDIUM", "LOW"
action_directives must have at least 1 and at most 20 items.

EXTRACTION AND SYNTHESIS RULES:
1. Base your plan on the facts, departments, and deadlines in the judgment.
2. If explicit details are missing, use your legal domain expertise to infer logical next steps, standard procedures, or use sensible defaults.
3. Output ONLY valid JSON - no explanation, preamble, markdown code blocks, or commentary."""


    def _call_nvidia_nim_api(self, system_prompt: str, human_prompt: str) -> str:
        """Call NVIDIA NIM API for LLM generation.

        Args:
            system_prompt: System message for the LLM
            human_prompt: Human message for the LLM

        Returns:
            JSON string response from NVIDIA NIM API

        Raises:
            RuntimeError: If NVIDIA NIM API call fails
        """
        try:
            logger.info("Calling NVIDIA NIM API...")
            
            # Apply throttling before making the request
            nvidia_nim_throttler.wait()

            url = "https://integrate.api.nvidia.com/v1/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.nvidia_nim_api_key}"
            }

            payload = {
                "model": self.nvidia_nim_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": human_prompt}
                ],
                "temperature": self.temperature,
                "response_format": {"type": "json_object"}
            }

            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.error(f"NVIDIA NIM API HTTP error: {exc.response.status_code} - {exc.response.text}")
                    raise

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            logger.info("NVIDIA NIM API call successful")
            return content

        except Exception as e:
            logger.error(f"NVIDIA NIM API call failed: {e}", exc_info=True)
            raise RuntimeError(f"NVIDIA NIM API call failed: {e}") from e

    def _extract_entities_summary(self, entities: List[Dict[str, Any]]) -> str:
        """Synthesize extracted entities into a concise summary.

        Args:
            entities: List of ExtractedEntity dicts

        Returns:
            Formatted entity summary
        """
        if not entities:
            return "No entities available."

        entity_groups = {}
        for entity in entities:
            entity_type = entity.get("entity_type", "UNKNOWN")
            text = entity.get("extracted_text", "")
            confidence = entity.get("confidence_score", 0)

            if entity_type not in entity_groups:
                entity_groups[entity_type] = []
            entity_groups[entity_type].append({"text": text, "confidence": confidence})

        summary_lines = ["Extracted Case Entities:"]
        for entity_type, items in entity_groups.items():
            summary_lines.append(f"\n{entity_type}:")
            for item in items[:5]:  # Limit to top 5 per type
                confidence_pct = int(item["confidence"] * 100)
                summary_lines.append(f"  - {item['text']} ({confidence_pct}% confidence)")

        return "\n".join(summary_lines)

    def generate_action_plan(
        self,
        case_number: str,
        case_summary: str,
        extracted_entities: List[Dict[str, Any]],
    ) -> ActionPlanResponse:
        """Generate structured action plan for case.

        Tries NVIDIA NIM API first (PRIMARY), falls back to Ollama if NVIDIA NIM unavailable.

        Args:
            case_number: Case identifier
            case_summary: Brief summary of the case
            extracted_entities: List of ExtractedEntity data

        Returns:
            ActionPlanResponse with complete action plan

        Raises:
            RuntimeError: If both NVIDIA NIM and Ollama (if enabled) fail after retries
        """
        logger.info(f"Generating action plan for case: {case_number}")

        # Extract entity summary
        entity_summary = self._extract_entities_summary(extracted_entities)

        # RAG context disabled in extraction pipeline for speed
        rag_context = "No historical precedents available."

        # Build prompt
        system_prompt = self._build_system_prompt()

        human_prompt = f"""ACTUAL DOCUMENT TEXT (Your only source of truth):
========================================
{case_summary}
========================================

CASE NUMBER: {case_number}

EXTRACTED KEY ENTITIES AND CONCEPTS:
{entity_summary}

RELEVANT HISTORICAL PRECEDENTS (for reference only - focus on the actual document above):
{rag_context}

TASK: Analyze the ACTUAL DOCUMENT TEXT above and generate a comprehensive administrative action plan.

CRITICAL: Output ONLY valid JSON as requested. Do not include markdown formatting, markdown code blocks, or any conversational preamble/explanation."""

        # Try NVIDIA NIM API first (PRIMARY)
        if self.use_nvidia_nim:
            try:
                return self._try_nvidia_nim(system_prompt, human_prompt)
            except Exception as nvidia_nim_error:
                logger.warning(f"NVIDIA NIM API failed: {nvidia_nim_error}")
                logger.info("Attempting fallback to Ollama...")
                try:
                    return self._try_ollama(system_prompt, human_prompt)
                except Exception as ollama_error:
                    logger.error(f"Ollama fallback also failed: {ollama_error}")
                    raise RuntimeError(
                        f"Both NVIDIA NIM and Ollama failed. NVIDIA NIM: {str(nvidia_nim_error)[:100]}, "
                        f"Ollama: {str(ollama_error)[:100]}"
                    ) from ollama_error
        else:
            # Only Ollama available
            try:
                return self._try_ollama(system_prompt, human_prompt)
            except Exception as ollama_error:
                raise RuntimeError(f"Ollama failed: {ollama_error}") from ollama_error

    def _try_ollama(self, system_prompt: str, human_prompt: str) -> ActionPlanResponse:
        """Try to generate action plan using Ollama.

        Args:
            system_prompt: System message for the LLM
            human_prompt: Human message for the LLM

        Returns:
            ActionPlanResponse with complete action plan

        Raises:
            RuntimeError: If Ollama fails after max retries
        """
        self._initialize_llm()

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Ollama LLM generation attempt {attempt + 1}/{self.max_retries}")

                # Use pre-rendered message templates to avoid LangChain's
                # f-string parser choking on curly braces in the prompt content.
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]

                raw_output = self.llm.invoke(messages)
                result = self.parser.parse(raw_output)

                logger.info("Ollama LLM generation successful")
                return result

            except Exception as e:
                logger.warning(
                    f"Ollama attempt {attempt + 1} failed: {e}. "
                    f"Retrying..." if attempt < self.max_retries - 1 else ""
                )

                if attempt < self.max_retries - 1:
                    time.sleep(1)
                else:
                    raise RuntimeError(
                        f"Ollama failed after {self.max_retries} attempts: {e}"
                    ) from e

    def _try_nvidia_nim(self, system_prompt: str, human_prompt: str) -> ActionPlanResponse:
        """Try to generate action plan using NVIDIA NIM API.

        Args:
            system_prompt: System message for the LLM
            human_prompt: Human message for the LLM

        Returns:
            ActionPlanResponse with complete action plan

        Raises:
            RuntimeError: If NVIDIA NIM fails or response parsing fails
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"NVIDIA NIM API generation attempt {attempt + 1}/{self.max_retries}")

                response_text = self._call_nvidia_nim_api(system_prompt, human_prompt)

                # Extract JSON from response (may have markdown formatting)
                json_str = response_text
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0]

                json_data = json.loads(json_str.strip())
                result = ActionPlanResponse(**json_data)

                logger.info("NVIDIA NIM API generation successful")
                return result

            except Exception as e:
                logger.warning(
                    f"NVIDIA NIM attempt {attempt + 1} failed: {e}. "
                    f"Retrying..." if attempt < self.max_retries - 1 else ""
                )

                if attempt < self.max_retries - 1:
                    # Wait longer for rate limit (429) errors
                    wait_time = 65 if "429" in str(e) else 2
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(
                        f"NVIDIA NIM failed after {self.max_retries} attempts: {e}"
                    ) from e

    def generate_action_plan_with_fallback(
        self,
        case_number: str,
        case_summary: str,
        extracted_entities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate action plan with graceful fallback if LLM fails.

        Returns action plan as JSON dict rather than Pydantic model,
        suitable for direct JSONB storage in database.

        Args:
            case_number: Case identifier
            case_summary: Brief summary of the case
            extracted_entities: List of ExtractedEntity data

        Returns:
            Dictionary representation of ActionPlanResponse
        """
        try:
            action_plan = self.generate_action_plan(
                case_number, case_summary, extracted_entities
            )
            return action_plan.model_dump()
        except Exception as e:
            logger.error(f"Action plan generation failed: {e}", exc_info=True)
            # Return minimal valid structure
            return {
                "compliance_assessment": {
                    "recommendation": "Manual review required",
                    "reasoning": f"LLM generation failed: {str(e)[:200]}",
                },
                "litigation_roi": {
                    "estimated_compliance_cost": 0,
                    "estimated_litigation_cost": 0,
                    "financial_recommendation": "Consult with legal team",
                },
                "statutory_timeline": {
                    "explicit_deadline": "TBD - requires manual review",
                    "limitation_act_inference": "TBD - requires manual review",
                },
                "action_directives": [
                    {
                        "department_name": "Legal",
                        "task_description": "Schedule manual compliance review",
                        "urgency_level": "HIGH",
                    }
                ],
            }
