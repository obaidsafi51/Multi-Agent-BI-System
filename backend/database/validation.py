"""
Data validation functions for database operations.
"""

from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


class PercentageType(Enum):
    """Enum defining different types of percentage validations"""
    STANDARD = "standard"           # -100% to 100% (tax rates, margins)
    ROI = "roi"                    # Unlimited range (can be very high or very low)
    GROWTH_RATE = "growth_rate"    # -100% to unlimited positive
    VARIANCE = "variance"          # Unlimited range (budget variances)
    MARGIN = "margin"              # 0% to 100% (profit margins)
    UTILIZATION = "utilization"    # 0% to 100% (resource utilization)


@dataclass
class PercentageValidationConfig:
    """Configuration for percentage validation rules"""
    min_value: Optional[Decimal]
    max_value: Optional[Decimal]
    warning_threshold: Optional[Decimal]
    allow_null: bool = True
    precision: int = 2
    description: str = ""


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, field: str, message: str, value: Any = None, 
                 percentage_type: Optional[PercentageType] = None):
        self.field = field
        self.message = message
        self.value = value
        self.percentage_type = percentage_type
        
        if percentage_type:
            config = DataValidator.get_percentage_config(percentage_type)
            self.message += f" (Expected range for {percentage_type.value}: {config.description})"
        
        super().__init__(f"Validation error for field '{field}': {self.message}")


class ValidationWarning:
    """Warning for percentage values that are valid but unusual"""
    def __init__(self, field: str, message: str, value: Any, percentage_type: PercentageType):
        self.field = field
        self.message = message
        self.value = value
        self.percentage_type = percentage_type
        self.timestamp = datetime.now()


