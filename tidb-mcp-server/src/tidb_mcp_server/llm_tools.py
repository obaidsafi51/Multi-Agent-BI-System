"""
LLM tools for Universal MCP Server.

This module implements LLM-related MCP tools for text generation, analysis,
and AI-powered operations using the Kimi (Moonshot) API.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import httpx
import json

from .config import LLMConfig
from .exceptions import TiDBMCPServerError
from .cache_manager import CacheManager, CacheKeyGenerator

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with Kimi (Moonshot) LLM API.
    """
    
    def __init__(self, config: LLMConfig, cache_manager: Optional[CacheManager] = None):
        """
        Initialize LLM client.
        
        Args:
            config: LLM configuration
            cache_manager: Optional cache manager for response caching
        """
        self.config = config
        self.cache_manager = cache_manager
        self.base_url = config.base_url or "https://api.moonshot.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"LLMClient initialized for provider: {config.provider}")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate text using the LLM.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            use_cache: Whether to use response caching
            
        Returns:
            Dictionary with generated text and metadata
        """
        start_time = time.time()
        
        try:
            # Use config defaults if not specified
            max_tokens = max_tokens or self.config.max_tokens
            temperature = temperature or self.config.temperature
            
            # Create cache key
            cache_key = None
            if use_cache and self.cache_manager:
                cache_key = CacheKeyGenerator.llm_key(prompt, system_prompt, max_tokens, temperature)
                cached_result = self.cache_manager.get(cache_key)
                if cached_result:
                    logger.debug("LLM response retrieved from cache")
                    return cached_result
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare request payload
            payload = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            logger.info(f"Generating text with LLM: {prompt[:100]}...")
            
            # Make API request
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            # Process response
            execution_time_ms = (time.time() - start_time) * 1000
            
            if "choices" not in result or not result["choices"]:
                raise Exception("Invalid response format from LLM API")
            
            generated_text = result["choices"][0]["message"]["content"]
            
            response_data = {
                "generated_text": generated_text,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "model": self.config.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "execution_time_ms": execution_time_ms,
                "usage": result.get("usage", {}),
                "success": True
            }
            
            # Cache the response
            if use_cache and self.cache_manager and cache_key:
                self.cache_manager.set(cache_key, response_data)
            
            logger.info(f"Text generated successfully in {execution_time_ms:.2f}ms")
            return response_data
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"LLM text generation failed: {error_msg}")
            
            return {
                "generated_text": "",
                "prompt": prompt,
                "system_prompt": system_prompt,
                "model": self.config.model,
                "execution_time_ms": execution_time_ms,
                "success": False,
                "error": error_msg
            }
    
    async def analyze_data(
        self,
        data: str,
        analysis_type: str = "general",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze data using LLM with specific analysis prompts.
        
        Args:
            data: Data to analyze (JSON, CSV, or text format)
            analysis_type: Type of analysis (general, financial, trend, summary)
            context: Optional context about the data
            
        Returns:
            Dictionary with analysis results
        """
        # Create analysis-specific system prompt
        analysis_prompts = {
            "general": "You are a data analyst. Analyze the provided data and provide insights.",
            "financial": "You are a financial analyst. Analyze the financial data and provide business insights.",
            "trend": "You are a trend analyst. Identify patterns and trends in the provided data.",
            "summary": "You are a data summarizer. Provide a concise summary of the key points in the data.",
            "sql": "You are a SQL expert. Analyze the query results and explain what they show."
        }
        
        system_prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
        
        if context:
            system_prompt += f" Context: {context}"
        
        # Create user prompt
        user_prompt = f"Please analyze this data:\n\n{data}\n\nProvide insights, patterns, and recommendations."
        
        result = await self.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3  # Lower temperature for more focused analysis
        )
        
        # Add analysis metadata
        result["analysis_type"] = analysis_type
        result["data_preview"] = data[:200] + "..." if len(data) > 200 else data
        
        return result
    
    async def generate_sql_query(
        self,
        natural_language_query: str,
        schema_info: Optional[str] = None,
        examples: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate SQL query from natural language using LLM.
        
        Args:
            natural_language_query: User's question in natural language
            schema_info: Database schema information
            examples: Optional example queries
            
        Returns:
            Dictionary with generated SQL and metadata
        """
        system_prompt = """You are a SQL expert. Convert natural language questions into valid SQL SELECT queries.
Rules:
1. Only generate SELECT queries (no INSERT, UPDATE, DELETE, DROP, etc.)
2. Use proper SQL syntax for TiDB/MySQL
3. Include comments explaining the query logic
4. Return only the SQL query without additional explanation"""
        
        if schema_info:
            system_prompt += f"\n\nDatabase Schema:\n{schema_info}"
        
        if examples:
            system_prompt += f"\n\nExample queries:\n" + "\n".join(examples)
        
        user_prompt = f"Convert this question to SQL: {natural_language_query}"
        
        result = await self.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1  # Very low temperature for precise SQL generation
        )
        
        # Add SQL-specific metadata
        result["query_type"] = "sql_generation"
        result["natural_language_query"] = natural_language_query
        
        return result
    
    async def explain_query_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain SQL query results in natural language.
        
        Args:
            query: The SQL query that was executed
            results: Query results
            context: Optional business context
            
        Returns:
            Dictionary with explanation and insights
        """
        system_prompt = """You are a data analyst. Explain SQL query results in clear, business-friendly language.
Focus on:
1. What the data shows
2. Key insights and patterns
3. Business implications
4. Recommendations if applicable"""
        
        if context:
            system_prompt += f"\n\nBusiness Context: {context}"
        
        # Limit results for prompt size
        limited_results = results[:10] if len(results) > 10 else results
        results_preview = f"Query returned {len(results)} rows. Sample data:\n{json.dumps(limited_results, indent=2)}"
        
        user_prompt = f"""SQL Query: {query}

Results: {results_preview}

Please explain what this data shows and provide insights."""
        
        result = await self.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.4
        )
        
        # Add explanation metadata
        result["query"] = query
        result["result_count"] = len(results)
        result["explanation_type"] = "query_results"
        
        return result


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def initialize_llm_tools(config: LLMConfig, cache_manager: Optional[CacheManager] = None) -> None:
    """
    Initialize LLM tools with configuration.
    
    Args:
        config: LLM configuration
        cache_manager: Optional cache manager
    """
    global _llm_client
    _llm_client = LLMClient(config, cache_manager)
    logger.info("LLM tools initialized")


