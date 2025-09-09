"""
AI-Enhanced Semantic Mapper with KIMI Integration for Dynamic Schema Management.

This module extends the basic semantic mapping with AI-powered semantic analysis using
KIMI API (Moonshot AI) for enhanced business term to database schema mapping.
"""

import asyncio
import os
import json
import logging
import aiohttp
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import hashlib

try:
    from .semantic_mapper import SemanticSchemaMapper, SemanticMapping
    from .models import TableSchema, ColumnInfo, TableInfo
    from .config import MCPSchemaConfig
except ImportError:
    # Fallback for direct execution
    from semantic_mapper import SemanticSchemaMapper, SemanticMapping
    from models import TableSchema, ColumnInfo, TableInfo
    from config import MCPSchemaConfig

logger = logging.getLogger(__name__)


@dataclass
class AISemanticMapping(SemanticMapping):
    """Enhanced semantic mapping with AI analysis."""
    ai_explanation: str
    source_api: str  # 'kimi', 'fallback', 'cache'
    cost_tokens: int = 0
    processing_time_ms: int = 0


@dataclass
class KIMIResponse:
    """Response from KIMI API."""
    mappings: List[Dict[str, Any]]
    total_tokens: int
    processing_time_ms: int
    confidence_scores: List[float]


class KIMIAPIClient:
    """Client for KIMI (Moonshot AI) API integration."""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config
        self.base_url = "https://api.moonshot.cn/v1/chat/completions"
        self.model = config.get('model', 'moonshot-v1-8k')
        self.temperature = config.get('temperature', 0.1)
        self.max_tokens = config.get('max_tokens', 1000)
        
        # Rate limiting
        self.api_usage_tracker = {}
        self.rate_limit_per_hour = config.get('rate_limit_per_hour', 50)
        self.rate_limit_per_day = config.get('rate_limit_per_day', 200)
        
    async def check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        hour_key = f"kimi_{now.strftime('%Y%m%d%H')}"
        day_key = f"kimi_{now.strftime('%Y%m%d')}"
        
        # Clean old entries
        current_hour = now.hour
        current_day = now.day
        keys_to_remove = []
        for key in self.api_usage_tracker:
            if 'kimi_' in key:
                if len(key) == 15:  # hour format
                    key_hour = int(key[-2:])
                    if key_hour != current_hour:
                        keys_to_remove.append(key)
                elif len(key) == 13:  # day format
                    key_day = int(key[-2:])
                    if key_day != current_day:
                        keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.api_usage_tracker[key]
        
        # Check limits
        hour_usage = self.api_usage_tracker.get(hour_key, 0)
        day_usage = self.api_usage_tracker.get(day_key, 0)
        
        return (hour_usage < self.rate_limit_per_hour and 
                day_usage < self.rate_limit_per_day)
    
    def increment_usage(self) -> None:
        """Increment API usage counters."""
        now = datetime.now()
        hour_key = f"kimi_{now.strftime('%Y%m%d%H')}"
        day_key = f"kimi_{now.strftime('%Y%m%d')}"
        
        self.api_usage_tracker[hour_key] = self.api_usage_tracker.get(hour_key, 0) + 1
        self.api_usage_tracker[day_key] = self.api_usage_tracker.get(day_key, 0) + 1
    
    def get_system_prompt(self) -> str:
        """Get system prompt for KIMI API."""
        return """You are an expert database schema analyst with deep knowledge of business intelligence and data mapping. Your job is to map business terms to database schema elements (tables and columns).

Guidelines:
- Analyze the semantic meaning and business context of terms
- Consider domain-specific terminology and abbreviations
- Account for common naming conventions in databases (snake_case, camelCase, etc.)
- Evaluate synonym relationships and conceptual similarity
- Provide confidence scores between 0.0 and 1.0 based on:
  * 0.9-1.0: Exact or near-exact matches
  * 0.7-0.9: Strong semantic similarity
  * 0.5-0.7: Moderate similarity with context
  * Below 0.5: Weak similarity (exclude from results)

Always respond with valid JSON in the specified format and explain your reasoning."""
    
    def build_mapping_prompt(self, business_term: str, schema_elements: List[Dict], context: str = None) -> str:
        """Build prompt for semantic mapping."""
        schema_desc = "\n".join([
            f"- {elem['table_name']}.{elem['column_name']}: {elem.get('description', 'No description available')}"
            for elem in schema_elements
        ])
        
        context_section = f"\nQuery Context: {context}" if context else ""
        
        return f"""Business Term: "{business_term}"{context_section}

Available Database Schema Elements:
{schema_desc}

Task: Identify which schema elements best match the business term "{business_term}". Consider:
1. Direct name matches and variations
2. Semantic similarity and business meaning
3. Common abbreviations and synonyms
4. Context clues from the query

Response Format (JSON only):
{{
    "mappings": [
        {{
            "table_name": "table_name",
            "column_name": "column_name", 
            "confidence_score": 0.95,
            "mapping_type": "exact|semantic|synonym|contextual",
            "explanation": "Brief explanation of why this mapping makes sense"
        }}
    ]
}}

Only include mappings with confidence score >= 0.5. Order by confidence score (highest first)."""
    
    async def semantic_mapping_request(self, business_term: str, schema_elements: List[Dict], 
                                     context: str = None) -> KIMIResponse:
        """Make semantic mapping request to KIMI API."""
        if not await self.check_rate_limit():
            raise Exception("KIMI API rate limit exceeded")
        
        start_time = datetime.now()
        
        try:
            prompt = self.build_mapping_prompt(business_term, schema_elements, context)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': self.get_system_prompt()},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.increment_usage()
                        
                        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                        
                        # Parse response
                        content = result['choices'][0]['message']['content'].strip()
                        
                        # Extract JSON from response
                        try:
                            # Find JSON block in response
                            json_start = content.find('{')
                            json_end = content.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                json_content = content[json_start:json_end]
                                parsed_data = json.loads(json_content)
                            else:
                                # Fallback: try to parse entire content as JSON
                                parsed_data = json.loads(content)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse KIMI response as JSON: {e}")
                            logger.error(f"Response content: {content}")
                            raise Exception(f"Invalid JSON response from KIMI: {e}")
                        
                        mappings = parsed_data.get('mappings', [])
                        confidence_scores = [m.get('confidence_score', 0.0) for m in mappings]
                        total_tokens = result.get('usage', {}).get('total_tokens', 0)
                        
                        return KIMIResponse(
                            mappings=mappings,
                            total_tokens=total_tokens,
                            processing_time_ms=processing_time,
                            confidence_scores=confidence_scores
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"KIMI API error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"KIMI API request failed: {e}")
            raise


class AISemanticSchemaMapper(SemanticSchemaMapper):
    """Enhanced Semantic Schema Mapper with AI-powered analysis using KIMI."""
    
    def __init__(self, config: MCPSchemaConfig):
        super().__init__(config)
        
        # AI configuration
        self.kimi_api_key = os.getenv('KIMI_API_KEY')
        self.ai_config = config.semantic_mapping.get('ai_config', {})
        
        # KIMI client
        self.kimi_client = None
        if self.kimi_api_key:
            self.kimi_client = KIMIAPIClient(self.kimi_api_key, self.ai_config.get('kimi', {}))
        
        # AI-specific cache
        self.ai_mapping_cache = {}
        self.cache_ttl_hours = self.ai_config.get('cache_ttl_hours', 24)
        
        # Configuration
        self.use_ai_for_mapping = self.ai_config.get('enabled', True) and bool(self.kimi_api_key)
        self.ai_confidence_threshold = self.ai_config.get('confidence_threshold', 0.7)
        self.fallback_to_fuzzy = self.ai_config.get('fallback_to_fuzzy', True)
        self.fuzzy_threshold = self.ai_config.get('fuzzy_threshold', 0.8)
        self.max_ai_suggestions = self.ai_config.get('max_suggestions', 5)
        
        logger.info(f"AI Semantic Mapper initialized. KIMI available: {bool(self.kimi_client)}")
    
    def is_ai_available(self) -> bool:
        """Check if AI services are available."""
        return self.use_ai_for_mapping and self.kimi_client is not None
    
    def generate_cache_key(self, term: str, schema_elements: List[Dict], context: str = None) -> str:
        """Generate cache key for AI mapping results."""
        # Create deterministic hash of input parameters
        content = f"{term}:{json.dumps(schema_elements, sort_keys=True)}:{context or ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        if 'timestamp' not in cache_entry:
            return False
        
        cache_time = cache_entry['timestamp']
        expiry_time = cache_time + timedelta(hours=self.cache_ttl_hours)
        return datetime.now() < expiry_time
    
    async def map_business_term_ai(self, term: str, schema_elements: List[Dict], 
                                 context: str = None) -> List[AISemanticMapping]:
        """Map business term using AI with fallback strategies."""
        
        # Check cache first
        cache_key = self.generate_cache_key(term, schema_elements, context)
        if cache_key in self.ai_mapping_cache:
            cached_entry = self.ai_mapping_cache[cache_key]
            if self.is_cache_valid(cached_entry):
                logger.debug(f"Using cached AI mapping for term: {term}")
                return cached_entry['mappings']
            else:
                # Remove expired cache entry
                del self.ai_mapping_cache[cache_key]
        
        # Try AI mapping first
        if self.is_ai_available():
            try:
                ai_mappings = await self._map_with_kimi(term, schema_elements, context)
                
                # Cache successful result
                self.ai_mapping_cache[cache_key] = {
                    'mappings': ai_mappings,
                    'timestamp': datetime.now()
                }
                
                logger.info(f"Successfully mapped '{term}' using KIMI AI. Found {len(ai_mappings)} mappings.")
                return ai_mappings
                
            except Exception as e:
                logger.warning(f"AI mapping failed for term '{term}': {e}")
                if not self.fallback_to_fuzzy:
                    raise
        
        # Fallback to fuzzy matching
        if self.fallback_to_fuzzy:
            logger.info(f"Using fuzzy matching fallback for term: {term}")
            return await self._fallback_fuzzy_mapping(term, schema_elements)
        else:
            raise Exception("AI mapping failed and fallback is disabled")
    
    async def _map_with_kimi(self, term: str, schema_elements: List[Dict], 
                           context: str = None) -> List[AISemanticMapping]:
        """Use KIMI API for semantic mapping."""
        
        if not self.kimi_client:
            raise Exception("KIMI client not available")
        
        try:
            # Make API request
            kimi_response = await self.kimi_client.semantic_mapping_request(
                term, schema_elements, context
            )
            
            # Convert to AISemanticMapping objects
            ai_mappings = []
            for mapping_data in kimi_response.mappings:
                confidence = mapping_data.get('confidence_score', 0.0)
                
                # Only include mappings above threshold
                if confidence >= self.ai_confidence_threshold:
                    ai_mapping = AISemanticMapping(
                        business_term=term,
                        schema_element_type='column',
                        schema_element_path=f"{mapping_data.get('table_name', '')}.{mapping_data.get('column_name', '')}",
                        confidence_score=confidence,
                        similarity_type=mapping_data.get('mapping_type', 'ai_semantic'),
                        context_match=bool(context),
                        metadata={
                            'table_name': mapping_data.get('table_name', ''),
                            'column_name': mapping_data.get('column_name', ''),
                            'api_tokens': kimi_response.total_tokens
                        },
                        created_at=datetime.now(),
                        ai_explanation=mapping_data.get('explanation', ''),
                        source_api='kimi',
                        cost_tokens=kimi_response.total_tokens,
                        processing_time_ms=kimi_response.processing_time_ms
                    )
                    ai_mappings.append(ai_mapping)
            
            # Sort by confidence score
            ai_mappings.sort(key=lambda x: x.confidence_score, reverse=True)
            
            # Limit results
            return ai_mappings[:self.max_ai_suggestions]
            
        except Exception as e:
            logger.error(f"KIMI mapping failed: {e}")
            raise
    
    async def _fallback_fuzzy_mapping(self, term: str, schema_elements: List[Dict]) -> List[AISemanticMapping]:
        """Fallback to fuzzy string matching when AI is unavailable."""
        
        mappings = []
        for element in schema_elements:
            table_name = element.get('table_name', '')
            column_name = element.get('column_name', '')
            
            # Calculate similarities
            table_similarity = SequenceMatcher(None, term.lower(), table_name.lower()).ratio()
            column_similarity = SequenceMatcher(None, term.lower(), column_name.lower()).ratio()
            
            # Use the higher similarity
            max_similarity = max(table_similarity, column_similarity)
            
            # Only include if above fuzzy threshold
            if max_similarity >= self.fuzzy_threshold:
                mapping = AISemanticMapping(
                    business_term=term,
                    schema_element_type='column',
                    schema_element_path=f"{table_name}.{column_name}",
                    confidence_score=max_similarity,
                    similarity_type='fuzzy',
                    context_match=False,
                    metadata={
                        'table_name': table_name,
                        'column_name': column_name,
                        'table_similarity': table_similarity,
                        'column_similarity': column_similarity
                    },
                    created_at=datetime.now(),
                    ai_explanation=f"Fuzzy string matching: {max_similarity:.2f} similarity",
                    source_api='fallback',
                    cost_tokens=0,
                    processing_time_ms=0
                )
                mappings.append(mapping)
        
        # Sort by confidence and limit results
        mappings.sort(key=lambda x: x.confidence_score, reverse=True)
        return mappings[:self.max_ai_suggestions]
