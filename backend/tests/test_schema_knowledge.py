"""
Unit tests for Schema Knowledge Base component.
"""

import pytest
import json
import tempfile
import os
from datetime import date, datetime
from pathlib import Path

from backend.schema_knowledge import (
    SchemaKnowledgeBase, 
    TermMapper, 
    QueryTemplateEngine, 
    TimeProcessor
)
from backend.schema_knowledge.similarity_matcher import SimilarityMatcher
from backend.models.core import QueryIntent, FinancialEntity


class TestTermMapper:
    """Test cases for TermMapper component"""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing"""
        config = {
            "financial_metrics": {
                "revenue": {
                    "synonyms": ["sales", "income", "turnover"],
                    "database_mapping": "financial_overview.revenue",
                    "description": "Total income from business operations",
                    "category": "income_statement",
                    "data_type": "decimal",
                    "aggregation_methods": ["sum", "avg"],
                    "time_sensitive": True
                },
                "profit": {
                    "synonyms": ["net profit", "earnings", "bottom line"],
                    "database_mapping": "financial_overview.net_profit",
                    "description": "Total earnings after expenses",
                    "category": "income_statement",
                    "data_type": "decimal",
                    "aggregation_methods": ["sum", "avg"],
                    "time_sensitive": True
                }
            },
            "departments": {
                "sales": {
                    "synonyms": ["sales team", "revenue team"],
                    "database_mapping": "budget_tracking.department = 'sales'",
                    "description": "Sales department"
                }
            }
        }
        return config
    
    @pytest.fixture
    def term_mapper(self, sample_config):
        """Create TermMapper with sample configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "business_terms.json"
            with open(config_file, 'w') as f:
                json.dump(sample_config, f)
            
            yield TermMapper(temp_dir)
    
    def test_direct_term_mapping(self, term_mapper):
        """Test direct term mapping"""
        entity = term_mapper.map_term("revenue")
        
        assert entity is not None
        assert entity.entity_type == "metric"
        assert entity.entity_value == "revenue"
        assert entity.confidence_score == 1.0
        assert entity.database_mapping == "financial_overview.revenue"
        assert "sales" in entity.synonyms
    
    def test_synonym_mapping(self, term_mapper):
        """Test synonym mapping"""
        entity = term_mapper.map_term("sales")
        
        assert entity is not None
        assert entity.entity_value == "revenue"
        assert entity.confidence_score == 1.0
    
    def test_fuzzy_matching(self, term_mapper):
        """Test fuzzy matching for similar terms"""
        entity = term_mapper.map_term("revenu")  # Missing 'e'
        
        assert entity is not None
        assert entity.entity_value == "revenue"
        assert entity.confidence_score < 1.0
        assert entity.confidence_score >= 0.7
    
    def test_unknown_term(self, term_mapper):
        """Test handling of unknown terms"""
        entity = term_mapper.map_term("unknown_metric")
        assert entity is None
    
    def test_similar_terms_suggestion(self, term_mapper):
        """Test similar terms suggestion"""
        similar_terms = term_mapper.get_similar_terms("revenu", limit=3)
        
        assert len(similar_terms) > 0
        assert similar_terms[0][0] == "revenue"
        assert similar_terms[0][1] >= 0.7
    
    def test_department_mapping(self, term_mapper):
        """Test department term mapping"""
        entity = term_mapper.map_term("sales")
        
        # Note: This might map to revenue or sales department depending on implementation
        assert entity is not None
        assert entity.entity_value in ["revenue", "sales"]
    
    def test_aggregation_methods(self, term_mapper):
        """Test aggregation methods retrieval"""
        methods = term_mapper.get_aggregation_methods("revenue")
        
        assert "sum" in methods
        assert "avg" in methods
    
    def test_term_statistics(self, term_mapper):
        """Test term statistics"""
        stats = term_mapper.get_term_statistics()
        
        assert stats["total_terms"] >= 2
        assert stats["total_synonyms"] >= 4
        assert "income_statement" in stats["categories"]