def _ensure_llm_initialized() -> LLMClient:
    """Ensure LLM client is initialized."""
    global _llm_client
    if _llm_client is None:
        raise RuntimeError("LLM tools not initialized. Call initialize_llm_tools() first.")
    return _llm_client


# MCP Tool Functions
async def generate_text_tool(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Generate text using LLM.
    
    Args:
        prompt: User prompt/question
        system_prompt: Optional system prompt
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation
        use_cache: Whether to use caching
        
    Returns:
        Generated text and metadata
    """
    client = _ensure_llm_initialized()
    return await client.generate_text(prompt, system_prompt, max_tokens, temperature, use_cache)


async def analyze_data_tool(
    data: str,
    analysis_type: str = "general",
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze data using LLM.
    
    Args:
        data: Data to analyze
        analysis_type: Type of analysis
        context: Optional context
        
    Returns:
        Analysis results and insights
    """
    client = _ensure_llm_initialized()
    return await client.analyze_data(data, analysis_type, context)


async def generate_sql_tool(
    natural_language_query: str,
    schema_info: Optional[str] = None,
    examples: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate SQL query from natural language.
    
    Args:
        natural_language_query: User's question
        schema_info: Database schema information
        examples: Optional example queries
        
    Returns:
        Generated SQL query and metadata
    """
    client = _ensure_llm_initialized()
    return await client.generate_sql_query(natural_language_query, schema_info, examples)


async def explain_results_tool(
    query: str,
    results: List[Dict[str, Any]],
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Explain query results in natural language.
    
    Args:
        query: SQL query
        results: Query results
        context: Optional context
        
    Returns:
        Explanation and insights
    """
    client = _ensure_llm_initialized()
    return await client.explain_query_results(query, results, context)


# List of LLM MCP tools
LLM_TOOLS = [
    generate_text_tool,
    analyze_data_tool,
    generate_sql_tool,
    explain_results_tool
]