class DataValidator:
    """Data validation utilities for financial data"""
    
    # Minimum threshold for financial calculations to avoid division by very small numbers
    EPSILON = Decimal('0.01')  # 1 cent minimum for percentage calculations
    
    # Percentage validation configuration registry
    PERCENTAGE_VALIDATION_CONFIGS = {
        PercentageType.STANDARD: PercentageValidationConfig(
            min_value=Decimal('-100'),
            max_value=Decimal('100'),
            warning_threshold=None,
            description="Standard percentage (-100% to 100%)"
        ),
        PercentageType.ROI: PercentageValidationConfig(
            min_value=None,
            max_value=None,
            warning_threshold=Decimal('1000'),  # Warn if >1000%
            description="Return on Investment (unlimited range)"
        ),
        PercentageType.GROWTH_RATE: PercentageValidationConfig(
            min_value=Decimal('-100'),
            max_value=None,
            warning_threshold=Decimal('500'),   # Warn if >500%
            description="Growth rate (-100% to unlimited positive)"
        ),
        PercentageType.VARIANCE: PercentageValidationConfig(
            min_value=None,
            max_value=None,
            warning_threshold=Decimal('200'),   # Warn if >200% or <-200%
            description="Budget variance (unlimited range)"
        ),
        PercentageType.MARGIN: PercentageValidationConfig(
            min_value=Decimal('0'),
            max_value=Decimal('100'),
            warning_threshold=None,
            description="Profit margin (0% to 100%)"
        ),
        PercentageType.UTILIZATION: PercentageValidationConfig(
            min_value=Decimal('0'),
            max_value=Decimal('100'),
            warning_threshold=None,
            description="Resource utilization (0% to 100%)"
        )
    }
    
    @staticmethod
    def validate_decimal(value: Any, field_name: str, max_digits: int = 15, decimal_places: int = 2) -> Decimal:
        """Validate and convert value to Decimal"""
        if value is None:
            return None
        
        try:
            decimal_value = Decimal(str(value))
            
            # Check precision (total number of significant digits)
            # Decimal.as_tuple() returns (sign, digits, exponent) where:
            # - sign: 0 for positive, 1 for negative
            # - digits: tuple of individual digits (0-9) representing ALL significant digits
            # - exponent: power of 10 to apply to the digits
            #
            # Examples of digits tuple:
            #   123.45   → digits = (1, 2, 3, 4, 5), len = 5 significant digits
            #   0.00123  → digits = (1, 2, 3), len = 3 significant digits (leading zeros ignored)
            #   1230000  → digits = (1, 2, 3, 0, 0, 0, 0), len = 7 digits (trailing zeros count)
            #   0.10     → digits = (1, 0), len = 2 significant digits
            #   1000.00  → digits = (1, 0, 0, 0, 0, 0), len = 6 digits (all zeros after 1 count)
            #
            # The len(digits) gives us the total count of significant digits,
            # which is what we want to limit for precision control
            sign, digits, exponent = decimal_value.as_tuple()
            if len(digits) > max_digits:
                raise ValidationError(
                    field_name, 
                    f"Value has too many digits (max {max_digits})", 
                    value
                )
            
            # Check decimal places
            # In Decimal.as_tuple(), exponent represents the power of 10
            # For decimal numbers: exponent = -number_of_decimal_places
            # Examples:
            #   123.45 → exponent = -2 (2 decimal places)
            #   123.456 → exponent = -3 (3 decimal places)
            #   123 → exponent = 0 (0 decimal places)
            actual_decimal_places = -exponent if exponent < 0 else 0
            if actual_decimal_places > decimal_places:
                raise ValidationError(
                    field_name, 
                    f"Value has {actual_decimal_places} decimal places (max {decimal_places})", 
                    value
                )
            
            return decimal_value
            
        except (InvalidOperation, ValueError) as e:
            raise ValidationError(field_name, f"Invalid decimal value: {e}", value)
    
    @staticmethod
    def validate_date(value: Any, field_name: str) -> date:
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
                raise ValidationError(field_name, f"Invalid date format: {e}", value)
        
        raise ValidationError(field_name, "Value must be a date, datetime, or date string", value)
    
    @staticmethod
    def validate_string(value: Any, field_name: str, max_length: int = None, min_length: int = 0) -> str:
        """Validate string value"""
        if value is None:
            return None
        
        if not isinstance(value, str):
            value = str(value)
        
        if len(value) < min_length:
            raise ValidationError(
                field_name, 
                f"String too short (min {min_length} characters)", 
                value
            )
        
        if max_length and len(value) > max_length:
            raise ValidationError(
                field_name, 
                f"String too long (max {max_length} characters)", 
                value
            )
        
        return value.strip()
    
    @staticmethod
    def get_percentage_config(percentage_type: PercentageType) -> PercentageValidationConfig:
        """Get validation configuration for percentage type"""
        return DataValidator.PERCENTAGE_VALIDATION_CONFIGS[percentage_type]
    
    @staticmethod
    def validate_percentage_typed(
        value: Any, 
        field_name: str, 
        percentage_type: PercentageType = PercentageType.STANDARD
    ) -> Tuple[Decimal, Optional[ValidationWarning]]:
        """Validate percentage with type-specific rules"""
        decimal_value = DataValidator.validate_decimal(value, field_name, 5, 2)
        warning = None
        
        if decimal_value is None:
            return decimal_value, warning
        
        config = DataValidator.get_percentage_config(percentage_type)
        
        # Check minimum value
        if config.min_value is not None and decimal_value < config.min_value:
            raise ValidationError(
                field_name,
                f"Percentage must be >= {config.min_value}%",
                value,
                percentage_type
            )
        
        # Check maximum value
        if config.max_value is not None and decimal_value > config.max_value:
            raise ValidationError(
                field_name,
                f"Percentage must be <= {config.max_value}%",
                value,
                percentage_type
            )
        
        # Check warning threshold
        if config.warning_threshold is not None:
            if percentage_type == PercentageType.VARIANCE:
                # For variance, warn if absolute value exceeds threshold
                if abs(decimal_value) > config.warning_threshold:
                    warning = ValidationWarning(
                        field_name,
                        f"Unusual {percentage_type.value} percentage: {decimal_value}% (threshold: ±{config.warning_threshold}%)",
                        value,
                        percentage_type
                    )
            else:
                # For other types, warn if value exceeds threshold
                if decimal_value > config.warning_threshold:
                    warning = ValidationWarning(
                        field_name,
                        f"Unusual {percentage_type.value} percentage: {decimal_value}% (threshold: {config.warning_threshold}%)",
                        value,
                        percentage_type
                    )
        
        return decimal_value, warning
    
    @staticmethod
    def validate_percentage(value: Any, field_name: str) -> Decimal:
        """Validate percentage value (-100 to 100) - Legacy method for backward compatibility"""
        decimal_value, warning = DataValidator.validate_percentage_typed(
            value, field_name, PercentageType.STANDARD
        )
        
        if warning:
            logger.warning(f"Percentage validation warning: {warning.message}")
        
        return decimal_value
    
    @staticmethod
    def validate_positive_decimal(value: Any, field_name: str) -> Decimal:
        """Validate positive decimal value"""
        decimal_value = DataValidator.validate_decimal(value, field_name)
        
        if decimal_value is not None and decimal_value < 0:
            raise ValidationError(field_name, "Value must be positive", value)
        
        return decimal_value
    
    @staticmethod
    def validate_user_id(value: Any) -> str:
        """Validate user ID format"""
        user_id = DataValidator.validate_string(value, "user_id", max_length=100, min_length=1)
        
        if user_id and not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            raise ValidationError(
                "user_id", 
                "User ID can only contain letters, numbers, underscores, and hyphens", 
                value
            )
        
        return user_id
    
    @staticmethod
    def validate_json_data(value: Any, field_name: str) -> Dict[str, Any]:
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
                raise ValidationError(field_name, f"Invalid JSON: {e}", value)
        
        raise ValidationError(field_name, "Value must be a dictionary or JSON string", value)


