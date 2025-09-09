"""
Comprehensive test suite for Phase 2: Semantic Understanding and Query Intelligence.

Tests for:
- SemanticSchemaMapper (Task 4)
- IntelligentQueryBuilder (Task 5) 
- SchemaChangeDetector (Task 6)
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

# Import the modules under test
from backend.schema_management.semantic_mapper import (
    SemanticSchemaMapper, SemanticMappingConfig, SemanticMapping,
    BusinessTerm, SchemaElement, MappingCandidate
)
from backend.schema_management.query_builder import (
    IntelligentQueryBuilder, QueryIntent, QueryContext, QueryResult,
    TableMapping, ColumnMapping, QueryPlan, AggregationType
)
from backend.schema_management.change_detector import (
    SchemaChangeDetector, SchemaChange, ChangeType, ChangeSeverity,
    SchemaSnapshot
)
from backend.schema_management.models import (
    TableSchema, ColumnInfo, TableInfo, DatabaseInfo
)


class TestSemanticSchemaMapper:
    """Test suite for SemanticSchemaMapper."""
    
    @pytest.fixture
    def mapper_config(self):
        """Create test configuration for semantic mapper."""
        return SemanticMappingConfig(
            confidence_threshold=0.6,
            max_suggestions=3,
            enable_fuzzy_matching=True,
            enable_semantic_similarity=False,  # Disable for testing without NLTK
            fuzzy_threshold=0.5,
            learning_enabled=True
        )
    
    @pytest.fixture
    def semantic_mapper(self, mapper_config):
        """Create semantic mapper instance for testing."""
        return SemanticSchemaMapper(config=mapper_config)
    
    @pytest.fixture
    def sample_table_schema(self):
        """Create sample table schema for testing."""
        columns = [
            ColumnInfo(
                name="order_id",
                data_type="int",
                is_nullable=False,
                default_value=None,
                is_primary_key=True,
                is_foreign_key=False,
                comment="Unique order identifier"
            ),
            ColumnInfo(
                name="customer_id",
                data_type="int",
                is_nullable=False,
                default_value=None,
                is_primary_key=False,
                is_foreign_key=True,
                comment="Customer reference"
            ),
            ColumnInfo(
                name="total_amount",
                data_type="decimal(10,2)",
                is_nullable=False,
                default_value="0.00",
                is_primary_key=False,
                is_foreign_key=False,
                comment="Total order amount"
            ),
            ColumnInfo(
                name="order_date",
                data_type="datetime",
                is_nullable=False,
                default_value="CURRENT_TIMESTAMP",
                is_primary_key=False,
                is_foreign_key=False,
                comment="When the order was placed"
            )
        ]
        
        return TableSchema(
            database="test_db",
            table="orders",
            columns=columns,
            indexes=[],
            primary_keys=["order_id"],
            foreign_keys=[],
            constraints=[],
            table_info=TableInfo(
                name="orders",
                type="BASE TABLE",
                engine="InnoDB",
                rows=10000,
                size_mb=50.0,
                comment="Customer orders table"
            )
        )
    
    def test_load_default_business_terms(self, semantic_mapper):
        """Test loading of default business terms."""
        assert len(semantic_mapper.business_terms) > 0
        assert 'revenue' in semantic_mapper.business_terms
        assert 'customer' in semantic_mapper.business_terms
        
        revenue_term = semantic_mapper.business_terms['revenue']
        assert revenue_term.primary_term == 'revenue'
        assert 'sales' in revenue_term.synonyms
        assert revenue_term.category == 'financial'
    
    def test_add_business_term(self, semantic_mapper):
        """Test adding new business terms."""
        new_term = BusinessTerm(
            primary_term='profit_margin',
            synonyms=['margin', 'profitability'],
            category='financial',
            description='Profit as percentage of revenue',
            context_keywords=['profit', 'margin', 'percentage']
        )
        
        semantic_mapper.add_business_term(new_term)
        assert 'profit_margin' in semantic_mapper.business_terms
        
        stored_term = semantic_mapper.business_terms['profit_margin']
        assert stored_term.primary_term == 'profit_margin'
        assert 'margin' in stored_term.synonyms
    
    @pytest.mark.asyncio
    async def test_analyze_table_schema(self, semantic_mapper, sample_table_schema):
        """Test schema analysis for semantic information extraction."""
        schema_element = await semantic_mapper.analyze_table_schema(sample_table_schema)
        
        assert schema_element.element_type == 'table'
        assert schema_element.name == 'orders'
        assert 'order' in schema_element.business_concepts
        
        # Check that columns were analyzed and added to schema elements
        assert len(semantic_mapper.schema_elements) >= 5  # 1 table + 4 columns
    
    def test_extract_business_concepts(self, semantic_mapper):
        """Test business concept extraction from names and comments."""
        # Test with order-related text
        concepts = semantic_mapper._extract_business_concepts(
            "order_total", 
            "Total amount for customer order"
        )
        assert 'order' in concepts
        
        # Test with revenue-related text
        concepts = semantic_mapper._extract_business_concepts(
            "sales_amount",
            "Revenue from sales transactions"
        )
        assert 'revenue' in concepts
    
    def test_generate_semantic_tags(self, semantic_mapper):
        """Test semantic tag generation."""
        # Test identifier tags
        tags = semantic_mapper._generate_semantic_tags("user_id", None)
        assert 'identifier' in tags
        
        # Test temporal tags
        tags = semantic_mapper._generate_semantic_tags("created_at", "When record was created")
        assert 'temporal' in tags
        
        # Test monetary tags
        tags = semantic_mapper._generate_semantic_tags("price", "Product price")
        assert 'monetary' in tags
        
        # Test boolean tags
        tags = semantic_mapper._generate_semantic_tags("is_active", "Whether user is active")
        assert 'boolean' in tags
    
    def test_calculate_fuzzy_similarity(self, semantic_mapper):
        """Test fuzzy string similarity calculation."""
        element = SchemaElement(
            element_type='column',
            full_path='test.orders.customer_id',
            name='customer_id',
            description='Customer identifier',
            semantic_tags=['identifier'],
            business_concepts=['customer'],
            data_type='int',
            sample_values=None,
            usage_patterns={}
        )
        
        # Test exact match
        similarity = semantic_mapper._calculate_fuzzy_similarity('customer_id', element)
        assert similarity == 1.0
        
        # Test partial match
        similarity = semantic_mapper._calculate_fuzzy_similarity('customer', element)
        assert similarity > 0.5
        
        # Test no match
        similarity = semantic_mapper._calculate_fuzzy_similarity('unrelated', element)
        assert similarity < 0.3
    
    def test_calculate_concept_similarity(self, semantic_mapper):
        """Test business concept similarity calculation."""
        element = SchemaElement(
            element_type='column',
            full_path='test.orders.customer_id',
            name='customer_id',
            description='Customer identifier',
            semantic_tags=['identifier'],
            business_concepts=['customer'],
            data_type='int',
            sample_values=None,
            usage_patterns={}
        )
        
        # Test direct concept match
        similarity = semantic_mapper._calculate_concept_similarity('customer', element)
        assert similarity == 1.0
        
        # Test synonym match
        similarity = semantic_mapper._calculate_concept_similarity('client', element)
        assert similarity > 0.5  # 'client' is a synonym of 'customer'
        
        # Test no concept match
        similarity = semantic_mapper._calculate_concept_similarity('product', element)
        assert similarity < 0.3
    
    @pytest.mark.asyncio
    async def test_map_business_term_simple(self, semantic_mapper, sample_table_schema):
        """Test simple business term mapping."""
        # Analyze the table schema first
        await semantic_mapper.analyze_table_schema(sample_table_schema)
        
        # Map business term to schema elements
        mappings = await semantic_mapper.map_business_term('customer')
        
        assert len(mappings) > 0
        assert any(mapping.schema_element_path.endswith('customer_id') for mapping in mappings)
        
        # Check confidence scores
        for mapping in mappings:
            assert mapping.confidence_score >= semantic_mapper.config.confidence_threshold
    
    def test_learn_successful_mapping(self, semantic_mapper):
        """Test learning from successful mappings."""
        mapping = SemanticMapping(
            business_term='revenue',
            schema_element_type='column',
            schema_element_path='test.sales.amount',
            confidence_score=0.8,
            similarity_type='semantic',
            context_match=True,
            metadata={},
            created_at=datetime.now()
        )
        
        # Learn from successful mapping
        semantic_mapper.learn_successful_mapping(mapping, success_score=1.0)
        
        # Check that mapping was learned
        learned = semantic_mapper._get_learned_mappings('revenue')
        assert len(learned) == 1
        assert learned[0].schema_element_path == 'test.sales.amount'
        assert learned[0].confidence_score > 0.8  # Should be boosted
    
    @pytest.mark.asyncio
    async def test_suggest_alternative_terms(self, semantic_mapper):
        """Test alternative term suggestions."""
        suggestions = await semantic_mapper.suggest_alternative_terms('revenu')  # Misspelled
        
        assert len(suggestions) > 0
        assert 'revenue' in suggestions  # Should suggest the correct spelling
    
    def test_get_mapping_statistics(self, semantic_mapper, sample_table_schema):
        """Test mapping statistics generation."""
        stats = semantic_mapper.get_mapping_statistics()
        
        assert 'total_schema_elements' in stats
        assert 'total_business_terms' in stats
        assert 'configuration' in stats
        assert stats['total_business_terms'] > 0


class TestIntelligentQueryBuilder:
    """Test suite for IntelligentQueryBuilder."""
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create mock schema manager."""
        manager = Mock()
        manager.discover_databases = AsyncMock(return_value=[
            DatabaseInfo(name="test_db", charset="utf8", collation="utf8_general_ci", accessible=True)
        ])
        manager.get_tables = AsyncMock(return_value=[
            TableInfo(name="orders", type="BASE TABLE", engine="InnoDB", rows=1000, size_mb=10.0)
        ])
        manager.get_table_schema = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_semantic_mapper(self):
        """Create mock semantic mapper."""
        mapper = Mock()
        mapper.map_business_term = AsyncMock()
        mapper.suggest_alternative_terms = AsyncMock(return_value=['sales', 'income'])
        return mapper
    
    @pytest.fixture
    def query_builder(self, mock_schema_manager, mock_semantic_mapper):
        """Create query builder instance."""
        return IntelligentQueryBuilder(
            schema_manager=mock_schema_manager,
            semantic_mapper=mock_semantic_mapper
        )
    
    @pytest.fixture
    def sample_query_intent(self):
        """Create sample query intent."""
        return QueryIntent(
            metric_type='revenue',
            filters={'region': 'north', 'year': 2023},
            time_period='last_30_days',
            aggregation_type='sum',
            group_by=['month'],
            order_by='month',
            limit=100,
            confidence=0.8,
            parsed_entities={'revenue': 'total_amount', 'region': 'sales_region'}
        )
    
    @pytest.fixture
    def sample_query_context(self):
        """Create sample query context."""
        return QueryContext(
            user_id='test_user',
            session_id='test_session',
            query_history=['previous query'],
            available_schemas=['test_db'],
            user_preferences={'default_limit': 1000},
            business_context='Sales analysis for Q4 2023'
        )
    
    def test_query_builder_initialization(self, query_builder):
        """Test query builder initialization."""
        assert query_builder.config['max_joins'] == 5
        assert query_builder.config['confidence_threshold'] == 0.6
        assert 'time_filters' in query_builder.common_patterns
        assert 'aggregation_templates' in query_builder.common_patterns
    
    def test_is_numeric_column(self, query_builder):
        """Test numeric column detection."""
        numeric_col = ColumnInfo(
            name="amount", data_type="decimal(10,2)", is_nullable=False,
            default_value=None, is_primary_key=False, is_foreign_key=False
        )
        assert query_builder._is_numeric_column(numeric_col)
        
        text_col = ColumnInfo(
            name="name", data_type="varchar(255)", is_nullable=True,
            default_value=None, is_primary_key=False, is_foreign_key=False
        )
        assert not query_builder._is_numeric_column(text_col)
    
    def test_is_dimension_column(self, query_builder):
        """Test dimension column detection."""
        dimension_col = ColumnInfo(
            name="category", data_type="varchar(100)", is_nullable=True,
            default_value=None, is_primary_key=False, is_foreign_key=False
        )
        assert query_builder._is_dimension_column(dimension_col)
        
        id_col = ColumnInfo(
            name="customer_id", data_type="int", is_nullable=False,
            default_value=None, is_primary_key=False, is_foreign_key=True
        )
        assert query_builder._is_dimension_column(id_col)  # Foreign keys are dimensions
    
    def test_build_filter_condition(self, query_builder):
        """Test filter condition building."""
        column = ColumnInfo(
            name="region", data_type="varchar(50)", is_nullable=True,
            default_value=None, is_primary_key=False, is_foreign_key=False
        )
        
        # Test simple equality
        condition = query_builder._build_filter_condition(column, 'north', 'sales')
        assert condition == "sales.region = 'north'"
        
        # Test IN clause
        condition = query_builder._build_filter_condition(column, ['north', 'south'], 'sales')
        assert "sales.region IN" in condition
        
        # Test range filter
        numeric_column = ColumnInfo(
            name="amount", data_type="decimal(10,2)", is_nullable=False,
            default_value=None, is_primary_key=False, is_foreign_key=False
        )
        condition = query_builder._build_filter_condition(
            numeric_column, {'min': 100, 'max': 1000}, 'orders'
        )
        assert "orders.amount >= 100" in condition
        assert "orders.amount <= 1000" in condition
    
    def test_calculate_confidence_score(self, query_builder):
        """Test query confidence score calculation."""
        similarity_scores = {
            'exact': 1.0,
            'fuzzy': 0.8,
            'semantic': 0.7,
            'concept': 0.9
        }
        context_relevance = 0.6
        
        confidence = query_builder._calculate_confidence_score(
            similarity_scores, context_relevance
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # Should be high given good similarity scores
    
    @pytest.mark.asyncio
    async def test_suggest_alternative_metrics(self, query_builder):
        """Test alternative metric suggestions."""
        suggestions = await query_builder._suggest_alternative_metrics('revenu')
        assert 'sales' in suggestions
        assert 'income' in suggestions


class TestSchemaChangeDetector:
    """Test suite for SchemaChangeDetector."""
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create mock schema manager."""
        manager = Mock()
        manager.discover_databases = AsyncMock(return_value=[
            DatabaseInfo(name="test_db", charset="utf8", collation="utf8_general_ci", accessible=True)
        ])
        manager.get_tables = AsyncMock(return_value=[])
        manager.get_table_schema = AsyncMock(return_value=None)
        return manager
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        cache = Mock()
        cache.invalidate_by_pattern = AsyncMock()
        return cache
    
    @pytest.fixture
    def change_detector(self, mock_schema_manager, mock_cache_manager):
        """Create change detector instance."""
        config = {
            'check_interval_seconds': 1,  # Fast for testing
            'enable_impact_analysis': True,
            'enable_migration_suggestions': True,
            'enable_cache_invalidation': True
        }
        return SchemaChangeDetector(
            schema_manager=mock_schema_manager,
            cache_manager=mock_cache_manager,
            config=config
        )
    
    @pytest.fixture
    def sample_table_schema_v1(self):
        """Create sample table schema version 1."""
        columns = [
            ColumnInfo(
                name="id", data_type="int", is_nullable=False,
                default_value=None, is_primary_key=True, is_foreign_key=False
            ),
            ColumnInfo(
                name="name", data_type="varchar(100)", is_nullable=False,
                default_value=None, is_primary_key=False, is_foreign_key=False
            )
        ]
        
        return TableSchema(
            database="test_db",
            table="users",
            columns=columns,
            indexes=[],
            primary_keys=["id"],
            foreign_keys=[],
            constraints=[]
        )
    
    @pytest.fixture
    def sample_table_schema_v2(self):
        """Create sample table schema version 2 (with changes)."""
        columns = [
            ColumnInfo(
                name="id", data_type="int", is_nullable=False,
                default_value=None, is_primary_key=True, is_foreign_key=False
            ),
            ColumnInfo(
                name="name", data_type="varchar(255)", is_nullable=False,  # Changed length
                default_value=None, is_primary_key=False, is_foreign_key=False
            ),
            ColumnInfo(  # New column
                name="email", data_type="varchar(255)", is_nullable=True,
                default_value=None, is_primary_key=False, is_foreign_key=False
            )
        ]
        
        return TableSchema(
            database="test_db",
            table="users",
            columns=columns,
            indexes=[],
            primary_keys=["id"],
            foreign_keys=[],
            constraints=[]
        )
    
    def test_initialize_severity_rules(self, change_detector):
        """Test severity rules initialization."""
        assert ChangeType.COMMENT_CHANGED in change_detector.severity_rules
        assert change_detector.severity_rules[ChangeType.COMMENT_CHANGED] == ChangeSeverity.LOW
        assert change_detector.severity_rules[ChangeType.TABLE_DROPPED] == ChangeSeverity.CRITICAL
    
    def test_calculate_schema_hash(self, change_detector, sample_table_schema_v1):
        """Test schema hash calculation."""
        table_schemas = {"users": sample_table_schema_v1}
        hash1 = change_detector._calculate_schema_hash(table_schemas)
        
        # Hash should be consistent
        hash2 = change_detector._calculate_schema_hash(table_schemas)
        assert hash1 == hash2
        
        # Hash should change when schema changes
        sample_table_schema_v1.columns[1].data_type = "varchar(200)"
        hash3 = change_detector._calculate_schema_hash(table_schemas)
        assert hash1 != hash3
    
    def test_detect_table_changes(self, change_detector):
        """Test table-level change detection."""
        old_tables = {"users", "orders"}
        new_tables = {"users", "products"}  # orders dropped, products added
        
        changes = change_detector._detect_table_changes(
            "test_db", old_tables, new_tables, {}, {}
        )
        
        assert len(changes) == 2
        change_types = [c.change_type for c in changes]
        assert ChangeType.TABLE_CREATED in change_types
        assert ChangeType.TABLE_DROPPED in change_types
    
    @pytest.mark.asyncio
    async def test_compare_table_schemas(self, change_detector, sample_table_schema_v1, sample_table_schema_v2):
        """Test table schema comparison."""
        changes = await change_detector._compare_table_schemas(
            sample_table_schema_v1, sample_table_schema_v2, "test_db"
        )
        
        assert len(changes) >= 2  # Should detect column addition and modification
        change_types = [c.change_type for c in changes]
        assert ChangeType.COLUMN_ADDED in change_types
        assert ChangeType.COLUMN_MODIFIED in change_types
    
    def test_compare_columns(self, change_detector, sample_table_schema_v1, sample_table_schema_v2):
        """Test column comparison."""
        changes = change_detector._compare_columns(
            sample_table_schema_v1, sample_table_schema_v2, "test_db"
        )
        
        assert len(changes) >= 2
        
        # Find the column addition change
        added_changes = [c for c in changes if c.change_type == ChangeType.COLUMN_ADDED]
        assert len(added_changes) == 1
        assert added_changes[0].element_name == "email"
        
        # Find the column modification change (name column data type change)
        modified_changes = [c for c in changes if c.change_type == ChangeType.COLUMN_MODIFIED]
        assert len(modified_changes) >= 1
    
    def test_determine_column_add_severity(self, change_detector):
        """Test column addition severity determination."""
        # Nullable column - low severity
        nullable_col = ColumnInfo(
            name="optional_field", data_type="varchar(100)", is_nullable=True,
            default_value=None, is_primary_key=False, is_foreign_key=False
        )
        severity = change_detector._determine_column_add_severity(nullable_col)
        assert severity == ChangeSeverity.LOW
        
        # Required column with default - low severity
        default_col = ColumnInfo(
            name="status", data_type="varchar(20)", is_nullable=False,
            default_value="active", is_primary_key=False, is_foreign_key=False
        )
        severity = change_detector._determine_column_add_severity(default_col)
        assert severity == ChangeSeverity.LOW
        
        # Required column without default - medium severity
        required_col = ColumnInfo(
            name="required_field", data_type="varchar(100)", is_nullable=False,
            default_value=None, is_primary_key=False, is_foreign_key=False
        )
        severity = change_detector._determine_column_add_severity(required_col)
        assert severity == ChangeSeverity.MEDIUM
    
    def test_determine_column_modification_severity(self, change_detector):
        """Test column modification severity determination."""
        old_col = ColumnInfo(
            name="status", data_type="varchar(20)", is_nullable=True,
            default_value="active", is_primary_key=False, is_foreign_key=False
        )
        
        # Making column non-nullable - high severity
        new_col_non_null = ColumnInfo(
            name="status", data_type="varchar(20)", is_nullable=False,
            default_value="active", is_primary_key=False, is_foreign_key=False
        )
        severity = change_detector._determine_column_modification_severity(old_col, new_col_non_null)
        assert severity == ChangeSeverity.HIGH
        
        # Removing default value - medium severity  
        new_col_no_default = ColumnInfo(
            name="status", data_type="varchar(20)", is_nullable=True,
            default_value=None, is_primary_key=False, is_foreign_key=False
        )
        severity = change_detector._determine_column_modification_severity(old_col, new_col_no_default)
        assert severity == ChangeSeverity.MEDIUM
    
    @pytest.mark.asyncio
    async def test_analyze_change_impact(self, change_detector):
        """Test change impact analysis."""
        change = SchemaChange(
            change_id="test_change",
            change_type=ChangeType.COLUMN_DROPPED,
            severity=ChangeSeverity.HIGH,
            database="test_db",
            table="users",
            element_name="old_column",
            old_definition={"name": "old_column", "data_type": "varchar(100)"},
            new_definition=None,
            detected_at=datetime.now()
        )
        
        impact = await change_detector._analyze_change_impact(change)
        
        assert 'breaking_change' in impact
        assert 'affected_tables' in impact
        assert 'cache_invalidation_required' in impact
        assert impact['breaking_change'] is True  # Column drop is breaking
    
    @pytest.mark.asyncio
    async def test_generate_migration_suggestions(self, change_detector):
        """Test migration suggestion generation."""
        change = SchemaChange(
            change_id="test_change",
            change_type=ChangeType.COLUMN_DROPPED,
            severity=ChangeSeverity.HIGH,
            database="test_db",
            table="users",
            element_name="old_column",
            old_definition={"name": "old_column"},
            new_definition=None,
            detected_at=datetime.now()
        )
        
        suggestions = await change_detector._generate_migration_suggestions(change)
        
        assert len(suggestions) > 0
        assert any("UPDATE SELECT statements" in s for s in suggestions)
        assert any("INSERT statements" in s for s in suggestions)
    
    def test_change_listener_management(self, change_detector):
        """Test change listener add/remove functionality."""
        def test_listener(change):
            pass
        
        # Add listener
        change_detector.add_change_listener(test_listener)
        assert test_listener in change_detector.change_listeners
        
        # Remove listener
        change_detector.remove_change_listener(test_listener)
        assert test_listener not in change_detector.change_listeners
    
    def test_get_change_history_filtering(self, change_detector):
        """Test change history filtering."""
        # Add some test changes
        change1 = SchemaChange(
            change_id="change1",
            change_type=ChangeType.COLUMN_ADDED,
            severity=ChangeSeverity.LOW,
            database="db1",
            table="table1",
            element_name="col1",
            old_definition=None,
            new_definition={},
            detected_at=datetime.now() - timedelta(hours=1)
        )
        
        change2 = SchemaChange(
            change_id="change2",
            change_type=ChangeType.TABLE_DROPPED,
            severity=ChangeSeverity.CRITICAL,
            database="db2",
            table="table2",
            element_name="table2",
            old_definition={},
            new_definition=None,
            detected_at=datetime.now()
        )
        
        change_detector.detected_changes = [change1, change2]
        
        # Test database filtering
        db1_changes = change_detector.get_change_history(database="db1")
        assert len(db1_changes) == 1
        assert db1_changes[0].database == "db1"
        
        # Test severity filtering
        critical_changes = change_detector.get_change_history(severity=ChangeSeverity.CRITICAL)
        assert len(critical_changes) == 1
        assert critical_changes[0].severity == ChangeSeverity.CRITICAL
        
        # Test time filtering
        recent_changes = change_detector.get_change_history(
            since=datetime.now() - timedelta(minutes=30)
        )
        assert len(recent_changes) == 1
        assert recent_changes[0].change_id == "change2"
        
        # Test limit
        limited_changes = change_detector.get_change_history(limit=1)
        assert len(limited_changes) == 1
    
    def test_get_change_statistics(self, change_detector):
        """Test change statistics generation."""
        # Add test changes
        changes = [
            SchemaChange(
                change_id=f"change{i}",
                change_type=ChangeType.COLUMN_ADDED if i % 2 == 0 else ChangeType.TABLE_DROPPED,
                severity=ChangeSeverity.LOW if i % 2 == 0 else ChangeSeverity.CRITICAL,
                database=f"db{i % 2}",
                table=f"table{i}",
                element_name=f"element{i}",
                old_definition=None,
                new_definition={},
                detected_at=datetime.now() - timedelta(hours=i)
            )
            for i in range(5)
        ]
        
        change_detector.detected_changes = changes
        
        stats = change_detector.get_change_statistics()
        
        assert stats['total_changes'] == 5
        assert 'by_type' in stats
        assert 'by_severity' in stats
        assert 'by_database' in stats
        assert 'recent_activity' in stats
        
        assert stats['by_type']['column_added'] >= 1
        assert stats['by_type']['table_dropped'] >= 1


# Integration tests
class TestPhase2Integration:
    """Integration tests for Phase 2 components working together."""
    
    @pytest.fixture
    def integration_setup(self):
        """Set up components for integration testing."""
        # This would set up real or more sophisticated mock components
        # for testing the interaction between SemanticMapper, QueryBuilder, and ChangeDetector
        pass
    
    @pytest.mark.asyncio
    async def test_semantic_mapping_to_query_building(self):
        """Test the flow from semantic mapping to query building."""
        # This test would verify that:
        # 1. SemanticMapper correctly maps business terms to schema elements
        # 2. QueryBuilder uses these mappings to generate SQL
        # 3. The generated SQL is valid and addresses the original intent
        pass
    
    @pytest.mark.asyncio
    async def test_schema_change_impact_on_mappings(self):
        """Test how schema changes affect semantic mappings."""
        # This test would verify that:
        # 1. SchemaChangeDetector detects schema changes
        # 2. Affected semantic mappings are invalidated
        # 3. Query building adapts to the new schema
        pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
