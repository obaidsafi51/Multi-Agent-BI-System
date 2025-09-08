"""
MCP-integrated data validation functions for database operations.
This module provides backward compatibility while using MCP schema management.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import asyncio

logger = logging.getLogger(__name__)

# Import MCP schema management components
try:
    from ..schema_management.manager import MCPSchemaManager
    from ..schema_management.enhanced_data_validator import (
        EnhancedDataValidator, EnhancedFinancialDataValidator, 
        MCPValidationError, PercentageType, validate_data_quality_mcp
    )
    from ..schema_management.dynamic_validator import DynamicValidationConfig
    MCP_AVAILABLE = True
except ImportError:
    logger.error("MCP schema management is required but not available")
    MCPSchemaManager = None
    EnhancedDataValidator = None
    EnhancedFinancialDataValidator = None
    MCPValidationError = None
    PercentageType = None
    DynamicValidationConfig = None
    validate_data_quality_mcp = None
    MCP_AVAILABLE = False


# Backward compatibility aliases
ValidationError = MCPValidationError if MCPValidationError else Exception
DataValidator = EnhancedDataValidator if EnhancedDataValidator else object
FinancialDataValidator = EnhancedFinancialDataValidator if EnhancedFinancialDataValidator else object


async def validate_data_quality_with_mcp(
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
    if not MCP_AVAILABLE:
        logger.error("MCP schema management not available")
        return data, ["MCP validation not available"]
    
    if not schema_manager:
        logger.error("MCP schema manager is required")
        return data, ["MCP schema manager not provided"]
    
    return await validate_data_quality_mcp(data, table_name, database_name, schema_manager)


def validate_data_quality(data: List[Dict[str, Any]], table_name: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Legacy validate data quality function - now requires MCP.
    
    Args:
        data: List of data records
        table_name: Name of the target table
        
    Returns:
        Tuple of (validated_data, warnings)
    """
    warnings = ["Static validation is deprecated. Use validate_data_quality_with_mcp() with MCP schema manager instead."]
    logger.warning("Static validation is deprecated. MCP schema management is now required.")
    return data, warnings