class FinancialDataValidator:
    """Specialized validator for financial data"""
    
    @staticmethod
    def validate_financial_overview(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate financial overview data"""
        validated = {}
        
        # Required fields
        validated['period_date'] = DataValidator.validate_date(data.get('period_date'), 'period_date')
        validated['period_type'] = DataValidator.validate_string(
            data.get('period_type'), 'period_type', max_length=20
        )
        
        # Validate period_type enum
        valid_periods = ['daily', 'monthly', 'quarterly', 'yearly']
        if validated['period_type'] not in valid_periods:
            raise ValidationError(
                'period_type', 
                f"Must be one of: {', '.join(valid_periods)}", 
                validated['period_type']
            )
        
        # Optional financial fields
        validated['revenue'] = DataValidator.validate_positive_decimal(
            data.get('revenue'), 'revenue'
        )
        validated['gross_profit'] = DataValidator.validate_decimal(
            data.get('gross_profit'), 'gross_profit'
        )
        validated['net_profit'] = DataValidator.validate_decimal(
            data.get('net_profit'), 'net_profit'
        )
        validated['operating_expenses'] = DataValidator.validate_positive_decimal(
            data.get('operating_expenses'), 'operating_expenses'
        )
        
        # Business logic validation
        if (validated['revenue'] and validated['gross_profit'] and 
            validated['gross_profit'] > validated['revenue']):
            raise ValidationError(
                'gross_profit', 
                'Gross profit cannot exceed revenue', 
                validated['gross_profit']
            )
        
        return validated
    
    @staticmethod
    def validate_cash_flow(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate cash flow data"""
        validated = {}
        
        validated['period_date'] = DataValidator.validate_date(data.get('period_date'), 'period_date')
        validated['operating_cash_flow'] = DataValidator.validate_decimal(
            data.get('operating_cash_flow'), 'operating_cash_flow'
        )
        validated['investing_cash_flow'] = DataValidator.validate_decimal(
            data.get('investing_cash_flow'), 'investing_cash_flow'
        )
        validated['financing_cash_flow'] = DataValidator.validate_decimal(
            data.get('financing_cash_flow'), 'financing_cash_flow'
        )
        validated['net_cash_flow'] = DataValidator.validate_decimal(
            data.get('net_cash_flow'), 'net_cash_flow'
        )
        validated['cash_balance'] = DataValidator.validate_positive_decimal(
            data.get('cash_balance'), 'cash_balance'
        )
        
        return validated
    
    @staticmethod
    def validate_budget_tracking(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate budget tracking data"""
        validated = {}
        
        validated['department'] = DataValidator.validate_string(
            data.get('department'), 'department', max_length=100, min_length=1
        )
        validated['period_date'] = DataValidator.validate_date(data.get('period_date'), 'period_date')
        validated['budgeted_amount'] = DataValidator.validate_positive_decimal(
            data.get('budgeted_amount'), 'budgeted_amount'
        )
        validated['actual_amount'] = DataValidator.validate_positive_decimal(
            data.get('actual_amount'), 'actual_amount'
        )
        
        # Calculate variance if both amounts are provided
        if validated['budgeted_amount'] is not None and validated['actual_amount'] is not None:
            variance = validated['actual_amount'] - validated['budgeted_amount']
            validated['variance_amount'] = variance
            
            # Calculate variance percentage only if budgeted amount is greater than or equal to epsilon
            # When budget is very small or zero, percentage variance is undefined/misleading
            if validated['budgeted_amount'] >= DataValidator.EPSILON:
                variance_pct = (variance / validated['budgeted_amount']) * 100
                validated['variance_percentage'], warning = DataValidator.validate_percentage_typed(
                    variance_pct, 'variance_percentage', PercentageType.VARIANCE
                )
                if warning:
                    logger.warning(f"Budget variance warning: {warning.message}")
            else:
                # When budgeted_amount is very small or zero, variance percentage is undefined
                # Set to None to indicate this special case
                validated['variance_percentage'] = None
        
        return validated
    
    @staticmethod
    def validate_investment(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate investment data"""
        validated = {}
        
        validated['investment_name'] = DataValidator.validate_string(
            data.get('investment_name'), 'investment_name', max_length=200, min_length=1
        )
        validated['investment_category'] = DataValidator.validate_string(
            data.get('investment_category'), 'investment_category', max_length=100
        )
        validated['initial_amount'] = DataValidator.validate_positive_decimal(
            data.get('initial_amount'), 'initial_amount'
        )
        validated['current_value'] = DataValidator.validate_positive_decimal(
            data.get('current_value'), 'current_value'
        )
        
        # Calculate ROI if both amounts are provided
        if validated['initial_amount'] is not None and validated['current_value'] is not None:
            # Calculate ROI only if initial amount is greater than or equal to epsilon
            # When initial investment is very small or zero, ROI is undefined/misleading
            if validated['initial_amount'] >= DataValidator.EPSILON:
                roi = ((validated['current_value'] - validated['initial_amount']) / 
                       validated['initial_amount']) * 100
                validated['roi_percentage'], warning = DataValidator.validate_percentage_typed(
                    roi, 'roi_percentage', PercentageType.ROI
                )
                if warning:
                    logger.warning(f"ROI warning: {warning.message}")
            else:
                # When initial_amount is very small or zero, ROI is undefined
                # Set to None to indicate this special case
                validated['roi_percentage'] = None
        
        validated['status'] = DataValidator.validate_string(data.get('status'), 'status')
        if validated['status']:
            valid_statuses = ['active', 'completed', 'terminated']
            if validated['status'] not in valid_statuses:
                raise ValidationError(
                    'status', 
                    f"Must be one of: {', '.join(valid_statuses)}", 
                    validated['status']
                )
        
        validated['start_date'] = DataValidator.validate_date(data.get('start_date'), 'start_date')
        validated['end_date'] = DataValidator.validate_date(data.get('end_date'), 'end_date')
        
        # Validate date logic
        if (validated['start_date'] and validated['end_date'] and 
            validated['start_date'] > validated['end_date']):
            raise ValidationError(
                'end_date', 
                'End date cannot be before start date', 
                validated['end_date']
            )
        
        return validated


def validate_data_quality(data: List[Dict[str, Any]], table_name: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate data quality and return cleaned data with warnings
    
    Args:
        data: List of data records
        table_name: Name of the target table
        
    Returns:
        Tuple of (validated_data, warnings)
    """
    validated_data = []
    warnings = []
    
    validator_map = {
        'financial_overview': FinancialDataValidator.validate_financial_overview,
        'cash_flow': FinancialDataValidator.validate_cash_flow,
        'budget_tracking': FinancialDataValidator.validate_budget_tracking,
        'investments': FinancialDataValidator.validate_investment,
    }
    
    validator = validator_map.get(table_name)
    if not validator:
        warnings.append(f"No specific validator found for table '{table_name}'")
        return data, warnings
    
    for i, record in enumerate(data):
        try:
            validated_record = validator(record)
            validated_data.append(validated_record)
        except ValidationError as e:
            warnings.append(f"Record {i+1}: {e}")
            logger.warning(f"Validation error in record {i+1}: {e}")
        except Exception as e:
            warnings.append(f"Record {i+1}: Unexpected error - {e}")
            logger.error(f"Unexpected validation error in record {i+1}: {e}")
    
    return validated_data, warnings