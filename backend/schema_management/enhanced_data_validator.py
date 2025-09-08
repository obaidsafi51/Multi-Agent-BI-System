"""
MCP-based Enhanced DataValidator for dynamic schema validation.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from enum import Enum

from .manager import MCPSchemaManager
from .dynamic_validator import DynamicDataValidator, DynamicValidationConfig
from .models import ValidationResult, ValidationError, ValidationWarning, ValidationSeverity

logger = logging.getLogger(__name__)


class PercentageType(Enum):
    """Enum defining different types of percentage validations"""
    STANDARD = "standard"           # -100% to 100% (tax rates, margins)
    ROI = "roi"                    # Unlimited range (can be very high or very low)
    GROWTH_RATE = "growth_rate"    # -100% to unlimited positive
    VARIANCE = "variance"          # Unlimited range (budget variances)
    MARGIN = "margin"              # 0% to 100% (profit margins)
    UTILIZATION = "utilization"    # 0% to 100% (resource utilization)


class MCPValidationError(Exception):
    """Custom exception for MCP validation errors"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Validation error for field '{field}': {message}")


class EnhancedDataValidator:
    """
    MCP-based enhanced data validator that provides dynamic schema-based validation.
    
    This class replaces static validation with real-time schema validation using MCP server.
    """
    
    def __init__(
        self,
        schema_manager: MCPSchemaManager,
        config: Optional[DynamicValidationConfig] = None
    ):
        """
        Initialize enhanced data validator with MCP schema manager.
        
        Args:
            schema_manager: MCP schema manager instance
            config: Validation configuration options
        """
        self.schema_manager = schema_manager
        self.dynamic_validator = DynamicDataValidator(schema_manager, config)
        self.config = config or DynamicValidationConfig()
        
        logger.info("Enhanced Data Validator initialized with MCP schema management")
    
    async def validate_data_with_schema(
        self,
        data: Dict[str, Any],
        database: str,
        table: str
    ) -> ValidationResult:
        """
        Validate data against real-time schema information.
        
        Args:
            data: Data to validate
            database: Database name
            table: Table name
            
        Returns:
            Validation result with errors, warnings, and validated fields
        """
        return await self.dynamic_validator.validate_against_schema(data, database, table)
    
    def validate_decimal(self, value: Any, field_name: str, max_digits: int = 15, decimal_places: int = 2) -> Decimal:
        """Validate and convert value to Decimal"""
        if value is None:
            return None
        
        try:
            decimal_value = Decimal(str(value))
            
            # Check precision
            sign, digits, exponent = decimal_value.as_tuple()
            if len(digits) > max_digits:
                raise MCPValidationError(
                    field_name, 
                    f"Value has too many digits (max {max_digits})", 
                    value
                )
            
            # Check decimal places
            actual_decimal_places = -exponent if exponent < 0 else 0
            if actual_decimal_places > decimal_places:
                raise MCPValidationError(
                    field_name, 
                    f"Value has {actual_decimal_places} decimal places (max {decimal_places})", 
                    value
                )
            
            return decimal_value
            
        except (InvalidOperation, ValueError) as e:
            raise MCPValidationError(field_name, f"Invalid decimal value: {e}", value)
    
    def validate_date(self, value: Any, field_name: str) -> date:
        """Validate and convert value to date"""
        if value is None:
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            try:
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
                
                raise ValueError("No matching date format found")
                
            except ValueError as e:
                raise MCPValidationError(field_name, f"Invalid date format: {e}", value)
        
        raise MCPValidationError(field_name, "Value must be a date, datetime, or date string", value)
    
    def validate_string(self, value: Any, field_name: str, max_length: int = None, min_length: int = 0) -> str:
        """Validate string value"""
        if value is None:
            return None
        
        if not isinstance(value, str):
            value = str(value)
        
        if len(value) < min_length:
            raise MCPValidationError(
                field_name, 
                f"String too short (min {min_length} characters)", 
                value
            )
        
        if max_length and len(value) > max_length:
            raise MCPValidationError(
                field_name, 
                f"String too long (max {max_length} characters)", 
                value
            )
        
        return value.strip()
    
    def validate_percentage_typed(
        self, 
        value: Any, 
        field_name: str, 
        percentage_type: PercentageType = PercentageType.STANDARD
    ) -> Tuple[Decimal, Optional[str]]:
        """Validate percentage with type-specific rules"""
        decimal_value = self.validate_decimal(value, field_name, 5, 2)
        warning = None
        
        if decimal_value is None:
            return decimal_value, warning
        
        # Define validation rules by percentage type
        validation_rules = {
            PercentageType.STANDARD: {"min": -100, "max": 100, "warn_threshold": None},
            PercentageType.ROI: {"min": None, "max": None, "warn_threshold": 1000},
            PercentageType.GROWTH_RATE: {"min": -100, "max": None, "warn_threshold": 500},
            PercentageType.VARIANCE: {"min": None, "max": None, "warn_threshold": 200},
            PercentageType.MARGIN: {"min": 0, "max": 100, "warn_threshold": None},
            PercentageType.UTILIZATION: {"min": 0, "max": 100, "warn_threshold": None},
        }
        
        rules = validation_rules.get(percentage_type, validation_rules[PercentageType.STANDARD])
        
        # Check minimum value
        if rules["min"] is not None and decimal_value < rules["min"]:
            raise MCPValidationError(
                field_name,
                f"Percentage must be >= {rules['min']}%",
                value
            )
        
        # Check maximum value
        if rules["max"] is not None and decimal_value > rules["max"]:
            raise MCPValidationError(
                field_name,
                f"Percentage must be <= {rules['max']}%",
                value
            )
        
        # Check warning threshold
        if rules["warn_threshold"] is not None:
            if percentage_type == PercentageType.VARIANCE:
                if abs(decimal_value) > rules["warn_threshold"]:
                    warning = f"Unusual {percentage_type.value} percentage: {decimal_value}% (threshold: ±{rules['warn_threshold']}%)"
            else:
                if decimal_value > rules["warn_threshold"]:
                    warning = f"Unusual {percentage_type.value} percentage: {decimal_value}% (threshold: {rules['warn_threshold']}%)"
        
        return decimal_value, warning
    
    def validate_positive_decimal(self, value: Any, field_name: str) -> Decimal:
        """Validate positive decimal value"""
        decimal_value = self.validate_decimal(value, field_name)
        
        if decimal_value is not None and decimal_value < 0:
            raise MCPValidationError(field_name, "Value must be positive", value)
        
        return decimal_value
    
    def validate_user_id(self, value: Any) -> str:
        """Validate user ID format"""
        import re
        user_id = self.validate_string(value, "user_id", max_length=100, min_length=1)
        
        if user_id and not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            raise MCPValidationError(
                "user_id", 
                "User ID can only contain letters, numbers, underscores, and hyphens", 
                value
            )
        
        return user_id
    
    def validate_json_data(self, value: Any, field_name: str) -> Dict[str, Any]:
        """Validate JSON data"""
        if value is None:
            return None
        
        if isinstance(value, dict):
            return value
        
        if isinstance(value, str):
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise MCPValidationError(field_name, f"Invalid JSON: {e}", value)
        
        raise MCPValidationError(field_name, "Value must be a dictionary or JSON string", value)