class TestQueryTemplateEngine:
    """Test cases for QueryTemplateEngine component"""
    
    @pytest.fixture
    def sample_templates(self):
        """Create sample query templates"""
        templates = {
            "financial_overview_queries": {
                "basic_metric": {
                    "template": "SELECT {time_column}, {metric_columns} FROM financial_overview WHERE {time_filter} ORDER BY {time_column}",
                    "description": "Basic financial metric query",
                    "parameters": {
                        "time_column": "period_date",
                        "metric_columns": "revenue",
                        "time_filter": "period_date >= '{start_date}' AND period_date <= '{end_date}'"
                    },
                    "supports_aggregation": True,
                    "supports_comparison": True
                }
            }
        }
        return templates
    
    @pytest.fixture
    def query_engine(self, sample_templates):
        """Create QueryTemplateEngine with sample templates"""
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_file = Path(temp_dir) / "query_templates.json"
            with open(templates_file, 'w') as f:
                json.dump(sample_templates, f)
            
            yield QueryTemplateEngine(temp_dir)
    
    def test_template_selection(self, query_engine):
        """Test template selection based on query intent"""
        query_intent = QueryIntent(
            metric_type="revenue",
            time_period="Q1 2024",
            aggregation_level="monthly"
        )
        
        template_name = query_engine.select_template(query_intent)
        assert template_name is not None
        assert "basic_metric" in template_name or "revenue_analysis" in template_name
    
    def test_query_generation(self, query_engine):
        """Test SQL query generation"""
        query_intent = QueryIntent(
            metric_type="revenue",
            time_period="Q1 2024",
            aggregation_level="monthly"
        )
        
        generated_query = query_engine.generate_query(query_intent)
        
        assert generated_query.sql is not None
        assert "SELECT" in generated_query.sql.upper()
        assert "FROM" in generated_query.sql.upper()
        assert "financial_overview" in generated_query.sql
        assert generated_query.estimated_complexity in ["low", "medium", "high"]
    
    def test_parameter_substitution(self, query_engine):
        """Test parameter substitution in templates"""
        query_intent = QueryIntent(
            metric_type="revenue",
            time_period="2024",
            aggregation_level="monthly"
        )
        
        generated_query = query_engine.generate_query(query_intent)
        
        # Check that parameters were substituted
        assert "{time_column}" not in generated_query.sql
        assert "{metric_columns}" not in generated_query.sql
        assert "2024" in generated_query.sql
    
    def test_query_optimization(self, query_engine):
        """Test query optimization"""
        query_intent = QueryIntent(
            metric_type="revenue",
            time_period="last 5 years",
            aggregation_level="daily"
        )
        
        generated_query = query_engine.generate_query(query_intent)
        optimized_query = query_engine.optimize_query(generated_query)
        
        # High complexity queries should have LIMIT added
        if optimized_query.estimated_complexity == "high":
            assert "LIMIT" in optimized_query.sql.upper()


class TestSimilarityMatcher:
    """Test cases for SimilarityMatcher component"""
    
    @pytest.fixture
    def similarity_matcher(self):
        """Create SimilarityMatcher instance"""
        return SimilarityMatcher(similarity_threshold=0.7)
    
    def test_exact_match(self, similarity_matcher):
        """Test exact matching"""
        known_terms = ["revenue", "profit", "expenses"]
        matches = similarity_matcher.find_best_matches("revenue", known_terms)
        
        assert len(matches) > 0
        assert matches[0].similarity_score == 1.0
        assert matches[0].match_type == "exact"
        assert matches[0].canonical_term == "revenue"
    
    def test_fuzzy_match(self, similarity_matcher):
        """Test fuzzy matching"""
        known_terms = ["revenue", "profit", "expenses"]
        matches = similarity_matcher.find_best_matches("revenu", known_terms)
        
        assert len(matches) > 0
        assert matches[0].canonical_term == "revenue"
        assert matches[0].match_type == "fuzzy"
        assert matches[0].similarity_score >= 0.7
    
    def test_abbreviation_match(self, similarity_matcher):
        """Test abbreviation matching"""
        known_terms = ["revenue", "profit", "cash_flow"]
        matches = similarity_matcher.find_best_matches("cf", known_terms)
        
        # Should find cash_flow through abbreviation mapping
        cash_flow_matches = [m for m in matches if "cash" in m.canonical_term]
        assert len(cash_flow_matches) > 0
    
    def test_phonetic_match(self, similarity_matcher):
        """Test phonetic matching"""
        known_terms = ["revenue", "profit", "expenses"]
        matches = similarity_matcher.find_best_matches("revnue", known_terms)
        
        assert len(matches) > 0
        # Should find revenue through phonetic similarity
        revenue_matches = [m for m in matches if m.canonical_term == "revenue"]
        assert len(revenue_matches) > 0
    
    def test_similarity_threshold(self, similarity_matcher):
        """Test similarity threshold configuration"""
        similarity_matcher.set_similarity_threshold(0.9)
        
        known_terms = ["revenue", "profit", "expenses"]
        matches = similarity_matcher.find_best_matches("revenu", known_terms)
        
        # With high threshold, fuzzy matches might be filtered out
        for match in matches:
            assert match.similarity_score >= 0.9
    
    def test_spelling_corrections(self, similarity_matcher):
        """Test spelling correction suggestions"""
        corrections = similarity_matcher.suggest_corrections("revenu")
        
        assert len(corrections) > 0
        assert "revenue" in corrections


