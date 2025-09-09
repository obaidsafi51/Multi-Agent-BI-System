"""
Enhanced AI Semantic Mapper Integration.

This module provides integration between AI semantic mapping, user feedback,
and query success pattern analysis for continuous improvement.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from .ai_semantic_mapper import AISemanticSchemaMapper, AISemanticMapping
    from .user_feedback_system import UserFeedbackSystem, FeedbackType, MappingQuality
    from .query_success_analysis import QuerySuccessPatternAnalysis, QueryExecutionStatus
    from .config import MCPSchemaConfig
except ImportError:
    # Fallback for direct execution
    from ai_semantic_mapper import AISemanticSchemaMapper, AISemanticMapping
    from user_feedback_system import UserFeedbackSystem, FeedbackType, MappingQuality
    from query_success_analysis import QuerySuccessPatternAnalysis, QueryExecutionStatus
    from config import MCPSchemaConfig

logger = logging.getLogger(__name__)


class IntegratedAISemanticMapper:
    """
    Integrated AI Semantic Mapper with feedback learning and pattern analysis.
    
    This class combines AI-enhanced semantic mapping with user feedback learning
    and query success pattern analysis to continuously improve mapping accuracy.
    """
    
    def __init__(self, config: MCPSchemaConfig):
        self.config = config
        
        # Initialize components
        self.ai_mapper = AISemanticSchemaMapper(config)
        self.feedback_system = UserFeedbackSystem(config)
        self.pattern_analysis = QuerySuccessPatternAnalysis(config)
        
        # Integration settings
        self.integration_config = config.semantic_mapping.get('integration', {})
        self.auto_adjust_confidence = self.integration_config.get('auto_adjust_confidence', True)
        self.learning_enabled = self.integration_config.get('learning_enabled', True)
        self.min_feedback_for_adjustment = self.integration_config.get('min_feedback_for_adjustment', 5)
        
        logger.info("Integrated AI Semantic Mapper initialized")
    
    async def start(self):
        """Start the integrated mapping system."""
        await self.feedback_system.start()
        logger.info("Integrated AI Semantic Mapper started")
    
    async def stop(self):
        """Stop the integrated mapping system."""
        await self.feedback_system.stop()
        logger.info("Integrated AI Semantic Mapper stopped")
    
    async def map_business_term_enhanced(
        self,
        business_term: str,
        schema_elements: List[Dict[str, Any]],
        context: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[AISemanticMapping]:
        """
        Enhanced business term mapping with integrated learning.
        
        This method combines AI mapping with learned patterns from user feedback
        and query success analysis to provide improved mapping suggestions.
        """
        try:
            # 1. Get base AI mappings
            base_mappings = await self.ai_mapper.map_business_term_ai(
                business_term, schema_elements, context
            )
            
            if not base_mappings:
                logger.warning(f"No base mappings found for term: {business_term}")
                return []
            
            # 2. Apply learning-based enhancements
            enhanced_mappings = await self._enhance_mappings_with_learning(
                business_term, base_mappings, user_id
            )
            
            # 3. Apply pattern-based confidence adjustments
            if self.auto_adjust_confidence:
                pattern_adjusted_mappings = await self._apply_pattern_adjustments(
                    business_term, enhanced_mappings
                )
            else:
                pattern_adjusted_mappings = enhanced_mappings
            
            # 4. Add learned suggestions
            learned_suggestions = await self._get_learned_suggestions(
                business_term, schema_elements, user_id
            )
            
            # 5. Combine and rank all mappings
            final_mappings = await self._combine_and_rank_mappings(
                pattern_adjusted_mappings, learned_suggestions
            )
            
            logger.info(f"Enhanced mapping for '{business_term}': {len(final_mappings)} suggestions")
            return final_mappings
            
        except Exception as e:
            logger.error(f"Error in enhanced mapping for '{business_term}': {e}")
            # Fallback to base AI mapping
            return await self.ai_mapper.map_business_term_ai(business_term, schema_elements, context)
    
    async def _enhance_mappings_with_learning(
        self,
        business_term: str,
        base_mappings: List[AISemanticMapping],
        user_id: Optional[str] = None
    ) -> List[AISemanticMapping]:
        """Enhance mappings with learned patterns from feedback."""
        enhanced_mappings = []
        
        for mapping in base_mappings:
            enhanced_mapping = mapping
            
            # Apply feedback-based confidence boost
            if self.learning_enabled:
                confidence_boost = self.feedback_system.get_mapping_confidence_boost(
                    business_term, mapping.schema_element_path
                )
                
                if confidence_boost > 0:
                    new_confidence = min(mapping.confidence_score + confidence_boost, 1.0)
                    enhanced_mapping.confidence_score = new_confidence
                    enhanced_mapping.ai_explanation += f" (boosted by feedback: +{confidence_boost:.2f})"
                    
                    logger.debug(f"Applied feedback boost to '{business_term}': +{confidence_boost:.2f}")
            
            enhanced_mappings.append(enhanced_mapping)
        
        return enhanced_mappings
    
    async def _apply_pattern_adjustments(
        self,
        business_term: str,
        mappings: List[AISemanticMapping]
    ) -> List[AISemanticMapping]:
        """Apply confidence adjustments based on query success patterns."""
        adjusted_mappings = []
        
        for mapping in mappings:
            adjusted_mapping = mapping
            
            # Get pattern-based confidence adjustment
            pattern_confidence = self.pattern_analysis.get_mapping_confidence_adjustment(
                business_term,
                mapping.schema_element_path,
                mapping.confidence_score
            )
            
            if pattern_confidence != mapping.confidence_score:
                adjustment = pattern_confidence - mapping.confidence_score
                adjusted_mapping.confidence_score = pattern_confidence
                adjusted_mapping.ai_explanation += f" (pattern adjustment: {adjustment:+.2f})"
                
                logger.debug(f"Applied pattern adjustment to '{business_term}': {adjustment:+.2f}")
            
            adjusted_mappings.append(adjusted_mapping)
        
        return adjusted_mappings
    
    async def _get_learned_suggestions(
        self,
        business_term: str,
        schema_elements: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> List[AISemanticMapping]:
        """Get additional mapping suggestions from learned patterns."""
        learned_suggestions = []
        
        # Get learned mappings from feedback system
        learned_mappings = self.feedback_system.get_learned_mappings(business_term, user_id)
        
        # Get pattern-based recommendations
        pattern_recommendations = self.pattern_analysis.pattern_analyzer.get_mapping_recommendations(
            business_term, user_id
        )
        
        # Convert learned mappings to AISemanticMapping objects
        for learned_mapping in learned_mappings:
            # Check if this mapping is available in current schema
            table_name, column_name = learned_mapping.split('.', 1) if '.' in learned_mapping else ('', learned_mapping)
            
            for element in schema_elements:
                if (element.get('table_name') == table_name and 
                    element.get('column_name') == column_name):
                    
                    suggestion = AISemanticMapping(
                        business_term=business_term,
                        schema_element_type='column',
                        schema_element_path=learned_mapping,
                        confidence_score=0.8,  # High confidence for learned mappings
                        similarity_type='learned',
                        context_match=False,
                        metadata={
                            'table_name': table_name,
                            'column_name': column_name,
                            'source': 'feedback_learning'
                        },
                        created_at=datetime.now(),
                        ai_explanation="Learned from user feedback and corrections",
                        source_api='feedback_learning',
                        cost_tokens=0,
                        processing_time_ms=0
                    )
                    learned_suggestions.append(suggestion)
        
        # Add pattern-based recommendations
        for rec in pattern_recommendations:
            table_name, column_name = rec['mapping'].split('.', 1) if '.' in rec['mapping'] else ('', rec['mapping'])
            
            for element in schema_elements:
                if (element.get('table_name') == table_name and 
                    element.get('column_name') == column_name):
                    
                    suggestion = AISemanticMapping(
                        business_term=business_term,
                        schema_element_type='column',
                        schema_element_path=rec['mapping'],
                        confidence_score=0.7 + rec.get('confidence_boost', 0.0),
                        similarity_type='pattern_learned',
                        context_match=False,
                        metadata={
                            'table_name': table_name,
                            'column_name': column_name,
                            'source': 'pattern_analysis',
                            'success_rate': rec.get('success_rate', 0.0),
                            'usage_count': rec.get('usage_count', 0)
                        },
                        created_at=datetime.now(),
                        ai_explanation=f"Learned from query success patterns (success rate: {rec.get('success_rate', 0.0):.1%})",
                        source_api='pattern_analysis',
                        cost_tokens=0,
                        processing_time_ms=0
                    )
                    learned_suggestions.append(suggestion)
        
        return learned_suggestions
    
    async def _combine_and_rank_mappings(
        self,
        ai_mappings: List[AISemanticMapping],
        learned_mappings: List[AISemanticMapping]
    ) -> List[AISemanticMapping]:
        """Combine and rank all mapping suggestions."""
        all_mappings = []
        seen_paths = set()
        
        # Add AI mappings first (they have priority)
        for mapping in ai_mappings:
            if mapping.schema_element_path not in seen_paths:
                all_mappings.append(mapping)
                seen_paths.add(mapping.schema_element_path)
        
        # Add learned mappings that aren't duplicates
        for mapping in learned_mappings:
            if mapping.schema_element_path not in seen_paths:
                all_mappings.append(mapping)
                seen_paths.add(mapping.schema_element_path)
        
        # Sort by confidence score (descending)
        all_mappings.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Limit to top suggestions
        max_suggestions = self.ai_mapper.max_ai_suggestions
        return all_mappings[:max_suggestions]
    
    async def record_mapping_usage(
        self,
        user_id: str,
        session_id: str,
        business_term: str,
        selected_mapping: str,
        all_suggestions: List[AISemanticMapping],
        user_satisfaction: Optional[MappingQuality] = None,
        user_feedback_type: Optional[FeedbackType] = None,
        actual_mapping: Optional[str] = None,
        comments: str = ""
    ) -> str:
        """Record mapping usage for learning and analysis."""
        try:
            # Find the selected mapping in suggestions
            selected_suggestion = None
            for suggestion in all_suggestions:
                if suggestion.schema_element_path == selected_mapping:
                    selected_suggestion = suggestion
                    break
            
            if not selected_suggestion:
                logger.warning(f"Selected mapping '{selected_mapping}' not found in suggestions")
                return ""
            
            # Submit feedback
            feedback_id = await self.feedback_system.submit_feedback(
                user_id=user_id,
                session_id=session_id,
                business_term=business_term,
                suggested_mapping=selected_mapping,
                feedback_type=user_feedback_type or FeedbackType.POSITIVE,
                mapping_id=selected_suggestion.metadata.get('mapping_id', ''),
                actual_mapping=actual_mapping,
                quality_rating=user_satisfaction,
                comments=comments,
                ai_confidence=selected_suggestion.confidence_score,
                user_confidence=1.0 if user_satisfaction and user_satisfaction.value >= 4 else 0.5,
                processing_time_ms=selected_suggestion.processing_time_ms
            )
            
            logger.info(f"Recorded mapping usage: {feedback_id}")
            return feedback_id
            
        except Exception as e:
            logger.error(f"Error recording mapping usage: {e}")
            return ""
    
    async def record_query_execution_result(
        self,
        user_id: str,
        session_id: str,
        business_query: str,
        generated_sql: str,
        execution_status: QueryExecutionStatus,
        execution_time_ms: int,
        rows_returned: int,
        used_mappings: List[Dict[str, Any]],
        mapped_terms: List[str],
        ai_confidence_scores: List[float],
        error_message: Optional[str] = None,
        user_expertise_level: str = "unknown",
        query_intent: str = ""
    ) -> str:
        """Record query execution result for pattern analysis."""
        try:
            record_id = await self.pattern_analysis.record_query_execution(
                user_id=user_id,
                session_id=session_id,
                business_query=business_query,
                generated_sql=generated_sql,
                execution_status=execution_status,
                execution_time_ms=execution_time_ms,
                rows_returned=rows_returned,
                mapped_terms=mapped_terms,
                used_mappings=used_mappings,
                ai_confidence_scores=ai_confidence_scores,
                error_message=error_message,
                user_expertise_level=user_expertise_level,
                query_intent=query_intent
            )
            
            logger.info(f"Recorded query execution: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"Error recording query execution: {e}")
            return ""
    
    def get_optimal_confidence_threshold(self, business_term: Optional[str] = None) -> float:
        """Get optimal confidence threshold based on learned patterns."""
        return self.pattern_analysis.get_optimal_confidence_threshold(business_term)
    
    def get_system_analytics(self) -> Dict[str, Any]:
        """Get comprehensive system analytics."""
        return {
            'ai_mapper_status': {
                'ai_available': self.ai_mapper.is_ai_available(),
                'cache_size': len(self.ai_mapper.ai_mapping_cache),
                'fallback_enabled': self.ai_mapper.fallback_to_fuzzy
            },
            'feedback_analytics': self.feedback_system.get_feedback_analytics().to_dict() if hasattr(self.feedback_system.get_feedback_analytics(), 'to_dict') else {},
            'pattern_analytics': self.pattern_analysis.get_success_analytics(),
            'integration_config': {
                'auto_adjust_confidence': self.auto_adjust_confidence,
                'learning_enabled': self.learning_enabled,
                'min_feedback_for_adjustment': self.min_feedback_for_adjustment
            }
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status summary."""
        return {
            'ai_mapper': self.ai_mapper.is_ai_available(),
            'feedback_system': self.feedback_system.get_system_status(),
            'pattern_analysis': self.pattern_analysis.get_system_status(),
            'integration_active': True
        }