class MCPIntegratedDataValidator:
    """
    Data validator that integrates MCP schema management.
    
    This class provides a bridge between legacy validation code and the new
    MCP-based dynamic validation system.
    """
    
    def __init__(self, schema_manager: Optional[MCPSchemaManager] = None):
        """
        Initialize MCP integrated data validator.
        
        Args:
            schema_manager: MCP schema manager instance (required)
        """
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP schema management is required but not available")
        
        if not schema_manager:
            raise ValueError("MCP schema manager is required")
        
        self.schema_manager = schema_manager
        self.enhanced_validator = EnhancedDataValidator(schema_manager)
        logger.info("MCP integrated data validator initialized")
    
    async def validate_with_schema(
        self,
        data: Dict[str, Any],
        database: str,
        table: str
    ) -> Dict[str, Any]:
        """
        Validate data using MCP schema information.
        
        Args:
            data: Data to validate
            database: Database name
            table: Table name
            
        Returns:
            Validated data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        validation_result = await self.enhanced_validator.validate_data_with_schema(
            data, database, table
        )
        
        if not validation_result.is_valid:
            # Convert validation errors to legacy format
            error_messages = []
            for error in validation_result.errors:
                error_messages.append(f"{error.field}: {error.message}")
            
            raise ValidationError(
                "validation", 
                "; ".join(error_messages)
            )
        
        # Log warnings but don't fail validation
        for warning in validation_result.warnings:
            logger.warning(f"Validation warning - {warning.field}: {warning.message}")
        
        return data
    
    # Delegate to enhanced validator methods
    def validate_decimal(self, value: Any, field_name: str, max_digits: int = 15, decimal_places: int = 2):
        """Validate decimal value using enhanced validator."""
        return self.enhanced_validator.validate_decimal(value, field_name, max_digits, decimal_places)
    
    def validate_date(self, value: Any, field_name: str):
        """Validate date value using enhanced validator."""
        return self.enhanced_validator.validate_date(value, field_name)
    
    def validate_string(self, value: Any, field_name: str, max_length: int = None, min_length: int = 0):
        """Validate string value using enhanced validator."""
        return self.enhanced_validator.validate_string(value, field_name, max_length, min_length)
    
    def validate_percentage_typed(self, value: Any, field_name: str, percentage_type = None):
        """Validate percentage value using enhanced validator."""
        if percentage_type is None and PercentageType:
            percentage_type = PercentageType.STANDARD
        return self.enhanced_validator.validate_percentage_typed(value, field_name, percentage_type)
    
    def validate_percentage(self, value: Any, field_name: str):
        """Validate percentage value using enhanced validator."""
        if PercentageType:
            return self.enhanced_validator.validate_percentage_typed(value, field_name, PercentageType.STANDARD)
        else:
            return self.enhanced_validator.validate_decimal(value, field_name, 5, 2)
    
    def validate_positive_decimal(self, value: Any, field_name: str):
        """Validate positive decimal value using enhanced validator."""
        return self.enhanced_validator.validate_positive_decimal(value, field_name)
    
    def validate_user_id(self, value: Any):
        """Validate user ID using enhanced validator."""
        return self.enhanced_validator.validate_user_id(value)
    
    def validate_json_data(self, value: Any, field_name: str):
        """Validate JSON data using enhanced validator."""
        return self.enhanced_validator.validate_json_data(value, field_name)


class MCPIntegratedFinancialDataValidator:
    """
    Financial data validator that integrates MCP schema management.
    """
    
    def __init__(self, schema_manager: Optional[MCPSchemaManager] = None):
        """
        Initialize MCP integrated financial data validator.
        
        Args:
            schema_manager: MCP schema manager instance (required)
        """
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP schema management is required but not available")
        
        if not schema_manager:
            raise ValueError("MCP schema manager is required")
        
        self.schema_manager = schema_manager
        self.enhanced_validator = EnhancedFinancialDataValidator(schema_manager)
        logger.info("MCP integrated financial validator initialized")
    
    async def validate_financial_overview(self, data: Dict[str, Any], database: str = "ai_cfo_bi") -> Dict[str, Any]:
        """Validate financial overview data with MCP integration."""
        return await self.enhanced_validator.validate_financial_overview(data, database)
    
    async def validate_cash_flow(self, data: Dict[str, Any], database: str = "ai_cfo_bi") -> Dict[str, Any]:
        """Validate cash flow data with MCP integration."""
        return await self.enhanced_validator.validate_cash_flow(data, database)
    
    async def validate_budget_tracking(self, data: Dict[str, Any], database: str = "ai_cfo_bi") -> Dict[str, Any]:
        """Validate budget tracking data with MCP integration."""
        return await self.enhanced_validator.validate_budget_tracking(data, database)
    
    async def validate_investment(self, data: Dict[str, Any], database: str = "ai_cfo_bi") -> Dict[str, Any]:
        """Validate investment data with MCP integration."""
        return await self.enhanced_validator.validate_investment(data, database)


# Factory functions for creating MCP-integrated validators

def create_mcp_data_validator(schema_manager: MCPSchemaManager) -> MCPIntegratedDataValidator:
    """
    Factory function to create an MCP-integrated data validator.
    
    Args:
        schema_manager: MCP schema manager instance
        
    Returns:
        MCP integrated data validator
    """
    return MCPIntegratedDataValidator(schema_manager)


def create_mcp_financial_validator(schema_manager: MCPSchemaManager) -> MCPIntegratedFinancialDataValidator:
    """
    Factory function to create an MCP-integrated financial data validator.
    
    Args:
        schema_manager: MCP schema manager instance
        
    Returns:
        MCP integrated financial data validator
    """
    return MCPIntegratedFinancialDataValidator(schema_manager)


# Deprecated static validation warning
def _warn_static_validation_deprecated():
    """Warn about deprecated static validation."""
    logger.warning(
        "Static validation is deprecated. Please migrate to MCP-based validation using "
        "MCPIntegratedDataValidator or MCPIntegratedFinancialDataValidator with a "
        "schema_manager instance."
    )


# Legacy compatibility - these will log warnings when used
if not MCP_AVAILABLE:
    logger.error(
        "MCP schema management is not available. Please ensure the schema_management "
        "module is properly installed and configured."
    )