class TestTimeProcessor:
    """Test cases for TimeProcessor component"""
    
    @pytest.fixture
    def time_processor(self):
        """Create TimeProcessor instance"""
        return TimeProcessor(fiscal_year_start_month=1)
    
    def test_quarterly_parsing(self, time_processor):
        """Test quarterly time period parsing"""
        period = time_processor.parse_time_period("Q1 2024")
        
        assert period.period_type.value == "quarterly"
        assert period.quarter == 1
        assert period.year == 2024
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 3, 31)
        assert "Q1 2024" in period.period_label
    
    def test_monthly_parsing(self, time_processor):
        """Test monthly time period parsing"""
        period = time_processor.parse_time_period("January 2024")
        
        assert period.period_type.value == "monthly"
        assert period.month == 1
        assert period.year == 2024
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 1, 31)
    
    def test_yearly_parsing(self, time_processor):
        """Test yearly time period parsing"""
        period = time_processor.parse_time_period("2024")
        
        assert period.period_type.value == "yearly"
        assert period.year == 2024
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 12, 31)
    
    def test_relative_periods(self, time_processor):
        """Test relative time period parsing"""
        # Use specific reference date to ensure consistent test behavior
        reference_date = date(2025, 8, 30)  # August 30, 2025
        period = time_processor.parse_time_period("this quarter", reference_date)
        
        assert period.period_type.value == "quarterly"
        assert period.is_partial  # Current quarter is typically partial
    
    def test_range_periods(self, time_processor):
        """Test range-based time periods"""
        period = time_processor.parse_time_period("last 6 months")
        
        assert period.period_type.value == "monthly"
        assert "6 months" in period.period_label
        # Should be approximately 6 months duration
        duration = period.end_date - period.start_date
        assert 150 <= duration.days <= 200  # Approximate 6 months
    
    def test_comparison_periods(self, time_processor):
        """Test comparison period generation"""
        base_period = time_processor.parse_time_period("Q1 2024")
        comparison = time_processor.parse_comparison("vs last year", base_period)
        
        assert comparison is not None
        assert comparison.comparison_type == "year_over_year"
        assert comparison.comparison_period.year == 2023
        assert comparison.comparison_period.quarter == 1
    
    def test_period_validation(self, time_processor):
        """Test time period validation"""
        period = time_processor.parse_time_period("Q1 2024")
        validation = time_processor.validate_time_period(period)
        
        assert validation["is_valid"]
        assert validation["duration_days"] > 0
    
    def test_fiscal_year_handling(self):
        """Test fiscal year handling"""
        # Fiscal year starting in April
        fiscal_processor = TimeProcessor(fiscal_year_start_month=4)
        period = fiscal_processor.parse_time_period("Q1 2024")
        
        # Q1 of fiscal year should start in April
        assert period.start_date.month == 4