class EnhancedFinancialDataValidator:
    """
    MCP-based enhanced financial data validator.
    """
    
    def __init__(
        self,
        schema_manager: MCPSchemaManager,
        config: Optional[DynamicValidationConfig] = None
    ):
        """
        Initialize enhanced financial data validator.
        
        Args:
            schema_manager: MCP schema manager instance
            config: Validation configuration options
        """
        self.schema_manager = schema_manager
        self.enhanced_validator = EnhancedDataValidator(schema_manager, config)
        self.config = config or DynamicValidationConfig()
        
        logger.info("Enhanced Financial Data Validator initialized with MCP schema management")
    
    async def validate_financial_overview(self, data: Dict[str, Any], database: str = "ai_cfo_bi") -> Dict[str, Any]:
        """Validate financial overview data using MCP schema"""
        result = await self.enhanced_validator.validate_data_with_schema(data, database, "financial_overview")
        
        if not result.is_valid:
            error_messages = [f"{error.field}: {error.message}" for error in result.errors]
            raise MCPValidationError("financial_overview", "; ".join(error_messages))
        
        return data
    
    async def validate_cash_flow(self, data: Dict[str, Any], database: str = "ai_cfo_bi") -> Dict[str, Any]:
        """Validate cash flow data using MCP schema"""
        result = await self.enhanced_validator.validate_data_with_schema(data, database, "cash_flow")
        
        if not result.is_valid:
            error_messages = [f"{error.field}: {error.message}" for error in result.errors]
            raise MCPValidationError("cash_flow", "; ".join(error_messages))
        
        return data
    
    async def validate_budget_tracking(self, data: Dict[str, Any], database: str = "ai_cfo_bi") -> Dict[str, Any]:
        """Validate budget tracking data using MCP schema"""
        result = await self.enhanced_validator.validate_data_with_schema(data, database, "budget_tracking")
        
        if not result.is_valid:
            error_messages = [f"{error.field}: {error.message}" for error in result.errors]
            raise MCPValidationError("budget_tracking", "; ".join(error_messages))
        
        return data
    
    async def validate_investment(self, data: Dict[str, Any], database: str = "ai_cfo_bi") -> Dict[str, Any]:
        """Validate investment data using MCP schema"""
        result = await self.enhanced_validator.validate_data_with_schema(data, database, "investments")
        
        if not result.is_valid:
            error_messages = [f"{error.field}: {error.message}" for error in result.errors]
            raise MCPValidationError("investments", "; ".join(error_messages))
        
        return data


