"""MOONSHOT API client with authentication, retry logic, and error handling"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from pydantic import ValidationError

from .models import KimiRequest, KimiResponse

logger = logging.getLogger(__name__)


class KimiAPIError(Exception):
    """Base exception for MOONSHOT API errors"""
    pass


class KimiAuthenticationError(KimiAPIError):
    """Authentication error with MOONSHOT API"""
    pass


class KimiRateLimitError(KimiAPIError):
    """Rate limit exceeded error"""
    pass


class KimiTimeoutError(KimiAPIError):
    """Request timeout error"""
    pass


class KimiClient:
    """MOONSHOT API client with retry logic and error handling"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.moonshot.ai/v1",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        
        # Always use real API - no development mode mock
        self.is_development = False
        
        if not self.api_key or self.api_key in ["your_actual_kimi_api_key_here", "your_moonshot_api_key_here"]:
            raise ValueError("MOONSHOT API key is required. Get one from https://platform.moonshot.ai/console")
        
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        logger.info(f"MOONSHOT client initialized with base URL: {base_url}")
        logger.info("Using real MOONSHOT API with KIMI model")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params
                )
                
                # Handle different HTTP status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise KimiAuthenticationError("Invalid API key or authentication failed")
                elif response.status_code == 429:
                    raise KimiRateLimitError("Rate limit exceeded")
                elif response.status_code >= 500:
                    if attempt < self.max_retries:
                        logger.warning(f"Server error {response.status_code}, retrying in {self.retry_delay}s")
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise KimiAPIError(f"Server error: {response.status_code}")
                else:
                    error_detail = response.text
                    raise KimiAPIError(f"API error {response.status_code}: {error_detail}")
                    
            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    logger.warning(f"Request timeout, retrying in {self.retry_delay}s")
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    raise KimiTimeoutError("Request timed out after all retries")
            except httpx.RequestError as e:
                if attempt < self.max_retries:
                    logger.warning(f"Request error: {e}, retrying in {self.retry_delay}s")
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    raise KimiAPIError(f"Request failed: {e}")
        
        raise KimiAPIError("Max retries exceeded")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "kimi-k2-0905-preview",
        temperature: float = 0.1,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> KimiResponse:
        """Create a chat completion using MOONSHOT API"""
        try:
            request_data = KimiRequest(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            logger.debug(f"Sending chat completion request: {len(messages)} messages")
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/chat/completions",
                data=request_data.model_dump()
            )
            
            # Validate and parse response
            kimi_response = KimiResponse(**response_data)
            
            logger.info(f"Chat completion successful, tokens used: {kimi_response.usage}")
            return kimi_response
            
        except ValidationError as e:
            logger.error(f"Invalid response format from MOONSHOT API: {e}")
            raise KimiAPIError(f"Invalid response format: {e}")
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise
    
    async def extract_financial_intent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract financial intent from natural language query"""
        system_prompt = """You are a financial data analysis expert. Your task is to analyze natural language queries from CFOs and extract structured financial intent.

Extract the following information from the query:
1. metric_type: The type of financial metric (revenue, profit, cash_flow, budget, investment, ratio, etc.)
2. time_period: The time period requested (specific dates, quarters, years, relative periods)
3. aggregation_level: How data should be aggregated (daily, monthly, quarterly, yearly)
4. filters: Any additional filters or conditions
5. comparison_periods: Any comparison periods mentioned
6. visualization_hint: Suggested chart type if mentioned or implied

Return your response as a JSON object with these fields. If any information is unclear or missing, indicate this in the response.

Examples:
Query: "Show me quarterly revenue for this year"
Response: {
  "metric_type": "revenue",
  "time_period": "this_year",
  "aggregation_level": "quarterly",
  "filters": {},
  "comparison_periods": [],
  "visualization_hint": "line_chart",
  "confidence_score": 0.9
}

