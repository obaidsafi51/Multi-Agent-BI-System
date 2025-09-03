"""Natural language query parser with financial metrics and time period extraction"""

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .kimi_client import KimiClient, KimiAPIError
from .models import (
    Ambiguity,
    AmbiguityType,
    FinancialEntity,
    ProcessingResult,
    QueryContext,
    QueryIntent,
)

logger = logging.getLogger(__name__)


class QueryPreprocessor:
    """Preprocesses queries before sending to KIMI"""
    
    def __init__(self):
        # Common financial abbreviations and their expansions
        self.abbreviations = {
            "q1": "first quarter",
            "q2": "second quarter", 
            "q3": "third quarter",
            "q4": "fourth quarter",
            "ytd": "year to date",
            "mtd": "month to date",
            "qtd": "quarter to date",
            "yoy": "year over year",
            "mom": "month over month",
            "qoq": "quarter over quarter",
            "roi": "return on investment",
            "roa": "return on assets",
            "roe": "return on equity",
            "ebitda": "earnings before interest taxes depreciation and amortization",
            "capex": "capital expenditure",
            "opex": "operational expenditure",
            "cogs": "cost of goods sold",
            "sga": "selling general and administrative",
            "p&l": "profit and loss",
            "b/s": "balance sheet",
            "cf": "cash flow",
        }
    
    def preprocess(self, query: str) -> str:
        """Preprocess the query text"""
        # Convert to lowercase for processing
        processed = query.lower().strip()
        
        # Expand common abbreviations
        for abbrev, expansion in self.abbreviations.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            processed = re.sub(pattern, expansion, processed, flags=re.IGNORECASE)
        
        # Normalize whitespace
        processed = re.sub(r'\s+', ' ', processed)
        
        # Remove extra punctuation but keep essential ones
        processed = re.sub(r'[^\w\s\-\.\,\?\!\%\$]', '', processed)
        
        logger.debug(f"Preprocessed query: '{query}' -> '{processed}'")
        return processed