async def validate_data_quality_mcp(
    data: List[Dict[str, Any]], 
    table_name: str,
    database_name: str = "ai_cfo_bi",
    schema_manager: Optional[MCPSchemaManager] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate data quality using MCP schema management.
    
    Args:
        data: List of data records
        table_name: Name of the target table
        database_name: Name of the database
        schema_manager: MCP schema manager instance
        
    Returns:
        Tuple of (validated_data, warnings)
    """
    if not schema_manager:
        raise ValueError("MCP schema manager is required for data quality validation")
    
    validated_data = []
    warnings = []
    
    try:
        # Create enhanced validator with MCP integration
        enhanced_validator = EnhancedDataValidator(schema_manager)
        
        for i, record in enumerate(data):
            try:
                # Use dynamic validation with schema
                validation_result = await enhanced_validator.validate_data_with_schema(
                    record, database_name, table_name
                )
                
                if validation_result.is_valid:
                    validated_data.append(record)
                    
                    # Add any warnings from validation
                    for warning in validation_result.warnings:
                        warnings.append(f"Record {i+1} - {warning.field}: {warning.message}")
                else:
                    # Collect validation errors as warnings (don't reject the record)
                    for error in validation_result.errors:
                        warnings.append(f"Record {i+1} - {error.field}: {error.message}")
                    
                    # Still include the record but mark it as having issues
                    validated_data.append(record)
                
            except Exception as e:
                warnings.append(f"Record {i+1}: MCP validation error - {e}")
                logger.error(f"MCP validation error for record {i+1}: {e}")
                validated_data.append(record)  # Include record anyway
        
    except Exception as e:
        logger.error(f"MCP validation system error: {e}")
        warnings.append(f"MCP validation system error: {e}")
        validated_data = data  # Return all data if validation system fails
    
    return validated_data, warnings


# Factory functions for creating MCP-integrated validators

def create_enhanced_data_validator(schema_manager: MCPSchemaManager) -> EnhancedDataValidator:
    """
    Factory function to create an MCP-based enhanced data validator.
    
    Args:
        schema_manager: MCP schema manager instance
        
    Returns:
        Enhanced data validator
    """
    return EnhancedDataValidator(schema_manager)


def create_enhanced_financial_validator(schema_manager: MCPSchemaManager) -> EnhancedFinancialDataValidator:
    """
    Factory function to create an MCP-based enhanced financial data validator.
    
    Args:
        schema_manager: MCP schema manager instance
        
    Returns:
        Enhanced financial data validator
    """
    return EnhancedFinancialDataValidator(schema_manager)
