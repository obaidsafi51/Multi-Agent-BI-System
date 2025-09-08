"""
Dynamic data validation system using real-time schema information from MCP server.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, InvalidOperation
from datetime import datetime
from dataclasses import dataclass

from .manager import MCPSchemaManager
from .models import (
    ValidationResult, ValidationError, ValidationWarning, ValidationSeverity,
    TableSchema, ColumnInfo
)

logger = logging.getLogger(__name__)


@dataclass
class DynamicValidationConfig:
    """Configuration for dynamic validation behavior."""
    strict_mode: bool = False
    validate_types: bool = True
    validate_constraints: bool = True
    validate_relationships: bool = True
    allow_unknown_columns: bool = False
    fallback_to_static: bool = True
    max_validation_time_ms: int = 5000


class DynamicValidator:
    """Simple dynamic validator for testing purposes."""
    
    def __init__(self, client):
        """Initialize dynamic validator."""
        from .manager import SchemaCacheManager
        self._cache = SchemaCacheManager(client)
        self.client = client
    
    def validate(self, data: Dict[str, Any]):
        """Validate data and return validation result object."""
        from .models import ValidationResult, ValidationError, ValidationSeverity
        
        try:
            schema = self._cache.get_schema()
            
            # Basic validation - check if data has required fields
            errors = []
            if not isinstance(data, dict):
                errors.append(ValidationError(
                    field="data",
                    message="Data must be a dictionary",
                    severity=ValidationSeverity.ERROR,
                    error_code="INVALID_TYPE"
                ))
            
            # Check for empty data
            if not data:
                errors.append(ValidationError(
                    field="data",
                    message="Data cannot be empty",
                    severity=ValidationSeverity.ERROR,
                    error_code="EMPTY_DATA"
                ))
            
            # Simple type validation - look for string values where we expect numbers
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            # If the field name suggests it should be numeric but it's a string
                            if sub_key == "id" and isinstance(sub_value, str) and not sub_value.isdigit():
                                errors.append(ValidationError(
                                    field=f"{key}.{sub_key}",
                                    message=f"Expected numeric value for id, got string: {sub_value}",
                                    severity=ValidationSeverity.ERROR,
                                    error_code="INVALID_TYPE"
                                ))
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=[],
                validated_fields=list(data.keys()) if isinstance(data, dict) else [],
                validation_time_ms=1
            )
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="validation_system",
                    message=f"Validation error: {str(e)}",
                    severity=ValidationSeverity.ERROR,
                    error_code="VALIDATION_ERROR"
                )],
                warnings=[],
                validated_fields=[],
                validation_time_ms=1
            )


class DynamicDataValidator:
    """
    Dynamic data validator that uses real-time schema information from MCP server.
    """
    
    def __init__(
        self,
        schema_manager: MCPSchemaManager,
        config: Optional[DynamicValidationConfig] = None
    ):
        """Initialize dynamic data validator."""
        self.schema_manager = schema_manager
        self.config = config or DynamicValidationConfig()
        logger.info("Initialized Dynamic Data Validator with MCP schema management")
    
    async def validate_against_schema(
        self,
        data: Dict[str, Any],
        database: str,
        table: str
    ) -> ValidationResult:
        """Validate data against real-time schema information."""
        start_time = datetime.now()
        errors = []
        warnings = []
        validated_fields = []
        
        try:
            schema = await self.schema_manager.get_table_schema(database, table)
            
            if not schema:
                if self.config.fallback_to_static:
                    return await self._fallback_validation(data, table)
                else:
                    errors.append(ValidationError(
                        field="table",
                        message=f"Table {database}.{table} not found",
                        severity=ValidationSeverity.ERROR,
                        error_code="TABLE_NOT_FOUND"
                    ))
            else:
                # Validate data types
                if self.config.validate_types:
                    type_errors, type_warnings, type_fields = await self.validate_data_types(data, schema)
                    errors.extend(type_errors)
                    warnings.extend(type_warnings)
                    validated_fields.extend(type_fields)
            
            validation_time_ms = self._get_elapsed_ms(start_time)
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                validated_fields=list(set(validated_fields)),
                validation_time_ms=validation_time_ms
            )
            
        except Exception as e:
            logger.error(f"Dynamic validation failed: {e}")
            if self.config.fallback_to_static:
                return await self._fallback_validation(data, table)
            else:
                return ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        field="validation_system",
                        message=f"Validation system error: {str(e)}",
                        severity=ValidationSeverity.ERROR,
                        error_code="VALIDATION_SYSTEM_ERROR"
                    )],
                    warnings=warnings,
                    validated_fields=validated_fields,
                    validation_time_ms=self._get_elapsed_ms(start_time)
                )
    
    async def validate_data_types(
        self,
        data: Dict[str, Any],
        schema: TableSchema
    ) -> Tuple[List[ValidationError], List[ValidationWarning], List[str]]:
        """Validate data types against current schema."""
        errors = []
        warnings = []
        validated_fields = []
        
        columns_by_name = {col.name: col for col in schema.columns}
        
        for field_name, value in data.items():
            if field_name not in columns_by_name:
                continue
            
            column = columns_by_name[field_name]
            validated_fields.append(field_name)
            
            # Handle NULL values
            if value is None:
                if not column.is_nullable:
                    errors.append(ValidationError(
                        field=field_name,
                        message=f"Field '{field_name}' cannot be NULL",
                        severity=ValidationSeverity.ERROR,
                        error_code="NULL_NOT_ALLOWED"
                    ))
                continue
            
            # Basic type validation
            data_type = column.data_type.lower()
            
            if data_type in ['int', 'integer', 'bigint', 'smallint', 'tinyint']:
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        field=field_name,
                        message=f"Invalid integer value: {value}",
                        severity=ValidationSeverity.ERROR,
                        error_code="INVALID_INTEGER"
                    ))
            
            elif data_type in ['decimal', 'numeric', 'float', 'double']:
                try:
                    Decimal(str(value))
                except (InvalidOperation, ValueError, TypeError):
                    errors.append(ValidationError(
                        field=field_name,
                        message=f"Invalid decimal value: {value}",
                        severity=ValidationSeverity.ERROR,
                        error_code="INVALID_DECIMAL"
                    ))
            
            elif data_type in ['varchar', 'char', 'text']:
                str_value = str(value)
                if column.max_length and len(str_value) > column.max_length:
                    errors.append(ValidationError(
                        field=field_name,
                        message=f"String length {len(str_value)} exceeds maximum {column.max_length}",
                        severity=ValidationSeverity.ERROR,
                        error_code="STRING_TOO_LONG"
                    ))
        
        return errors, warnings, validated_fields
    
    async def validate_constraints(
        self,
        data: Dict[str, Any],
        schema: TableSchema
    ) -> Tuple[List[ValidationError], List[ValidationWarning], List[str]]:
        """Validate constraints using MCP server data."""
        errors = []
        warnings = []
        validated_fields = []
        
        # Validate primary key constraints
        for pk_column in schema.primary_keys:
            validated_fields.append(pk_column)
            
            if pk_column not in data and self.config.strict_mode:
                errors.append(ValidationError(
                    field=pk_column,
                    message=f"Primary key field '{pk_column}' is required",
                    severity=ValidationSeverity.ERROR,
                    error_code="PRIMARY_KEY_MISSING"
                ))
            
            if pk_column in data and data[pk_column] is None:
                errors.append(ValidationError(
                    field=pk_column,
                    message=f"Primary key field '{pk_column}' cannot be NULL",
                    severity=ValidationSeverity.ERROR,
                    error_code="PRIMARY_KEY_NULL"
                ))
        
        return errors, warnings, validated_fields
    
    async def validate_relationships(
        self,
        data: Dict[str, Any],
        schema: TableSchema
    ) -> Tuple[List[ValidationError], List[ValidationWarning], List[str]]:
        """Validate foreign key relationships."""
        errors = []
        warnings = []
        validated_fields = []
        
        for fk in schema.foreign_keys:
            validated_fields.append(fk.column)
            
            if fk.column in data:
                fk_value = data[fk.column]
                
                if isinstance(fk_value, str) and not fk_value.strip():
                    warnings.append(ValidationWarning(
                        field=fk.column,
                        message=f"Foreign key '{fk.column}' references empty string",
                        suggestion="Ensure foreign key values are meaningful"
                    ))
        
        return errors, warnings, validated_fields
    
    async def _fallback_validation(
        self,
        data: Dict[str, Any],
        table: str
    ) -> ValidationResult:
        """Fallback validation when MCP is unavailable."""
        start_time = datetime.now()
        
        try:
            # When MCP is unavailable, perform basic validation
            errors = []
            warnings = [ValidationWarning(
                field="validation_fallback",
                message=f"MCP schema server unavailable for table '{table}' - using basic validation",
                suggestion="Ensure MCP server is available for full schema-based validation"
            )]
            
            # Basic validation: check for empty or null values in known critical fields
            validated_fields = []
            for field_name, value in data.items():
                validated_fields.append(field_name)
                
                # Basic null/empty checks
                if value is None:
                    warnings.append(ValidationWarning(
                        field=field_name,
                        message=f"Field '{field_name}' is null",
                        suggestion="Consider providing a value for this field"
                    ))
                elif isinstance(value, str) and not value.strip():
                    warnings.append(ValidationWarning(
                        field=field_name,
                        message=f"Field '{field_name}' is empty",
                        suggestion="Consider providing a non-empty value for this field"
                    ))
                
                # Basic type validation for known financial fields
                if field_name in ['revenue', 'gross_profit', 'net_profit', 'operating_expenses', 
                                 'budgeted_amount', 'actual_amount', 'initial_amount', 'current_value']:
                    if value is not None:
                        try:
                            decimal_value = Decimal(str(value))
                            if decimal_value < 0 and field_name in ['revenue', 'budgeted_amount', 'initial_amount']:
                                warnings.append(ValidationWarning(
                                    field=field_name,
                                    message=f"Field '{field_name}' has negative value: {decimal_value}",
                                    suggestion="Verify that negative values are expected for this field"
                                ))
                        except (InvalidOperation, ValueError):
                            errors.append(ValidationError(
                                field=field_name,
                                message=f"Field '{field_name}' has invalid decimal value: {value}",
                                severity=ValidationSeverity.ERROR,
                                error_code="INVALID_DECIMAL"
                            ))
                
                # Basic date validation
                if field_name in ['period_date', 'start_date', 'end_date']:
                    if value is not None and not isinstance(value, (datetime, str)):
                        errors.append(ValidationError(
                            field=field_name,
                            message=f"Field '{field_name}' must be a date or string",
                            severity=ValidationSeverity.ERROR,
                            error_code="INVALID_DATE_TYPE"
                        ))
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                validated_fields=validated_fields,
                validation_time_ms=self._get_elapsed_ms(start_time)
            )
        
        except Exception as e:
            logger.error(f"Fallback validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="validation_system",
                    message=f"Fallback validation error: {str(e)}",
                    severity=ValidationSeverity.ERROR,
                    error_code="FALLBACK_VALIDATION_ERROR"
                )],
                warnings=[],
                validated_fields=[],
                validation_time_ms=self._get_elapsed_ms(start_time)
            )
    
    def _get_elapsed_ms(self, start_time: datetime) -> int:
        """Get elapsed time in milliseconds."""
        return int((datetime.now() - start_time).total_seconds() * 1000)