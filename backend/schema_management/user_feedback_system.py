"""
User Feedback Integration System for AI-Enhanced Semantic Mapping.

This module provides comprehensive user feedback collection and analysis
to continuously improve semantic mapping quality and accuracy.
"""

import asyncio
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import statistics

try:
    from .ai_semantic_mapper import AISemanticMapping
    from .models import TableSchema, ColumnInfo
    from .config import MCPSchemaConfig
except ImportError:
    # Fallback for direct execution
    from ai_semantic_mapper import AISemanticMapping
    from models import TableSchema, ColumnInfo
    from config import MCPSchemaConfig

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of user feedback."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    CORRECTION = "correction"
    SUGGESTION = "suggestion"


class MappingQuality(Enum):
    """Quality ratings for mapping suggestions."""
    EXCELLENT = 5
    GOOD = 4
    FAIR = 3
    POOR = 2
    TERRIBLE = 1


@dataclass
class UserFeedback:
    """Individual user feedback record."""
    
    id: str
    user_id: str
    session_id: str
    timestamp: datetime
    feedback_type: FeedbackType
    mapping_id: str
    business_term: str
    suggested_mapping: str
    actual_mapping: Optional[str] = None
    quality_rating: Optional[MappingQuality] = None
    comments: str = ""
    context: Optional[str] = None
    ai_confidence: float = 0.0
    user_confidence: float = 0.0
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback to dictionary."""
        data = asdict(self)
        data['feedback_type'] = self.feedback_type.value
        if self.quality_rating:
            data['quality_rating'] = self.quality_rating.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class MappingCorrection:
    """User correction to a mapping suggestion."""
    
    feedback_id: str
    original_table: str
    original_column: str
    corrected_table: str
    corrected_column: str
    reason: str
    confidence_improvement: float = 0.0


@dataclass
class FeedbackAnalytics:
    """Analytics derived from user feedback."""
    
    total_feedback_count: int = 0
    positive_feedback_rate: float = 0.0
    average_quality_rating: float = 0.0
    top_problematic_terms: List[Tuple[str, int]] = None
    accuracy_improvement: float = 0.0
    user_satisfaction_score: float = 0.0
    common_correction_patterns: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.top_problematic_terms is None:
            self.top_problematic_terms = []
        if self.common_correction_patterns is None:
            self.common_correction_patterns = []


class FeedbackLearningEngine:
    """Engine for learning from user feedback to improve mappings."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_feedback_threshold = config.get('min_feedback_threshold', 5)
        self.confidence_adjustment_factor = config.get('confidence_adjustment_factor', 0.1)
        self.learning_rate = config.get('learning_rate', 0.05)
        
        # Learning data
        self.term_success_rates: Dict[str, float] = {}
        self.mapping_corrections: Dict[str, List[MappingCorrection]] = defaultdict(list)
        self.user_preferences: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        logger.info("Feedback learning engine initialized")
    
    def process_feedback(self, feedback: UserFeedback) -> Dict[str, Any]:
        """Process feedback and update learning models."""
        learning_updates = {
            'confidence_adjustments': [],
            'pattern_updates': [],
            'preference_updates': []
        }
        
        try:
            # Update success rates
            if feedback.quality_rating:
                self._update_term_success_rate(feedback.business_term, feedback.quality_rating)
                learning_updates['confidence_adjustments'].append({
                    'term': feedback.business_term,
                    'rating': feedback.quality_rating.value,
                    'adjustment': self._calculate_confidence_adjustment(feedback.quality_rating)
                })
            
            # Process corrections
            if feedback.feedback_type == FeedbackType.CORRECTION and feedback.actual_mapping:
                correction = self._extract_correction(feedback)
                if correction:
                    self.mapping_corrections[feedback.business_term].append(correction)
                    learning_updates['pattern_updates'].append({
                        'term': feedback.business_term,
                        'correction': asdict(correction)
                    })
            
            # Update user preferences
            self._update_user_preferences(feedback)
            learning_updates['preference_updates'].append({
                'user_id': feedback.user_id,
                'term': feedback.business_term,
                'preference_data': self.user_preferences[feedback.user_id]
            })
            
            logger.debug(f"Processed feedback for term '{feedback.business_term}': {feedback.feedback_type.value}")
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
        
        return learning_updates
    
    def _update_term_success_rate(self, term: str, rating: MappingQuality):
        """Update success rate for a business term."""
        # Convert rating to success score (0-1)
        success_score = (rating.value - 1) / 4  # Normalize to 0-1
        
        if term in self.term_success_rates:
            # Exponential moving average
            current_rate = self.term_success_rates[term]
            self.term_success_rates[term] = (
                (1 - self.learning_rate) * current_rate + 
                self.learning_rate * success_score
            )
        else:
            self.term_success_rates[term] = success_score
    
    def _calculate_confidence_adjustment(self, rating: MappingQuality) -> float:
        """Calculate confidence adjustment based on rating."""
        if rating.value >= 4:  # Good or excellent
            return self.confidence_adjustment_factor
        elif rating.value <= 2:  # Poor or terrible
            return -self.confidence_adjustment_factor
        else:  # Fair
            return 0.0
    
    def _extract_correction(self, feedback: UserFeedback) -> Optional[MappingCorrection]:
        """Extract correction information from feedback."""
        try:
            if not feedback.actual_mapping or not feedback.suggested_mapping:
                return None
            
            # Parse mappings (assuming format "table.column")
            suggested_parts = feedback.suggested_mapping.split('.')
            actual_parts = feedback.actual_mapping.split('.')
            
            if len(suggested_parts) != 2 or len(actual_parts) != 2:
                return None
            
            return MappingCorrection(
                feedback_id=feedback.id,
                original_table=suggested_parts[0],
                original_column=suggested_parts[1],
                corrected_table=actual_parts[0],
                corrected_column=actual_parts[1],
                reason=feedback.comments,
                confidence_improvement=self._calculate_confidence_improvement(feedback)
            )
        
        except Exception as e:
            logger.error(f"Error extracting correction: {e}")
            return None
    
    def _calculate_confidence_improvement(self, feedback: UserFeedback) -> float:
        """Calculate confidence improvement from user correction."""
        if feedback.user_confidence > feedback.ai_confidence:
            return feedback.user_confidence - feedback.ai_confidence
        return 0.0
    
    def _update_user_preferences(self, feedback: UserFeedback):
        """Update user-specific preferences."""
        user_prefs = self.user_preferences[feedback.user_id]
        
        # Track preferred mapping patterns
        if 'preferred_patterns' not in user_prefs:
            user_prefs['preferred_patterns'] = defaultdict(int)
        
        if feedback.actual_mapping:
            user_prefs['preferred_patterns'][feedback.actual_mapping] += 1
        
        # Track quality expectations
        if 'quality_expectations' not in user_prefs:
            user_prefs['quality_expectations'] = []
        
        if feedback.quality_rating:
            user_prefs['quality_expectations'].append(feedback.quality_rating.value)
            # Keep only recent expectations
            if len(user_prefs['quality_expectations']) > 20:
                user_prefs['quality_expectations'] = user_prefs['quality_expectations'][-20:]
    
    def get_confidence_boost(self, business_term: str, suggested_mapping: str) -> float:
        """Get confidence boost based on learned patterns."""
        boost = 0.0
        
        # Boost based on term success rate
        if business_term in self.term_success_rates:
            success_rate = self.term_success_rates[business_term]
            boost += success_rate * 0.1  # Max 10% boost
        
        # Boost based on corrections
        if business_term in self.mapping_corrections:
            corrections = self.mapping_corrections[business_term]
            for correction in corrections:
                corrected_mapping = f"{correction.corrected_table}.{correction.corrected_column}"
                if corrected_mapping == suggested_mapping:
                    boost += 0.15  # 15% boost for previously corrected mappings
        
        return min(boost, 0.25)  # Cap at 25% boost
    
    def get_mapping_suggestions(self, business_term: str, user_id: Optional[str] = None) -> List[str]:
        """Get mapping suggestions based on learned patterns."""
        suggestions = []
        
        # Get corrections for this term
        if business_term in self.mapping_corrections:
            corrections = self.mapping_corrections[business_term]
            for correction in corrections:
                suggestion = f"{correction.corrected_table}.{correction.corrected_column}"
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
        
        # Get user-specific preferences
        if user_id and user_id in self.user_preferences:
            user_prefs = self.user_preferences[user_id]
            preferred_patterns = user_prefs.get('preferred_patterns', {})
            
            # Sort by frequency and add to suggestions
            sorted_preferences = sorted(preferred_patterns.items(), key=lambda x: x[1], reverse=True)
            for pattern, _ in sorted_preferences[:3]:  # Top 3 preferences
                if pattern not in suggestions:
                    suggestions.append(pattern)
        
        return suggestions[:5]  # Return top 5 suggestions