class QueryParser:
    """Natural language query parser using KIMI LLM"""
    
    def __init__(self, kimi_client: KimiClient):
        self.kimi_client = kimi_client
        self.preprocessor = QueryPreprocessor()
        
        # Schema knowledge for validation
        self.known_metrics = {
            "revenue", "profit", "cash_flow", "budget", "investment", "ratio",
            "gross_profit", "net_profit", "operating_expenses", "debt_to_equity",
            "current_ratio", "quick_ratio", "gross_margin", "net_margin",
            "operating_cash_flow", "investing_cash_flow", "financing_cash_flow"
        }
        
        self.known_time_periods = {
            "daily", "weekly", "monthly", "quarterly", "yearly",
            "this_year", "last_year", "this_quarter", "last_quarter",
            "this_month", "last_month", "ytd", "mtd", "qtd"
        }
    
    async def parse_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Parse natural language query and extract structured information"""
        start_time = datetime.now()
        query_id = str(uuid.uuid4())
        
        try:
            # Preprocess the query
            processed_query = self.preprocessor.preprocess(query)
            
            # Create initial query context
            query_context = QueryContext(
                user_id=user_id,
                session_id=session_id,
                query_id=query_id,
                original_query=query,
                processed_query=processed_query,
                processing_metadata={"start_time": start_time.isoformat()}
            )
            
            # Extract financial intent using KIMI
            logger.info(f"Extracting intent for query: {query}")
            intent_data = await self.kimi_client.extract_financial_intent(
                processed_query, context
            )
            
            # Validate and create QueryIntent
            query_intent = self._create_query_intent(intent_data)
            query_context.intent = query_intent
            
            # Extract financial entities using KIMI
            logger.info(f"Extracting entities for query: {query}")
            entities_data = await self.kimi_client.extract_financial_entities(
                processed_query, context
            )
            
            # Create FinancialEntity objects
            entities = []
            for entity_data in entities_data:
                try:
                    entity = FinancialEntity(**entity_data)
                    entities.append(entity)
                except Exception as e:
                    logger.warning(f"Invalid entity data: {entity_data}, error: {e}")
            
            query_context.entities = entities
            
            # Detect ambiguities using KIMI
            logger.info(f"Detecting ambiguities for query: {query}")
            ambiguities_data = await self.kimi_client.detect_ambiguities(
                processed_query, context
            )
            
            # Process ambiguities
            ambiguities = []
            clarifications = []
            
            for ambiguity_data in ambiguities_data:
                try:
                    ambiguity = Ambiguity(**ambiguity_data)
                    ambiguities.append(ambiguity.description)
                    clarifications.append(ambiguity.suggested_clarification)
                except Exception as e:
                    logger.warning(f"Invalid ambiguity data: {ambiguity_data}, error: {e}")
            
            query_context.ambiguities = ambiguities
            query_context.clarifications = clarifications
            
            # Add processing metadata
            end_time = datetime.now()
            processing_time_ms = max(1, int((end_time - start_time).total_seconds() * 1000))
            
            query_context.processing_metadata.update({
                "end_time": end_time.isoformat(),
                "processing_time_ms": processing_time_ms,
                "entities_count": len(entities),
                "ambiguities_count": len(ambiguities)
            })
            
            logger.info(f"Query parsing completed in {processing_time_ms}ms")
            
            return ProcessingResult(
                success=True,
                query_context=query_context,
                processing_time_ms=processing_time_ms,
                kimi_usage={"total_requests": 3}  # intent + entities + ambiguities
            )
            
        except KimiAPIError as e:
            logger.error(f"KIMI API error during query parsing: {e}")
            processing_time_ms = max(1, int((datetime.now() - start_time).total_seconds() * 1000))
            
            return ProcessingResult(
                success=False,
                error_message=f"KIMI API error: {str(e)}",
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during query parsing: {e}")
            processing_time_ms = max(1, int((datetime.now() - start_time).total_seconds() * 1000))
            
            return ProcessingResult(
                success=False,
                error_message=f"Query parsing failed: {str(e)}",
                processing_time_ms=processing_time_ms
            )
    
    def _create_query_intent(self, intent_data: Dict[str, Any]) -> QueryIntent:
        """Create QueryIntent from KIMI response data"""
        try:
            # Validate required fields
            metric_type = intent_data.get("metric_type", "unknown")
            time_period = intent_data.get("time_period", "unknown")
            
            # Create QueryIntent with validation
            query_intent = QueryIntent(
                metric_type=metric_type,
                time_period=time_period,
                aggregation_level=intent_data.get("aggregation_level", "monthly"),
                filters=intent_data.get("filters", {}),
                comparison_periods=intent_data.get("comparison_periods", []),
                visualization_hint=intent_data.get("visualization_hint"),
                confidence_score=intent_data.get("confidence_score", 0.0)
            )
            
            # Validate against known metrics and time periods
            if metric_type not in self.known_metrics and metric_type != "unknown":
                logger.warning(f"Unknown metric type: {metric_type}")
            
            if time_period not in self.known_time_periods and time_period != "unknown":
                logger.warning(f"Unknown time period: {time_period}")
            
            return query_intent
            
        except Exception as e:
            logger.error(f"Failed to create QueryIntent: {e}")
            # Return a default QueryIntent
            return QueryIntent(
                metric_type="unknown",
                time_period="unknown",
                confidence_score=0.0
            )
    
    async def validate_query_context(self, query_context: QueryContext) -> List[str]:
        """Validate query context and return list of validation issues"""
        issues = []
        
        if not query_context.intent:
            issues.append("No intent extracted from query")
            return issues
        
        intent = query_context.intent
        
        # Check for low confidence
        if intent.confidence_score < 0.5:
            issues.append(f"Low confidence in intent extraction: {intent.confidence_score}")
        
        # Check for unknown metric type
        if intent.metric_type == "unknown":
            issues.append("Could not identify the financial metric requested (unknown metric type)")
        
        # Check for unknown time period
        if intent.time_period == "unknown":
            issues.append("Could not identify the time period requested (unknown time period)")
        
        # Check for ambiguities
        if query_context.ambiguities:
            issues.append(f"Query contains {len(query_context.ambiguities)} ambiguities")
        
        # Check entity extraction
        if not query_context.entities:
            issues.append("No financial entities extracted from query")
        
        return issues
    
    async def suggest_query_improvements(
        self, 
        query_context: QueryContext
    ) -> List[str]:
        """Suggest improvements for unclear or incomplete queries"""
        suggestions = []
        
        if not query_context.intent:
            return ["Please rephrase your query to include a specific financial metric and time period."]
        
        intent = query_context.intent
        
        # Suggest specific metrics if unknown
        if intent.metric_type == "unknown":
            suggestions.append(
                "Try specifying a financial metric like 'revenue', 'profit', 'cash flow', or 'budget variance'"
            )
        
        # Suggest specific time periods if unknown
        if intent.time_period == "unknown":
            suggestions.append(
                "Try specifying a time period like 'this quarter', 'last year', 'Q1 2024', or 'year to date'"
            )
        
        # Suggest comparisons if none specified
        if not intent.comparison_periods and intent.confidence_score > 0.7:
            suggestions.append(
                "Consider adding a comparison like 'vs last year' or 'compared to budget' for better insights"
            )
        
        # Use clarifications from ambiguity detection
        if query_context.clarifications:
            suggestions.extend(query_context.clarifications[:3])  # Limit to top 3
        
        return suggestions