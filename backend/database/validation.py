"""
Data validation functions for database operations.
"""

from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import re
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Validation error for field '{field}': {message}")


class DataValidator:
    """Data validation utilities for financial data"""
    
    @staticmethod
    def validate_decimal(value: Any, field_name: str, max_digits: int = 15, decimal_places: int = 2) -> Decimal:
        """Validate and convert value to Decimal"""
        if value is None:
            return None
        
        try:
            decimal_value = Decimal(str(value))
            
            # Check precision
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
    def validate_percentage(value: Any, field_name: str) -> Decimal:
        """Validate percentage value (-100 to 100)"""
        decimal_value = DataValidator.validate_decimal(value, field_name, 5, 2)
        
        if decimal_value is not None and (decimal_value < -100 or decimal_value > 100):
            raise ValidationError(
                field_name, 
                "Percentage must be between -100 and 100", 
                value
            )
        
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
            
            # Calculate variance percentage only if budgeted amount is greater than 0
            # When budget is 0, percentage variance is undefined/infinite
            if validated['budgeted_amount'] is not None and validated['budgeted_amount'] > 0:
                variance_pct = (variance / validated['budgeted_amount']) * 100
                validated['variance_percentage'] = DataValidator.validate_decimal(
                    variance_pct, 'variance_percentage', 5, 2
                )
            else:
                # When budgeted_amount is 0, variance percentage is undefined
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
            # Calculate ROI only if initial amount is greater than 0
            # When initial investment is 0, ROI is undefined/infinite
            if validated['initial_amount'] is not None and validated['initial_amount'] > 0:
                roi = ((validated['current_value'] - validated['initial_amount']) / 
                       validated['initial_amount']) * 100
                validated['roi_percentage'] = DataValidator.validate_decimal(roi, 'roi_percentage', 5, 2)
            else:
                # When initial_amount is 0, ROI is undefined
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