Query: "Compare cash flow this quarter vs last quarter"
Response: {
  "metric_type": "cash_flow",
  "time_period": "this_quarter",
  "aggregation_level": "quarterly",
  "filters": {},
  "comparison_periods": ["last_quarter"],
  "visualization_hint": "bar_chart",
  "confidence_score": 0.85
}"""

        user_message = f"Query: {query}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await self.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            
            # Extract the JSON response from the assistant's message
            assistant_message = response.choices[0]["message"]["content"]
            
            # Try to parse JSON from the response
            try:
                intent_data = json.loads(assistant_message)
                return intent_data
            except json.JSONDecodeError:
                # If direct JSON parsing fails, try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', assistant_message, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group())
                    return intent_data
                else:
                    raise KimiAPIError("Could not extract JSON from MOONSHOT response")
                    
        except Exception as e:
            logger.error(f"Financial intent extraction failed: {e}")
            raise KimiAPIError(f"Intent extraction failed: {e}")
    
    async def extract_financial_entities(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract financial entities from natural language query"""
        system_prompt = """You are a financial entity recognition expert. Extract all financial entities from the given query.

For each entity found, provide:
1. entity_type: Type of entity (metric, time_period, department, currency, percentage, etc.)
2. entity_value: Normalized value of the entity
3. confidence_score: Confidence in recognition (0.0 to 1.0)
4. synonyms: Alternative terms for this entity
5. original_text: Original text from the query

Return a JSON array of entities. If no entities are found, return an empty array.

Example:
Query: "Show me Q1 revenue and profit margins for the sales department"
Response: [
  {
    "entity_type": "time_period",
    "entity_value": "Q1",
    "confidence_score": 0.95,
    "synonyms": ["first quarter", "quarter 1"],
    "original_text": "Q1"
  },
  {
    "entity_type": "metric",
    "entity_value": "revenue",
    "confidence_score": 0.9,
    "synonyms": ["sales", "income", "turnover"],
    "original_text": "revenue"
  },
  {
    "entity_type": "metric",
    "entity_value": "profit_margin",
    "confidence_score": 0.85,
    "synonyms": ["margin", "profitability"],
    "original_text": "profit margins"
  },
  {
    "entity_type": "department",
    "entity_value": "sales",
    "confidence_score": 0.9,
    "synonyms": ["sales team", "sales division"],
    "original_text": "sales department"
  }
]"""

        user_message = f"Query: {query}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await self.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )
            
            assistant_message = response.choices[0]["message"]["content"]
            
            # Try to parse JSON from the response
            try:
                entities_data = json.loads(assistant_message)
                return entities_data if isinstance(entities_data, list) else []
            except json.JSONDecodeError:
                # Try to extract JSON array from text
                import re
                json_match = re.search(r'\[.*\]', assistant_message, re.DOTALL)
                if json_match:
                    entities_data = json.loads(json_match.group())
                    return entities_data if isinstance(entities_data, list) else []
                else:
                    logger.warning("Could not extract JSON array from MOONSHOT response")
                    return []
                    
        except Exception as e:
            logger.error(f"Financial entity extraction failed: {e}")
            return []    

    async def detect_ambiguities(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Detect ambiguities in the query and suggest clarifications"""
        system_prompt = """You are an expert at detecting ambiguities in financial queries. Analyze the query and identify any unclear or ambiguous parts that might need clarification.

For each ambiguity found, provide:
1. ambiguity_type: Type of ambiguity (time_period, metric_type, comparison_basis, aggregation_level, entity_reference)
2. description: Description of what is ambiguous
3. possible_interpretations: List of possible interpretations
4. confidence_score: Confidence in ambiguity detection (0.0 to 1.0)
5. suggested_clarification: A clarifying question to ask the user

Return a JSON array of ambiguities. If no ambiguities are found, return an empty array.

Example:
Query: "Show me the performance last quarter"
Response: [
  {
    "ambiguity_type": "metric_type",
    "description": "Performance metric is not specified",
    "possible_interpretations": ["revenue performance", "profit performance", "overall financial performance", "budget performance"],
    "confidence_score": 0.9,
    "suggested_clarification": "Which performance metric would you like to see? (revenue, profit, budget variance, etc.)"
  },
  {
    "ambiguity_type": "time_period",
    "description": "Last quarter could refer to different quarters depending on current date",
    "possible_interpretations": ["Q4 2024", "Q3 2024", "most recent completed quarter"],
    "confidence_score": 0.7,
    "suggested_clarification": "Which quarter are you referring to? (Q4 2024, Q3 2024, etc.)"
  }
]"""

        user_message = f"Query: {query}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await self.chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=1500
            )
            
            assistant_message = response.choices[0]["message"]["content"]
            
            # Try to parse JSON from the response
            try:
                ambiguities_data = json.loads(assistant_message)
                return ambiguities_data if isinstance(ambiguities_data, list) else []
            except json.JSONDecodeError:
                # Try to extract JSON array from text
                import re
                json_match = re.search(r'\[.*\]', assistant_message, re.DOTALL)
                if json_match:
                    ambiguities_data = json.loads(json_match.group())
                    return ambiguities_data if isinstance(ambiguities_data, list) else []
                else:
                    logger.warning("Could not extract JSON array from MOONSHOT response")
                    return []
                    
        except Exception as e:
            logger.error(f"Ambiguity detection failed: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if MOONSHOT API is accessible"""
        try:
            # Simple test request to verify API connectivity
            messages = [
                {"role": "user", "content": "Hello"}
            ]
            
            response = await self.chat_completion(
                messages=messages,
                max_tokens=10
            )
            
            return response.choices[0]["message"]["content"] is not None
            
        except Exception as e:
            logger.error(f"MOONSHOT API health check failed: {e}")
            return False