"""
Schema Change Detection System for real-time monitoring of database schema changes.

This module provides comprehensive schema change detection, impact analysis,
and automatic cache invalidation capabilities.
"""

import asyncio
import logging
import time
import hashlib
import json
from typing import List, Dict, Any, Optional, Set, Tuple, TYPE_CHECKING
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from .models import TableSchema, ColumnInfo, DatabaseInfo, TableInfo
from .enhanced_cache import EnhancedSchemaCache

if TYPE_CHECKING:
    from .manager import MCPSchemaManager

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Types of schema changes."""
    TABLE_CREATED = "table_created"
    TABLE_DROPPED = "table_dropped"
    TABLE_RENAMED = "table_renamed"
    COLUMN_ADDED = "column_added"
    COLUMN_DROPPED = "column_dropped"
    COLUMN_MODIFIED = "column_modified"
    COLUMN_RENAMED = "column_renamed"
    INDEX_ADDED = "index_added"
    INDEX_DROPPED = "index_dropped"
    CONSTRAINT_ADDED = "constraint_added"
    CONSTRAINT_DROPPED = "constraint_dropped"
    FOREIGN_KEY_ADDED = "foreign_key_added"
    FOREIGN_KEY_DROPPED = "foreign_key_dropped"
    DATA_TYPE_CHANGED = "data_type_changed"
    COMMENT_CHANGED = "comment_changed"


class ChangeSeverity(str, Enum):
    """Severity levels for schema changes."""
    LOW = "low"           # Non-breaking changes (comments, new optional columns)
    MEDIUM = "medium"     # Potentially breaking changes (new required columns, indexes)
    HIGH = "high"         # Breaking changes (dropped columns, data type changes)
    CRITICAL = "critical" # Critical breaking changes (dropped tables, foreign key changes)


@dataclass
class SchemaChange:
    """Represents a detected schema change."""
    change_id: str
    change_type: ChangeType
    severity: ChangeSeverity
    database: str
    table: Optional[str]
    element_name: str  # Table, column, index, or constraint name
    old_definition: Optional[Dict[str, Any]]
    new_definition: Optional[Dict[str, Any]]
    detected_at: datetime
    impact_analysis: Optional[Dict[str, Any]] = None
    migration_suggestions: Optional[List[str]] = None
    affected_queries: Optional[List[str]] = None


@dataclass
class ChangeImpact:
    """Analysis of change impact on the system."""
    breaking_change: bool
    affected_tables: List[str]
    affected_queries: List[str]
    cache_invalidation_required: Set[str]
    migration_required: bool
    rollback_possible: bool
    estimated_downtime_minutes: Optional[int]
    compatibility_issues: List[str]


@dataclass
class SchemaSnapshot:
    """Snapshot of database schema at a point in time."""
    snapshot_id: str
    database: str
    created_at: datetime
    schema_hash: str
    table_schemas: Dict[str, TableSchema]
    metadata: Dict[str, Any]


class SchemaChangeDetector:
    """
    Detects and analyzes database schema changes in real-time.
    
    Features:
    - Real-time schema monitoring
    - Change impact analysis
    - Automatic cache invalidation
    - Migration recommendations
    - Change audit logging
    - Notification system for agent synchronization
    """
    
    def __init__(
        self,
        schema_manager: "MCPSchemaManager",
        cache_manager: EnhancedSchemaCache,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize schema change detector.
        
        Args:
            schema_manager: Schema manager for database operations
            cache_manager: Cache manager for invalidation
            config: Optional configuration parameters
        """
        self.schema_manager = schema_manager
        self.cache_manager = cache_manager
        self.config = config or self._get_default_config()
        
        # Change tracking
        self.schema_snapshots: Dict[str, SchemaSnapshot] = {}
        self.detected_changes: List[SchemaChange] = []
        self.change_listeners: List[callable] = []
        
        # Monitoring state
        self.monitoring_enabled = False
        self.monitoring_task = None
        self.last_check_time = None
        
        # Change analysis
        self.severity_rules = self._initialize_severity_rules()
        self.impact_analyzers = self._initialize_impact_analyzers()
        
        logger.info("Initialized SchemaChangeDetector")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for change detection."""
        return {
            'check_interval_seconds': 60,  # How often to check for changes
            'enable_automatic_snapshots': True,
            'snapshot_retention_days': 30,
            'enable_impact_analysis': True,
            'enable_migration_suggestions': True,
            'enable_cache_invalidation': True,
            'notification_batch_size': 10,
            'max_stored_changes': 1000,
            'enable_trigger_based_detection': False,  # Requires database triggers
            'change_history_retention_days': 90
        }
    
    def _initialize_severity_rules(self) -> Dict[ChangeType, ChangeSeverity]:
        """Initialize rules for determining change severity."""
        return {
            # Low severity - Non-breaking changes
            ChangeType.COMMENT_CHANGED: ChangeSeverity.LOW,
            ChangeType.INDEX_ADDED: ChangeSeverity.LOW,
            
            # Medium severity - Potentially breaking
            ChangeType.COLUMN_ADDED: ChangeSeverity.MEDIUM,
            ChangeType.CONSTRAINT_ADDED: ChangeSeverity.MEDIUM,
            ChangeType.TABLE_CREATED: ChangeSeverity.MEDIUM,
            
            # High severity - Breaking changes
            ChangeType.COLUMN_DROPPED: ChangeSeverity.HIGH,
            ChangeType.COLUMN_MODIFIED: ChangeSeverity.HIGH,
            ChangeType.DATA_TYPE_CHANGED: ChangeSeverity.HIGH,
            ChangeType.INDEX_DROPPED: ChangeSeverity.HIGH,
            ChangeType.CONSTRAINT_DROPPED: ChangeSeverity.HIGH,
            
            # Critical severity - Major breaking changes
            ChangeType.TABLE_DROPPED: ChangeSeverity.CRITICAL,
            ChangeType.TABLE_RENAMED: ChangeSeverity.CRITICAL,
            ChangeType.FOREIGN_KEY_DROPPED: ChangeSeverity.CRITICAL,
            ChangeType.COLUMN_RENAMED: ChangeSeverity.CRITICAL
        }
    
    def _initialize_impact_analyzers(self) -> Dict[ChangeType, callable]:
        """Initialize impact analyzers for different change types."""
        return {
            ChangeType.TABLE_DROPPED: self._analyze_table_drop_impact,
            ChangeType.COLUMN_DROPPED: self._analyze_column_drop_impact,
            ChangeType.DATA_TYPE_CHANGED: self._analyze_data_type_change_impact,
            ChangeType.FOREIGN_KEY_DROPPED: self._analyze_foreign_key_drop_impact,
            ChangeType.TABLE_RENAMED: self._analyze_table_rename_impact,
            ChangeType.COLUMN_RENAMED: self._analyze_column_rename_impact
        }
    
    async def start_monitoring(self):
        """Start real-time schema change monitoring."""
        if self.monitoring_enabled:
            logger.warning("Schema change monitoring is already running")
            return
        
        self.monitoring_enabled = True
        self.last_check_time = datetime.now()
        
        # Create initial snapshots for all databases
        await self._create_initial_snapshots()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Started schema change monitoring")
    
    async def stop_monitoring(self):
        """Stop schema change monitoring."""
        if not self.monitoring_enabled:
            return
        
        self.monitoring_enabled = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped schema change monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for detecting schema changes."""
        logger.info("Schema change monitoring loop started")
        
        while self.monitoring_enabled:
            try:
                await self._check_for_changes()
                
                # Wait for next check
                await asyncio.sleep(self.config['check_interval_seconds'])
                
            except asyncio.CancelledError:
                logger.info("Schema change monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in schema change monitoring loop: {e}")
                # Wait before retrying to avoid rapid error loops
                await asyncio.sleep(60)
    
    async def _create_initial_snapshots(self):
        """Create initial schema snapshots for all databases."""
        try:
            databases = await self.schema_manager.discover_databases()
            
            for database in databases:
                if database.accessible:
                    await self._create_schema_snapshot(database.name)
            
            logger.info(f"Created initial snapshots for {len(databases)} databases")
            
        except Exception as e:
            logger.error(f"Failed to create initial snapshots: {e}")
    
    async def _create_schema_snapshot(self, database: str) -> SchemaSnapshot:
        """
        Create a schema snapshot for a database.
        
        Args:
            database: Database name
            
        Returns:
            Schema snapshot
        """
        # Get all tables in the database
        tables = await self.schema_manager.get_tables(database)
        table_schemas = {}
        
        # Get detailed schema for each table
        for table in tables:
            table_schema = await self.schema_manager.get_table_schema(database, table.name)
            if table_schema:
                table_schemas[table.name] = table_schema
        
        # Calculate schema hash for change detection
        schema_hash = self._calculate_schema_hash(table_schemas)
        
        snapshot = SchemaSnapshot(
            snapshot_id=f"{database}_{int(time.time())}",
            database=database,
            created_at=datetime.now(),
            schema_hash=schema_hash,
            table_schemas=table_schemas,
            metadata={
                'table_count': len(table_schemas),
                'total_columns': sum(len(schema.columns) for schema in table_schemas.values()),
                'total_indexes': sum(len(schema.indexes) for schema in table_schemas.values())
            }
        )
        
        # Store snapshot
        self.schema_snapshots[database] = snapshot
        
        logger.debug(f"Created schema snapshot for database {database} "
                    f"with {len(table_schemas)} tables")
        
        return snapshot
    
    def _calculate_schema_hash(self, table_schemas: Dict[str, TableSchema]) -> str:
        """
        Calculate a hash representing the current schema state.
        
        Args:
            table_schemas: Dictionary of table schemas
            
        Returns:
            SHA-256 hash of the schema
        """
        # Create a normalized representation of the schema
        schema_data = {}
        
        for table_name, schema in sorted(table_schemas.items()):
            table_data = {
                'table': table_name,
                'columns': [
                    {
                        'name': col.name,
                        'data_type': col.data_type,
                        'is_nullable': col.is_nullable,
                        'default_value': col.default_value,
                        'is_primary_key': col.is_primary_key,
                        'is_foreign_key': col.is_foreign_key
                    }
                    for col in sorted(schema.columns, key=lambda c: c.name)
                ],
                'indexes': [
                    {
                        'name': idx.name,
                        'columns': sorted(idx.columns),
                        'is_unique': idx.is_unique,
                        'is_primary': idx.is_primary
                    }
                    for idx in sorted(schema.indexes, key=lambda i: i.name)
                ],
                'foreign_keys': [
                    {
                        'name': fk.name,
                        'column': fk.column,
                        'referenced_table': fk.referenced_table,
                        'referenced_column': fk.referenced_column
                    }
                    for fk in sorted(schema.foreign_keys, key=lambda f: f.name)
                ]
            }
            schema_data[table_name] = table_data
        
        # Convert to JSON and hash
        schema_json = json.dumps(schema_data, sort_keys=True)
        return hashlib.sha256(schema_json.encode()).hexdigest()
    
    async def _check_for_changes(self):
        """Check for schema changes since last check."""
        current_time = datetime.now()
        
        try:
            databases = await self.schema_manager.discover_databases()
            changes = []
            
            for database in databases:
                if database.accessible:
                    database_changes = await self._check_database_changes(database.name)
                    changes.extend(database_changes)
            
            # Process detected changes
            if changes:
                await self._process_detected_changes(changes)
            
            self.last_check_time = current_time
            
        except Exception as e:
            logger.error(f"Failed to check for schema changes: {e}")
    
    async def _check_database_changes(self, database: str) -> List[SchemaChange]:
        """
        Check for changes in a specific database.
        
        Args:
            database: Database name
            
        Returns:
            List of detected changes
        """
        # Get current schema snapshot
        current_snapshot = await self._create_schema_snapshot(database)
        
        # Compare with previous snapshot
        previous_snapshot = self.schema_snapshots.get(database)
        
        if not previous_snapshot:
            # First time seeing this database - no changes to report
            return []
        
        # Quick hash comparison
        if current_snapshot.schema_hash == previous_snapshot.schema_hash:
            # No changes detected
            return []
        
        logger.info(f"Schema changes detected in database {database}")
        
        # Detailed comparison to identify specific changes
        changes = await self._compare_snapshots(previous_snapshot, current_snapshot)
        
        # Update stored snapshot
        self.schema_snapshots[database] = current_snapshot
        
        return changes
    
    async def _compare_snapshots(
        self,
        old_snapshot: SchemaSnapshot,
        new_snapshot: SchemaSnapshot
    ) -> List[SchemaChange]:
        """
        Compare two schema snapshots to identify changes.
        
        Args:
            old_snapshot: Previous schema snapshot
            new_snapshot: Current schema snapshot
            
        Returns:
            List of detected changes
        """
        changes = []
        
        old_tables = set(old_snapshot.table_schemas.keys())
        new_tables = set(new_snapshot.table_schemas.keys())
        
        # Detect table-level changes
        changes.extend(self._detect_table_changes(
            old_snapshot.database, old_tables, new_tables,
            old_snapshot.table_schemas, new_snapshot.table_schemas
        ))
        
        # Detect changes in existing tables
        common_tables = old_tables & new_tables
        for table_name in common_tables:
            old_schema = old_snapshot.table_schemas[table_name]
            new_schema = new_snapshot.table_schemas[table_name]
            
            table_changes = await self._compare_table_schemas(
                old_schema, new_schema, new_snapshot.database
            )
            changes.extend(table_changes)
        
        return changes
    
    def _detect_table_changes(
        self,
        database: str,
        old_tables: Set[str],
        new_tables: Set[str],
        old_schemas: Dict[str, TableSchema],
        new_schemas: Dict[str, TableSchema]
    ) -> List[SchemaChange]:
        """Detect table-level changes (created, dropped, renamed)."""
        changes = []
        
        # Tables created
        created_tables = new_tables - old_tables
        for table in created_tables:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.TABLE_CREATED,
                severity=self.severity_rules[ChangeType.TABLE_CREATED],
                database=database,
                table=table,
                element_name=table,
                old_definition=None,
                new_definition=asdict(new_schemas[table]),
                detected_at=datetime.now()
            )
            changes.append(change)
        
        # Tables dropped
        dropped_tables = old_tables - new_tables
        for table in dropped_tables:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.TABLE_DROPPED,
                severity=self.severity_rules[ChangeType.TABLE_DROPPED],
                database=database,
                table=table,
                element_name=table,
                old_definition=asdict(old_schemas[table]),
                new_definition=None,
                detected_at=datetime.now()
            )
            changes.append(change)
        
        # Note: Table renames are difficult to detect automatically
        # They appear as a drop + create. Advanced detection would require
        # analyzing table structure similarity.
        
        return changes
    
    async def _compare_table_schemas(
        self,
        old_schema: TableSchema,
        new_schema: TableSchema,
        database: str
    ) -> List[SchemaChange]:
        """Compare two table schemas to detect changes."""
        changes = []
        
        # Compare columns
        changes.extend(self._compare_columns(old_schema, new_schema, database))
        
        # Compare indexes
        changes.extend(self._compare_indexes(old_schema, new_schema, database))
        
        # Compare foreign keys
        changes.extend(self._compare_foreign_keys(old_schema, new_schema, database))
        
        # Compare constraints
        changes.extend(self._compare_constraints(old_schema, new_schema, database))
        
        # Compare table-level properties
        if old_schema.table_info and new_schema.table_info:
            if old_schema.table_info.comment != new_schema.table_info.comment:
                change = SchemaChange(
                    change_id=self._generate_change_id(),
                    change_type=ChangeType.COMMENT_CHANGED,
                    severity=self.severity_rules[ChangeType.COMMENT_CHANGED],
                    database=database,
                    table=new_schema.table,
                    element_name=f"{new_schema.table}.comment",
                    old_definition={'comment': old_schema.table_info.comment},
                    new_definition={'comment': new_schema.table_info.comment},
                    detected_at=datetime.now()
                )
                changes.append(change)
        
        return changes
    
    def _compare_columns(
        self,
        old_schema: TableSchema,
        new_schema: TableSchema,
        database: str
    ) -> List[SchemaChange]:
        """Compare column definitions between schemas."""
        changes = []
        
        old_columns = {col.name: col for col in old_schema.columns}
        new_columns = {col.name: col for col in new_schema.columns}
        
        old_col_names = set(old_columns.keys())
        new_col_names = set(new_columns.keys())
        
        # Columns added
        added_columns = new_col_names - old_col_names
        for col_name in added_columns:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.COLUMN_ADDED,
                severity=self._determine_column_add_severity(new_columns[col_name]),
                database=database,
                table=new_schema.table,
                element_name=col_name,
                old_definition=None,
                new_definition=asdict(new_columns[col_name]),
                detected_at=datetime.now()
            )
            changes.append(change)
        
        # Columns dropped
        dropped_columns = old_col_names - new_col_names
        for col_name in dropped_columns:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.COLUMN_DROPPED,
                severity=self.severity_rules[ChangeType.COLUMN_DROPPED],
                database=database,
                table=new_schema.table,
                element_name=col_name,
                old_definition=asdict(old_columns[col_name]),
                new_definition=None,
                detected_at=datetime.now()
            )
            changes.append(change)
        
        # Modified columns
        common_columns = old_col_names & new_col_names
        for col_name in common_columns:
            old_col = old_columns[col_name]
            new_col = new_columns[col_name]
            
            # Check for data type changes
            if old_col.data_type != new_col.data_type:
                change = SchemaChange(
                    change_id=self._generate_change_id(),
                    change_type=ChangeType.DATA_TYPE_CHANGED,
                    severity=self.severity_rules[ChangeType.DATA_TYPE_CHANGED],
                    database=database,
                    table=new_schema.table,
                    element_name=col_name,
                    old_definition={'data_type': old_col.data_type},
                    new_definition={'data_type': new_col.data_type},
                    detected_at=datetime.now()
                )
                changes.append(change)
            
            # Check for other column property changes
            if (old_col.is_nullable != new_col.is_nullable or
                old_col.default_value != new_col.default_value or
                old_col.is_primary_key != new_col.is_primary_key):
                
                change = SchemaChange(
                    change_id=self._generate_change_id(),
                    change_type=ChangeType.COLUMN_MODIFIED,
                    severity=self._determine_column_modification_severity(old_col, new_col),
                    database=database,
                    table=new_schema.table,
                    element_name=col_name,
                    old_definition=asdict(old_col),
                    new_definition=asdict(new_col),
                    detected_at=datetime.now()
                )
                changes.append(change)
            
            # Check for comment changes
            if old_col.comment != new_col.comment:
                change = SchemaChange(
                    change_id=self._generate_change_id(),
                    change_type=ChangeType.COMMENT_CHANGED,
                    severity=self.severity_rules[ChangeType.COMMENT_CHANGED],
                    database=database,
                    table=new_schema.table,
                    element_name=f"{col_name}.comment",
                    old_definition={'comment': old_col.comment},
                    new_definition={'comment': new_col.comment},
                    detected_at=datetime.now()
                )
                changes.append(change)
        
        return changes
    
    def _compare_indexes(
        self,
        old_schema: TableSchema,
        new_schema: TableSchema,
        database: str
    ) -> List[SchemaChange]:
        """Compare index definitions between schemas."""
        changes = []
        
        old_indexes = {idx.name: idx for idx in old_schema.indexes}
        new_indexes = {idx.name: idx for idx in new_schema.indexes}
        
        old_idx_names = set(old_indexes.keys())
        new_idx_names = set(new_indexes.keys())
        
        # Indexes added
        added_indexes = new_idx_names - old_idx_names
        for idx_name in added_indexes:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.INDEX_ADDED,
                severity=self.severity_rules[ChangeType.INDEX_ADDED],
                database=database,
                table=new_schema.table,
                element_name=idx_name,
                old_definition=None,
                new_definition=asdict(new_indexes[idx_name]),
                detected_at=datetime.now()
            )
            changes.append(change)
        
        # Indexes dropped
        dropped_indexes = old_idx_names - new_idx_names
        for idx_name in dropped_indexes:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.INDEX_DROPPED,
                severity=self.severity_rules[ChangeType.INDEX_DROPPED],
                database=database,
                table=new_schema.table,
                element_name=idx_name,
                old_definition=asdict(old_indexes[idx_name]),
                new_definition=None,
                detected_at=datetime.now()
            )
            changes.append(change)
        
        return changes
    
    def _compare_foreign_keys(
        self,
        old_schema: TableSchema,
        new_schema: TableSchema,
        database: str
    ) -> List[SchemaChange]:
        """Compare foreign key definitions between schemas."""
        changes = []
        
        old_fks = {fk.name: fk for fk in old_schema.foreign_keys}
        new_fks = {fk.name: fk for fk in new_schema.foreign_keys}
        
        old_fk_names = set(old_fks.keys())
        new_fk_names = set(new_fks.keys())
        
        # Foreign keys added
        added_fks = new_fk_names - old_fk_names
        for fk_name in added_fks:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.FOREIGN_KEY_ADDED,
                severity=ChangeSeverity.MEDIUM,
                database=database,
                table=new_schema.table,
                element_name=fk_name,
                old_definition=None,
                new_definition=asdict(new_fks[fk_name]),
                detected_at=datetime.now()
            )
            changes.append(change)
        
        # Foreign keys dropped
        dropped_fks = old_fk_names - new_fk_names
        for fk_name in dropped_fks:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.FOREIGN_KEY_DROPPED,
                severity=self.severity_rules[ChangeType.FOREIGN_KEY_DROPPED],
                database=database,
                table=new_schema.table,
                element_name=fk_name,
                old_definition=asdict(old_fks[fk_name]),
                new_definition=None,
                detected_at=datetime.now()
            )
            changes.append(change)
        
        return changes
    
    def _compare_constraints(
        self,
        old_schema: TableSchema,
        new_schema: TableSchema,
        database: str
    ) -> List[SchemaChange]:
        """Compare constraint definitions between schemas."""
        changes = []
        
        old_constraints = {const.name: const for const in old_schema.constraints}
        new_constraints = {const.name: const for const in new_schema.constraints}
        
        old_const_names = set(old_constraints.keys())
        new_const_names = set(new_constraints.keys())
        
        # Constraints added
        added_constraints = new_const_names - old_const_names
        for const_name in added_constraints:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.CONSTRAINT_ADDED,
                severity=self.severity_rules[ChangeType.CONSTRAINT_ADDED],
                database=database,
                table=new_schema.table,
                element_name=const_name,
                old_definition=None,
                new_definition=asdict(new_constraints[const_name]),
                detected_at=datetime.now()
            )
            changes.append(change)
        
        # Constraints dropped
        dropped_constraints = old_const_names - new_const_names
        for const_name in dropped_constraints:
            change = SchemaChange(
                change_id=self._generate_change_id(),
                change_type=ChangeType.CONSTRAINT_DROPPED,
                severity=self.severity_rules[ChangeType.CONSTRAINT_DROPPED],
                database=database,
                table=new_schema.table,
                element_name=const_name,
                old_definition=asdict(old_constraints[const_name]),
                new_definition=None,
                detected_at=datetime.now()
            )
            changes.append(change)
        
        return changes
    
    def _determine_column_add_severity(self, column: ColumnInfo) -> ChangeSeverity:
        """Determine severity of a column addition."""
        if column.is_nullable or column.default_value is not None:
            return ChangeSeverity.LOW  # Safe addition
        else:
            return ChangeSeverity.MEDIUM  # Requires default value for existing rows
    
    def _determine_column_modification_severity(
        self,
        old_column: ColumnInfo,
        new_column: ColumnInfo
    ) -> ChangeSeverity:
        """Determine severity of a column modification."""
        # Making column non-nullable is breaking
        if old_column.is_nullable and not new_column.is_nullable:
            return ChangeSeverity.HIGH
        
        # Removing default value can be breaking
        if old_column.default_value is not None and new_column.default_value is None:
            return ChangeSeverity.MEDIUM
        
        # Primary key changes are critical
        if old_column.is_primary_key != new_column.is_primary_key:
            return ChangeSeverity.CRITICAL
        
        return ChangeSeverity.LOW
    
    def _generate_change_id(self) -> str:
        """Generate unique change ID."""
        return f"change_{int(time.time() * 1000)}_{id(object())}"
    
    async def _process_detected_changes(self, changes: List[SchemaChange]):
        """Process and analyze detected schema changes."""
        logger.info(f"Processing {len(changes)} detected schema changes")
        
        for change in changes:
            # Perform impact analysis
            if self.config['enable_impact_analysis']:
                change.impact_analysis = await self._analyze_change_impact(change)
            
            # Generate migration suggestions
            if self.config['enable_migration_suggestions']:
                change.migration_suggestions = await self._generate_migration_suggestions(change)
            
            # Store the change
            self.detected_changes.append(change)
            
            # Perform cache invalidation
            if self.config['enable_cache_invalidation']:
                await self._invalidate_affected_caches(change)
            
            # Notify listeners
            await self._notify_change_listeners(change)
        
        # Cleanup old changes if we have too many
        await self._cleanup_old_changes()
    
    async def _analyze_change_impact(self, change: SchemaChange) -> Dict[str, Any]:
        """
        Analyze the impact of a schema change.
        
        Args:
            change: Schema change to analyze
            
        Returns:
            Impact analysis results
        """
        if change.change_type in self.impact_analyzers:
            analyzer = self.impact_analyzers[change.change_type]
            return await analyzer(change)
        else:
            # Default impact analysis
            return await self._default_impact_analysis(change)
    
    async def _default_impact_analysis(self, change: SchemaChange) -> Dict[str, Any]:
        """Default impact analysis for changes without specific analyzers."""
        return {
            'breaking_change': change.severity in [ChangeSeverity.HIGH, ChangeSeverity.CRITICAL],
            'affected_tables': [change.table] if change.table else [],
            'cache_invalidation_required': [f"{change.database}.*"],
            'migration_required': change.severity in [ChangeSeverity.HIGH, ChangeSeverity.CRITICAL],
            'estimated_downtime_minutes': 0 if change.severity == ChangeSeverity.LOW else 5,
            'compatibility_issues': []
        }
    
    async def _analyze_table_drop_impact(self, change: SchemaChange) -> Dict[str, Any]:
        """Analyze impact of table drop."""
        affected_tables = [change.table]
        
        # Find tables that reference this table via foreign keys
        try:
            databases = await self.schema_manager.discover_databases()
            for db in databases:
                if db.accessible:
                    tables = await self.schema_manager.get_tables(db.name)
                    for table in tables:
                        schema = await self.schema_manager.get_table_schema(db.name, table.name)
                        if schema:
                            for fk in schema.foreign_keys:
                                if fk.referenced_table == change.table:
                                    affected_tables.append(f"{db.name}.{table.name}")
        except Exception as e:
            logger.error(f"Failed to analyze table drop impact: {e}")
        
        return {
            'breaking_change': True,
            'affected_tables': affected_tables,
            'cache_invalidation_required': [f"{change.database}.*"],
            'migration_required': True,
            'estimated_downtime_minutes': 15,
            'compatibility_issues': [
                'All queries referencing this table will fail',
                'Foreign key constraints may prevent dependent operations'
            ]
        }
    
    async def _analyze_column_drop_impact(self, change: SchemaChange) -> Dict[str, Any]:
        """Analyze impact of column drop."""
        return {
            'breaking_change': True,
            'affected_tables': [change.table],
            'cache_invalidation_required': [f"{change.database}.{change.table}.*"],
            'migration_required': True,
            'estimated_downtime_minutes': 5,
            'compatibility_issues': [
                f'Queries selecting {change.element_name} will fail',
                f'Applications using {change.element_name} column need updates'
            ]
        }
    
    async def _analyze_data_type_change_impact(self, change: SchemaChange) -> Dict[str, Any]:
        """Analyze impact of data type change."""
        old_type = change.old_definition.get('data_type', '') if change.old_definition else ''
        new_type = change.new_definition.get('data_type', '') if change.new_definition else ''
        
        compatibility_issues = []
        migration_required = False
        
        # Check for potentially breaking type changes
        if 'varchar' in old_type.lower() and 'int' in new_type.lower():
            compatibility_issues.append('String to integer conversion may cause data loss')
            migration_required = True
        elif 'int' in old_type.lower() and 'varchar' in new_type.lower():
            compatibility_issues.append('Integer to string conversion changes query behavior')
        
        return {
            'breaking_change': len(compatibility_issues) > 0,
            'affected_tables': [change.table],
            'cache_invalidation_required': [f"{change.database}.{change.table}.{change.element_name}"],
            'migration_required': migration_required,
            'estimated_downtime_minutes': 2 if migration_required else 0,
            'compatibility_issues': compatibility_issues
        }
    
    async def _analyze_foreign_key_drop_impact(self, change: SchemaChange) -> Dict[str, Any]:
        """Analyze impact of foreign key drop."""
        return {
            'breaking_change': True,
            'affected_tables': [change.table],
            'cache_invalidation_required': [f"{change.database}.{change.table}.*"],
            'migration_required': False,
            'estimated_downtime_minutes': 0,
            'compatibility_issues': [
                'Referential integrity is no longer enforced',
                'Join queries may return different results'
            ]
        }
    
    async def _analyze_table_rename_impact(self, change: SchemaChange) -> Dict[str, Any]:
        """Analyze impact of table rename."""
        return {
            'breaking_change': True,
            'affected_tables': [change.element_name],  # Old table name
            'cache_invalidation_required': [f"{change.database}.*"],
            'migration_required': True,
            'estimated_downtime_minutes': 10,
            'compatibility_issues': [
                'All queries referencing old table name will fail',
                'Applications need configuration updates'
            ]
        }
    
    async def _analyze_column_rename_impact(self, change: SchemaChange) -> Dict[str, Any]:
        """Analyze impact of column rename."""
        return {
            'breaking_change': True,
            'affected_tables': [change.table],
            'cache_invalidation_required': [f"{change.database}.{change.table}.*"],
            'migration_required': True,
            'estimated_downtime_minutes': 5,
            'compatibility_issues': [
                f'Queries referencing old column name {change.element_name} will fail',
                'Applications need to be updated with new column name'
            ]
        }
    
    async def _generate_migration_suggestions(self, change: SchemaChange) -> List[str]:
        """
        Generate migration suggestions for a schema change.
        
        Args:
            change: Schema change
            
        Returns:
            List of migration suggestions
        """
        suggestions = []
        
        if change.change_type == ChangeType.TABLE_DROPPED:
            suggestions.extend([
                f"Backup data from {change.table} before proceeding",
                f"Update applications to remove references to {change.table}",
                "Check for dependent foreign key constraints",
                "Consider creating a view as temporary compatibility layer"
            ])
        
        elif change.change_type == ChangeType.COLUMN_DROPPED:
            suggestions.extend([
                f"Update SELECT statements to remove {change.element_name}",
                f"Modify INSERT statements to exclude {change.element_name}",
                "Check for applications using this column",
                "Consider adding a computed column if logic needs to be preserved"
            ])
        
        elif change.change_type == ChangeType.DATA_TYPE_CHANGED:
            suggestions.extend([
                f"Test data conversion from old to new type",
                f"Update application data types for {change.element_name}",
                "Check for potential data loss in conversion",
                "Update validation logic if needed"
            ])
        
        elif change.change_type == ChangeType.COLUMN_ADDED:
            if change.new_definition and not change.new_definition.get('is_nullable', True):
                suggestions.extend([
                    f"Provide default value for new column {change.element_name}",
                    "Update INSERT statements to include new column",
                    "Consider making column nullable initially"
                ])
        
        elif change.change_type == ChangeType.TABLE_RENAMED:
            suggestions.extend([
                f"Create view with old table name for backward compatibility",
                "Update all application references to use new table name",
                "Update foreign key references in other tables",
                "Consider gradual migration approach"
            ])
        
        return suggestions
    
    async def _invalidate_affected_caches(self, change: SchemaChange):
        """
        Invalidate caches affected by a schema change.
        
        Args:
            change: Schema change
        """
        try:
            if change.impact_analysis:
                cache_patterns = change.impact_analysis.get('cache_invalidation_required', [])
            else:
                # Default cache invalidation patterns
                cache_patterns = [f"{change.database}.*"]
                if change.table:
                    cache_patterns.append(f"{change.database}.{change.table}.*")
            
            for pattern in cache_patterns:
                await self.cache_manager.invalidate_by_pattern(pattern)
                logger.info(f"Invalidated cache pattern: {pattern}")
        
        except Exception as e:
            logger.error(f"Failed to invalidate affected caches: {e}")
    
    async def _notify_change_listeners(self, change: SchemaChange):
        """
        Notify registered change listeners about a schema change.
        
        Args:
            change: Schema change
        """
        for listener in self.change_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(change)
                else:
                    listener(change)
            except Exception as e:
                logger.error(f"Error notifying change listener: {e}")
    
    def add_change_listener(self, listener: callable):
        """
        Add a change listener function.
        
        Args:
            listener: Function to call when changes are detected
        """
        self.change_listeners.append(listener)
        logger.debug(f"Added change listener: {listener.__name__}")
    
    def remove_change_listener(self, listener: callable):
        """
        Remove a change listener function.
        
        Args:
            listener: Function to remove from listeners
        """
        if listener in self.change_listeners:
            self.change_listeners.remove(listener)
            logger.debug(f"Removed change listener: {listener.__name__}")
    
    async def _cleanup_old_changes(self):
        """Clean up old change records to prevent memory bloat."""
        max_changes = self.config['max_stored_changes']
        
        if len(self.detected_changes) > max_changes:
            # Keep the most recent changes
            self.detected_changes = sorted(
                self.detected_changes,
                key=lambda c: c.detected_at,
                reverse=True
            )[:max_changes]
            
            logger.debug(f"Cleaned up old change records, keeping {max_changes} most recent")
    
    def get_change_history(
        self,
        database: Optional[str] = None,
        table: Optional[str] = None,
        change_type: Optional[ChangeType] = None,
        severity: Optional[ChangeSeverity] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[SchemaChange]:
        """
        Get filtered change history.
        
        Args:
            database: Filter by database name
            table: Filter by table name
            change_type: Filter by change type
            severity: Filter by severity level
            since: Filter by changes since this datetime
            limit: Maximum number of changes to return
            
        Returns:
            Filtered list of schema changes
        """
        filtered_changes = self.detected_changes
        
        # Apply filters
        if database:
            filtered_changes = [c for c in filtered_changes if c.database == database]
        
        if table:
            filtered_changes = [c for c in filtered_changes if c.table == table]
        
        if change_type:
            filtered_changes = [c for c in filtered_changes if c.change_type == change_type]
        
        if severity:
            filtered_changes = [c for c in filtered_changes if c.severity == severity]
        
        if since:
            filtered_changes = [c for c in filtered_changes if c.detected_at >= since]
        
        # Sort by detection time (most recent first)
        filtered_changes.sort(key=lambda c: c.detected_at, reverse=True)
        
        # Apply limit
        if limit:
            filtered_changes = filtered_changes[:limit]
        
        return filtered_changes
    
    def get_change_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about detected schema changes.
        
        Returns:
            Dictionary with change statistics
        """
        if not self.detected_changes:
            return {
                'total_changes': 0,
                'by_type': {},
                'by_severity': {},
                'by_database': {},
                'recent_activity': {}
            }
        
        # Count by type
        by_type = defaultdict(int)
        for change in self.detected_changes:
            by_type[change.change_type.value] += 1
        
        # Count by severity
        by_severity = defaultdict(int)
        for change in self.detected_changes:
            by_severity[change.severity.value] += 1
        
        # Count by database
        by_database = defaultdict(int)
        for change in self.detected_changes:
            by_database[change.database] += 1
        
        # Recent activity (last 24 hours)
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        recent_changes = [c for c in self.detected_changes if c.detected_at >= recent_cutoff]
        
        return {
            'total_changes': len(self.detected_changes),
            'by_type': dict(by_type),
            'by_severity': dict(by_severity),
            'by_database': dict(by_database),
            'recent_activity': {
                'last_24_hours': len(recent_changes),
                'monitoring_enabled': self.monitoring_enabled,
                'last_check': self.last_check_time.isoformat() if self.last_check_time else None
            }
        }
    
    async def force_schema_check(self) -> List[SchemaChange]:
        """
        Force an immediate schema check for changes.
        
        Returns:
            List of detected changes
        """
        logger.info("Forcing immediate schema change check")
        
        changes = []
        try:
            databases = await self.schema_manager.discover_databases()
            
            for database in databases:
                if database.accessible:
                    database_changes = await self._check_database_changes(database.name)
                    changes.extend(database_changes)
            
            if changes:
                await self._process_detected_changes(changes)
            
            logger.info(f"Force check completed, found {len(changes)} changes")
            
        except Exception as e:
            logger.error(f"Force schema check failed: {e}")
        
        return changes
