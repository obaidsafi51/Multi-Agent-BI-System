"""
Query classifier for routing queries through appropriate processing paths.
Optimizes performance by identifying simple queries that can use fast path processing.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class ProcessingPath(Enum):
    """Processing path types"""
    FAST_PATH = "fast_path"
    STANDARD_PATH = "standard_path"
    COMPREHENSIVE_PATH = "comprehensive_path"


@dataclass
class QueryClassification:
    """Result of query classification"""
    complexity: QueryComplexity
    processing_path: ProcessingPath
    confidence_score: float
    reasoning: List[str]
    estimated_processing_time: float  # in seconds
    recommended_optimizations: List[str]


class QueryClassifier:
    """
    Intelligent query classifier that determines the optimal processing path
    for each query based on complexity analysis.
    """
    
    def __init__(self):
        # Simple query patterns (can use fast path)
        self.simple_patterns = [
            r'\b(show|display|get)\s+(revenue|profit|sales)\b',
            r'\b(what\s+is|how\s+much)\s+(revenue|profit|sales)\b',
            r'\b(last|this)\s+(month|quarter|year)\s+(revenue|profit|sales)\b',
            r'\b(revenue|profit|sales)\s+(last|this)\s+(month|quarter|year)\b',
            r'\b(total|sum)\s+(revenue|profit|sales)\b'
        ]
        
        # Complex query indicators
        self.complex_indicators = {
            'comparison_words': ['vs', 'versus', 'compared to', 'compare', 'difference', 'variance'],
            'multiple_metrics': ['and', 'plus', 'also', 'both', 'all', 'various'],
            'advanced_analysis': ['trend', 'correlation', 'forecast', 'predict', 'analyze', 'breakdown'],
            'conditional_logic': ['if', 'when', 'where', 'unless', 'except', 'only if'],
            'aggregation_functions': ['average', 'median', 'percentile', 'ratio', 'rate', 'margin'],
            'time_complexity': ['quarter over quarter', 'year over year', 'period comparison', 'seasonal']
        }
        
        # Known simple metrics
        self.simple_metrics = {
            'revenue', 'sales', 'income', 'profit', 'cost', 'expense', 
            'budget', 'cash', 'balance', 'total', 'amount'
        }
        
        # Known simple time periods
        self.simple_time_periods = {
            'today', 'yesterday', 'this week', 'last week', 'this month', 
            'last month', 'this quarter', 'last quarter', 'this year', 'last year'
        }
        
        # Financial abbreviations that add complexity
        self.complex_abbreviations = {
            'ebitda', 'roi', 'roa', 'roe', 'cogs', 'sga', 'capex', 'opex'
        }
        
        logger.info("Query classifier initialized with pattern matching rules")
    
    def classify_query(self, query: str, context: Optional[Dict] = None) -> QueryClassification:
        """
        Classify query and determine optimal processing path.
        
        Args:
            query: Natural language query
            context: Optional context information
            
        Returns:
            QueryClassification with complexity and processing recommendations
        """
        query_lower = query.lower().strip()
        
        # Initialize classification data
        complexity_score = 0.0
        reasoning = []
        optimizations = []
        
        # Analyze query components
        word_count = len(query.split())
        char_count = len(query)
        
        # 1. Basic length analysis
        if word_count <= 8 and char_count <= 50:
            complexity_score += 0
            reasoning.append("Short query length")
        elif word_count <= 15 and char_count <= 100:
            complexity_score += 1
            reasoning.append("Medium query length")
        else:
            complexity_score += 2
            reasoning.append("Long query length")
        
        # 2. Check for simple patterns
        simple_pattern_match = self._check_simple_patterns(query_lower)
        if simple_pattern_match:
            complexity_score -= 1
            reasoning.append(f"Matches simple pattern: {simple_pattern_match}")
            optimizations.append("Can use cached schema context")
        
        # 3. Check for complex indicators
        complex_score, complex_reasons = self._analyze_complexity_indicators(query_lower)
        complexity_score += complex_score
        reasoning.extend(complex_reasons)
        
        # 4. Analyze metrics complexity
        metrics_score, metrics_reasons = self._analyze_metrics_complexity(query_lower)
        complexity_score += metrics_score
        reasoning.extend(metrics_reasons)
        
        # 5. Analyze time period complexity
        time_score, time_reasons = self._analyze_time_complexity(query_lower)
        complexity_score += time_score
        reasoning.extend(time_reasons)
        
        # 6. Check for abbreviations and technical terms
        abbrev_score, abbrev_reasons = self._analyze_abbreviations(query_lower)
        complexity_score += abbrev_score
        reasoning.extend(abbrev_reasons)
        
        # 7. Context analysis
        if context:
            context_score, context_reasons = self._analyze_context_complexity(context)
            complexity_score += context_score
            reasoning.extend(context_reasons)
        
        # Determine complexity level and processing path
        complexity, processing_path, estimated_time = self._determine_processing_path(complexity_score)
        
        # Add optimization recommendations
        if complexity == QueryComplexity.SIMPLE:
            optimizations.extend([
                "Use parallel KIMI calls",
                "Skip entity extraction", 
                "Use minimal context building",
                "Cache result aggressively"
            ])
        elif complexity == QueryComplexity.MEDIUM:
            optimizations.extend([
                "Use parallel KIMI calls",
                "Selective entity extraction",
                "Standard context building"
            ])
        else:
            optimizations.extend([
                "Full parallel processing",
                "Complete entity extraction",
                "Comprehensive context building",
                "Advanced caching strategy"
            ])
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(complexity_score, reasoning)
        
        classification = QueryClassification(
            complexity=complexity,
            processing_path=processing_path,
            confidence_score=confidence_score,
            reasoning=reasoning,
            estimated_processing_time=estimated_time,
            recommended_optimizations=optimizations
        )
        
        logger.info(f"Query classified as {complexity.value} with {processing_path.value} "
                   f"(confidence: {confidence_score:.2f}, score: {complexity_score:.1f})")
        
        return classification
    
    def _check_simple_patterns(self, query: str) -> Optional[str]:
        """Check if query matches simple patterns"""
        for pattern in self.simple_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return pattern
        return None
    
    def _analyze_complexity_indicators(self, query: str) -> Tuple[float, List[str]]:
        """Analyze query for complexity indicators"""
        score = 0.0
        reasons = []
        
        for category, indicators in self.complex_indicators.items():
            found_indicators = [ind for ind in indicators if ind in query]
            if found_indicators:
                category_score = len(found_indicators) * 0.5
                score += category_score
                reasons.append(f"Found {category}: {', '.join(found_indicators[:3])}")
        
        return score, reasons
    
    def _analyze_metrics_complexity(self, query: str) -> Tuple[float, List[str]]:
        """Analyze complexity based on metrics mentioned"""
        score = 0.0
        reasons = []
        
        # Count metrics mentioned
        simple_metrics_found = [m for m in self.simple_metrics if m in query]
        
        if len(simple_metrics_found) == 1:
            score += 0
            reasons.append(f"Single simple metric: {simple_metrics_found[0]}")
        elif len(simple_metrics_found) > 1:
            score += len(simple_metrics_found) * 0.3
            reasons.append(f"Multiple metrics: {', '.join(simple_metrics_found[:3])}")
        
        # Check for ratio/calculation indicators
        calc_indicators = ['ratio', 'percentage', 'margin', 'rate', 'growth', 'change']
        calc_found = [ind for ind in calc_indicators if ind in query]
        if calc_found:
            score += len(calc_found) * 0.4
            reasons.append(f"Calculation indicators: {', '.join(calc_found)}")
        
        return score, reasons
    
    def _analyze_time_complexity(self, query: str) -> Tuple[float, List[str]]:
        """Analyze time period complexity"""
        score = 0.0
        reasons = []
        
        # Simple time periods
        simple_time_found = [t for t in self.simple_time_periods if t in query]
        if simple_time_found:
            score += 0
            reasons.append(f"Simple time period: {simple_time_found[0]}")
        
        # Complex time patterns
        complex_time_patterns = [
            r'\d{4}', # Year patterns
            r'q[1-4]', # Quarter patterns
            r'(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
            r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(week|day) \d+',
            r'between .+ and .+',
            r'from .+ to .+'
        ]
        
        for pattern in complex_time_patterns:
            if re.search(pattern, query):
                score += 0.3
                reasons.append(f"Complex time pattern: {pattern}")
        
        # Multiple time periods
        time_words = ['year', 'quarter', 'month', 'week', 'day']
        time_count = sum(1 for word in time_words if word in query)
        if time_count > 1:
            score += time_count * 0.2
            reasons.append(f"Multiple time references: {time_count}")
        
        return score, reasons
    
    def _analyze_abbreviations(self, query: str) -> Tuple[float, List[str]]:
        """Analyze abbreviations and technical terms"""
        score = 0.0
        reasons = []
        
        # Complex financial abbreviations
        complex_abbrev_found = [abbr for abbr in self.complex_abbreviations if abbr in query]
        if complex_abbrev_found:
            score += len(complex_abbrev_found) * 0.4
            reasons.append(f"Complex abbreviations: {', '.join(complex_abbrev_found)}")
        
        # Check for technical terms
        technical_terms = [
            'depreciation', 'amortization', 'accrual', 'deferred', 'provision',
            'allocation', 'consolidation', 'subsidiary', 'segment', 'division'
        ]
        
        tech_terms_found = [term for term in technical_terms if term in query]
        if tech_terms_found:
            score += len(tech_terms_found) * 0.3
            reasons.append(f"Technical terms: {', '.join(tech_terms_found[:3])}")
        
        return score, reasons
    
    def _analyze_context_complexity(self, context: Dict) -> Tuple[float, List[str]]:
        """Analyze context for complexity indicators"""
        score = 0.0
        reasons = []
        
        # Check for complex context elements
        if context.get('filters'):
            filter_count = len(context['filters'])
            score += filter_count * 0.2
            reasons.append(f"Context filters: {filter_count}")
        
        if context.get('comparison_periods'):
            comp_count = len(context['comparison_periods'])
            score += comp_count * 0.3
            reasons.append(f"Comparison periods: {comp_count}")
        
        if context.get('previous_queries'):
            prev_count = len(context['previous_queries'])
            score += min(prev_count * 0.1, 0.5)
            reasons.append(f"Query history context: {prev_count}")
        
        return score, reasons
    
    def _determine_processing_path(self, complexity_score: float) -> Tuple[QueryComplexity, ProcessingPath, float]:
        """Determine complexity level and processing path based on score"""
        if complexity_score <= 1.0:
            return (
                QueryComplexity.SIMPLE,
                ProcessingPath.FAST_PATH,
                0.5  # 500ms estimated
            )
        elif complexity_score <= 3.0:
            return (
                QueryComplexity.MEDIUM,
                ProcessingPath.STANDARD_PATH,
                1.2  # 1.2s estimated
            )
        else:
            return (
                QueryComplexity.COMPLEX,
                ProcessingPath.COMPREHENSIVE_PATH,
                2.5  # 2.5s estimated
            )
    
    def _calculate_confidence(self, complexity_score: float, reasoning: List[str]) -> float:
        """Calculate confidence score for classification"""
        base_confidence = 0.7
        
        # More reasoning = higher confidence
        reasoning_boost = min(len(reasoning) * 0.05, 0.2)
        
        # Score extremes = higher confidence
        if complexity_score <= 0.5 or complexity_score >= 4.0:
            extreme_boost = 0.1
        else:
            extreme_boost = 0.0
        
        confidence = min(base_confidence + reasoning_boost + extreme_boost, 0.95)
        return round(confidence, 2)
    
    def get_optimization_suggestions(self, classification: QueryClassification) -> List[str]:
        """Get specific optimization suggestions based on classification"""
        suggestions = []
        
        if classification.complexity == QueryComplexity.SIMPLE:
            suggestions.extend([
                "Skip ambiguity detection for obvious queries",
                "Use single KIMI call for intent only",
                "Apply aggressive result caching (24h TTL)",
                "Use pre-built SQL templates if available",
                "Skip detailed entity extraction"
            ])
        
        elif classification.complexity == QueryComplexity.MEDIUM:
            suggestions.extend([
                "Use parallel KIMI calls for intent and entities",
                "Skip ambiguity detection if confidence > 0.8",
                "Use standard caching (6h TTL)",
                "Consider SQL template matching first"
            ])
        
        else:  # COMPLEX
            suggestions.extend([
                "Use full parallel processing pipeline",
                "Include comprehensive entity extraction",
                "Perform ambiguity detection and resolution",
                "Use semantic caching for similar complex queries",
                "Consider breaking query into sub-queries"
            ])
        
        return suggestions
    
    def should_use_fast_path(self, query: str, context: Optional[Dict] = None) -> bool:
        """Quick check if query should use fast path processing"""
        classification = self.classify_query(query, context)
        return classification.processing_path == ProcessingPath.FAST_PATH
    
    def estimate_processing_time(self, query: str, context: Optional[Dict] = None) -> float:
        """Estimate processing time for query"""
        classification = self.classify_query(query, context)
        return classification.estimated_processing_time