class TestSchemaKnowledgeBase:
    """Test cases for main SchemaKnowledgeBase component"""
    
    @pytest.fixture
    def knowledge_base(self):
        """Create SchemaKnowledgeBase with sample configuration"""
        # Create temporary config files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create minimal config files
            business_terms = {
                "financial_metrics": {
                    "revenue": {
                        "synonyms": ["sales", "income"],
                        "database_mapping": "financial_overview.revenue",
                        "category": "income_statement",
                        "data_type": "decimal",
                        "aggregation_methods": ["sum"]
                    }
                }
            }
            
            query_templates = {
                "financial_overview_queries": {
                    "basic_metric": {
                        "template": "SELECT {time_column}, {metric_columns} FROM financial_overview WHERE {time_filter}",
                        "description": "Basic query",
                        "parameters": {"time_column": "period_date"},
                        "supports_aggregation": True,
                        "supports_comparison": True
                    }
                }
            }
            
            metrics_config = {
                "metric_definitions": {
                    "revenue": {
                        "display_name": "Revenue",
                        "visualization_preferences": {
                            "primary_chart": "line"
                        }
                    }
                }
            }
            
            # Write config files
            with open(Path(temp_dir) / "business_terms.json", 'w') as f:
                json.dump(business_terms, f)
            with open(Path(temp_dir) / "query_templates.json", 'w') as f:
                json.dump(query_templates, f)
            with open(Path(temp_dir) / "metrics_config.json", 'w') as f:
                json.dump(metrics_config, f)
            
            yield SchemaKnowledgeBase(temp_dir)
    
    def test_query_intent_processing(self, knowledge_base):
        """Test complete query intent processing"""
        query = "Show me revenue for Q1 2024"
        
        query_intent = knowledge_base.process_query_intent(query)
        
        assert query_intent.metric_type == "revenue"
        assert "Q1" in query_intent.time_period or "2024" in query_intent.time_period
        assert query_intent.confidence_score > 0.5
    
    def test_entity_extraction(self, knowledge_base):
        """Test financial entity extraction"""
        query = "Show me sales and profit for this quarter"
        
        entities = knowledge_base.extract_financial_entities(query)
        
        assert len(entities) >= 1
        # Should find revenue (mapped from sales)
        entity_values = [e.entity_value for e in entities]
        assert "revenue" in entity_values
    
    def test_time_period_extraction(self, knowledge_base):
        """Test time period extraction"""
        query = "Show me revenue for Q1 2024"
        
        time_period = knowledge_base.extract_time_period(query)
        
        assert time_period is not None
        assert time_period.period_type.value == "quarterly"
        assert time_period.quarter == 1
        assert time_period.year == 2024
    
    def test_sql_generation(self, knowledge_base):
        """Test SQL query generation"""
        query_intent = QueryIntent(
            metric_type="revenue",
            time_period="Q1 2024",
            aggregation_level="monthly"
        )
        
        generated_query = knowledge_base.generate_sql_query(query_intent)
        
        assert generated_query.sql is not None
        assert "SELECT" in generated_query.sql.upper()
        assert "revenue" in generated_query.sql
    
    def test_similar_terms_finding(self, knowledge_base):
        """Test similar terms finding"""
        similar_terms = knowledge_base.find_similar_terms("revenu")
        
        assert len(similar_terms) > 0
        assert similar_terms[0].canonical_term == "revenue"
    
    def test_query_correction_suggestions(self, knowledge_base):
        """Test query correction suggestions"""
        failed_query = "Show me revenu for Q1"
        
        error_response = knowledge_base.suggest_query_corrections(failed_query)
        
        assert error_response.error_type in ["unknown_terms", "ambiguous_terms", "processing_error"]
        assert len(error_response.suggestions) > 0
    
    def test_query_enhancement_suggestions(self, knowledge_base):
        """Test query enhancement suggestions"""
        query_intent = QueryIntent(
            metric_type="revenue",
            time_period="Q1 2024",
            aggregation_level="monthly"
        )
        
        suggestions = knowledge_base.get_query_enhancement_suggestions(query_intent)
        
        assert len(suggestions) > 0
        assert any("comparison" in s.lower() for s in suggestions)
    
    def test_query_validation(self, knowledge_base):
        """Test query intent validation"""
        query_intent = QueryIntent(
            metric_type="revenue",
            time_period="Q1 2024",
            aggregation_level="monthly"
        )
        
        validation = knowledge_base.validate_query_intent(query_intent)
        
        assert validation["is_valid"]
        assert validation["confidence_score"] > 0
    
    def test_metric_metadata(self, knowledge_base):
        """Test metric metadata retrieval"""
        metadata = knowledge_base.get_metric_metadata("revenue")
        
        assert metadata is not None
        assert metadata["display_name"] == "Revenue"
    
    def test_visualization_config(self, knowledge_base):
        """Test visualization configuration"""
        viz_config = knowledge_base.get_visualization_config("revenue")
        
        assert viz_config["primary_chart"] == "line"
    
    def test_statistics(self, knowledge_base):
        """Test knowledge base statistics"""
        stats = knowledge_base.get_statistics()
        
        assert "term_mappings" in stats
        assert "available_templates" in stats
        assert "cache_performance" in stats
    
    def test_cache_functionality(self, knowledge_base):
        """Test query caching"""
        query_intent = QueryIntent(
            metric_type="revenue",
            time_period="Q1 2024",
            aggregation_level="monthly"
        )
        
        # First call should be a cache miss
        generated_query1 = knowledge_base.generate_sql_query(query_intent)
        
        # Second call should be a cache hit
        generated_query2 = knowledge_base.generate_sql_query(query_intent)
        
        assert generated_query1.sql == generated_query2.sql
        
        stats = knowledge_base.get_statistics()
        assert stats["cache_performance"]["hits"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])