class UserFeedbackSystem:
    """
    Comprehensive user feedback system for AI-enhanced semantic mapping.
    
    Collects, analyzes, and learns from user feedback to continuously
    improve mapping quality and accuracy.
    """
    
    def __init__(self, config: MCPSchemaConfig):
        self.config = config
        self.feedback_config = config.semantic_mapping.get('user_feedback', {})
        
        # Storage
        self.feedback_storage: List[UserFeedback] = []
        self.max_storage_size = self.feedback_config.get('max_storage_size', 10000)
        
        # Learning engine
        self.learning_engine = FeedbackLearningEngine(
            self.feedback_config.get('learning_config', {})
        )
        
        # Analytics
        self.analytics_cache: Optional[FeedbackAnalytics] = None
        self.analytics_cache_expiry: Optional[datetime] = None
        self.analytics_cache_ttl = timedelta(hours=1)
        
        # Feedback processing queue
        self.feedback_queue: deque = deque()
        self.processing_task: Optional[asyncio.Task] = None
        
        logger.info("User feedback system initialized")
    
    async def start(self):
        """Start the feedback processing system."""
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_feedback_queue())
            logger.info("Started feedback processing task")
    
    async def stop(self):
        """Stop the feedback processing system."""
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped feedback processing task")
    
    async def submit_feedback(
        self,
        user_id: str,
        session_id: str,
        business_term: str,
        suggested_mapping: str,
        feedback_type: FeedbackType,
        mapping_id: str = "",
        actual_mapping: Optional[str] = None,
        quality_rating: Optional[MappingQuality] = None,
        comments: str = "",
        context: Optional[str] = None,
        ai_confidence: float = 0.0,
        user_confidence: float = 0.0,
        processing_time_ms: int = 0
    ) -> str:
        """Submit user feedback for a semantic mapping."""
        
        feedback_id = f"fb_{int(datetime.utcnow().timestamp())}_{user_id}"
        
        feedback = UserFeedback(
            id=feedback_id,
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.utcnow(),
            feedback_type=feedback_type,
            mapping_id=mapping_id,
            business_term=business_term,
            suggested_mapping=suggested_mapping,
            actual_mapping=actual_mapping,
            quality_rating=quality_rating,
            comments=comments,
            context=context,
            ai_confidence=ai_confidence,
            user_confidence=user_confidence,
            processing_time_ms=processing_time_ms
        )
        
        # Add to queue for processing
        self.feedback_queue.append(feedback)
        
        logger.info(f"Feedback submitted: {feedback_id} for term '{business_term}'")
        return feedback_id
    
    async def _process_feedback_queue(self):
        """Process feedback queue continuously."""
        while True:
            try:
                if self.feedback_queue:
                    feedback = self.feedback_queue.popleft()
                    await self._process_feedback(feedback)
                else:
                    await asyncio.sleep(1)  # Wait before checking again
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing feedback queue: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_feedback(self, feedback: UserFeedback):
        """Process individual feedback."""
        try:
            # Store feedback
            self.feedback_storage.append(feedback)
            
            # Trim storage if needed
            if len(self.feedback_storage) > self.max_storage_size:
                self.feedback_storage = self.feedback_storage[-self.max_storage_size:]
            
            # Process with learning engine
            learning_updates = self.learning_engine.process_feedback(feedback)
            
            # Invalidate analytics cache
            self.analytics_cache = None
            self.analytics_cache_expiry = None
            
            logger.debug(f"Processed feedback {feedback.id}, learning updates: {len(learning_updates)}")
            
        except Exception as e:
            logger.error(f"Error processing feedback {feedback.id}: {e}")
    
    def get_mapping_confidence_boost(self, business_term: str, suggested_mapping: str) -> float:
        """Get confidence boost for a mapping based on feedback learning."""
        return self.learning_engine.get_confidence_boost(business_term, suggested_mapping)
    
    def get_learned_mappings(self, business_term: str, user_id: Optional[str] = None) -> List[str]:
        """Get learned mapping suggestions for a business term."""
        return self.learning_engine.get_mapping_suggestions(business_term, user_id)
    
    def get_feedback_analytics(self, force_refresh: bool = False) -> FeedbackAnalytics:
        """Get comprehensive feedback analytics."""
        # Check cache
        if (not force_refresh and 
            self.analytics_cache is not None and 
            self.analytics_cache_expiry is not None and
            datetime.utcnow() < self.analytics_cache_expiry):
            return self.analytics_cache
        
        # Calculate analytics
        analytics = self._calculate_analytics()
        
        # Cache results
        self.analytics_cache = analytics
        self.analytics_cache_expiry = datetime.utcnow() + self.analytics_cache_ttl
        
        return analytics
    
    def _calculate_analytics(self) -> FeedbackAnalytics:
        """Calculate comprehensive feedback analytics."""
        if not self.feedback_storage:
            return FeedbackAnalytics()
        
        # Basic counts
        total_count = len(self.feedback_storage)
        positive_count = len([f for f in self.feedback_storage if f.feedback_type == FeedbackType.POSITIVE])
        
        # Quality ratings
        quality_ratings = [f.quality_rating.value for f in self.feedback_storage if f.quality_rating]
        avg_quality = statistics.mean(quality_ratings) if quality_ratings else 0.0
        
        # Problematic terms
        term_issues = defaultdict(int)
        for feedback in self.feedback_storage:
            if (feedback.feedback_type in [FeedbackType.NEGATIVE, FeedbackType.CORRECTION] or
                (feedback.quality_rating and feedback.quality_rating.value <= 2)):
                term_issues[feedback.business_term] += 1
        
        top_problematic = sorted(term_issues.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Correction patterns
        correction_patterns = []
        for term, corrections in self.learning_engine.mapping_corrections.items():
            if len(corrections) >= 2:  # Only include patterns with multiple corrections
                pattern = {
                    'business_term': term,
                    'correction_count': len(corrections),
                    'common_corrections': list(set([
                        f"{c.corrected_table}.{c.corrected_column}" for c in corrections
                    ]))[:3]
                }
                correction_patterns.append(pattern)
        
        # User satisfaction (based on quality ratings and positive feedback)
        satisfaction_factors = []
        if quality_ratings:
            satisfaction_factors.append(avg_quality / 5.0)  # Normalize to 0-1
        if total_count > 0:
            satisfaction_factors.append(positive_count / total_count)
        
        satisfaction_score = statistics.mean(satisfaction_factors) if satisfaction_factors else 0.0
        
        return FeedbackAnalytics(
            total_feedback_count=total_count,
            positive_feedback_rate=(positive_count / total_count) * 100 if total_count > 0 else 0.0,
            average_quality_rating=avg_quality,
            top_problematic_terms=top_problematic,
            user_satisfaction_score=satisfaction_score * 100,  # Convert to percentage
            common_correction_patterns=correction_patterns
        )
    
    def get_user_feedback_history(self, user_id: str, days: int = 30) -> List[UserFeedback]:
        """Get feedback history for a specific user."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return [
            feedback for feedback in self.feedback_storage
            if feedback.user_id == user_id and feedback.timestamp >= cutoff_date
        ]
    
    def get_term_feedback_history(self, business_term: str, days: int = 30) -> List[UserFeedback]:
        """Get feedback history for a specific business term."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return [
            feedback for feedback in self.feedback_storage
            if feedback.business_term == business_term and feedback.timestamp >= cutoff_date
        ]
    
    def export_feedback_data(self, format: str = "json") -> str:
        """Export feedback data for analysis."""
        if format.lower() == "json":
            feedback_data = [feedback.to_dict() for feedback in self.feedback_storage]
            return json.dumps({
                'feedback_data': feedback_data,
                'analytics': asdict(self.get_feedback_analytics()),
                'export_timestamp': datetime.utcnow().isoformat()
            }, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get user feedback system status."""
        return {
            'feedback_count': len(self.feedback_storage),
            'queue_size': len(self.feedback_queue),
            'processing_active': self.processing_task is not None and not self.processing_task.done(),
            'learned_terms': len(self.learning_engine.term_success_rates),
            'correction_patterns': len(self.learning_engine.mapping_corrections),
            'user_preferences': len(self.learning_engine.user_preferences),
            'cache_status': {
                'analytics_cached': self.analytics_cache is not None,
                'cache_expiry': self.analytics_cache_expiry.isoformat() if self.analytics_cache_expiry else None
            }
        }
