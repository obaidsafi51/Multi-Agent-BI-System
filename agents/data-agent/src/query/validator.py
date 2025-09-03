"""
Data validation and quality checks for query results.
Ensures data integrity and provides quality scoring for financial data.
"""

import re
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of data validation with quality metrics"""
    is_valid: bool
    quality_score: float
    issues: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


@dataclass
class DataQualityMetrics:
    """Comprehensive data quality metrics"""
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    timeliness_score: float
    overall_score: float
    total_records: int
    valid_records: int
    null_count: int
    outlier_count: int


class DataValidator:
    """
    Validates query results and provides data quality assessment.
    Implements financial data-specific validation rules and quality checks.
    """
    
    # Financial data validation rules
    VALIDATION_RULES = {
        'revenue': {
            'min_value': 0,
            'max_value': 1e12,  # 1 trillion
            'required_fields': ['period_date', 'revenue'],
            'decimal_places': 2
        },
        'profit': {
            'min_value': -1e12,  # Can be negative
            'max_value': 1e12,
            'required_fields': ['period_date', 'net_profit'],
            'decimal_places': 2
        },
        'cash_flow': {
            'min_value': -1e12,  # Can be negative
            'max_value': 1e12,
            'required_fields': ['period_date', 'net_cash_flow'],
            'decimal_places': 2
        },
        'ratios': {
            'min_value': 0,
            'max_value': 1000,  # Some ratios can be very high
            'required_fields': ['period_date'],
            'decimal_places': 4
        }
    }
    
    # Outlier detection thresholds (standard deviations)
    OUTLIER_THRESHOLD = 3.0
    
    # Data freshness thresholds (days)
    FRESHNESS_THRESHOLDS = {
        'daily': 1,
        'monthly': 31,
        'quarterly': 93,
        'yearly': 366
    }
    
    def __init__(self):
        """Initialize data validator with configuration."""
        self.current_date = datetime.now()
    
    def validate_query_result(
        self, 
        query_result: Dict[str, Any], 
        metric_type: str,
        expected_period_type: str = 'monthly'
    ) -> ValidationResult:
        """
        Validate complete query result with comprehensive quality checks.
        
        Args:
            query_result: Query result from database
            metric_type: Type of financial metric
            expected_period_type: Expected data period type
            
        Returns:
            ValidationResult: Comprehensive validation result
        """
        try:
            data = query_result.get('data', [])
            columns = query_result.get('columns', [])
            
            if not data:
                return ValidationResult(
                    is_valid=False,
                    quality_score=0.0,
                    issues=['No data returned from query'],
                    warnings=[],
                    metadata={'total_records': 0}
                )
            
            # Perform individual validation checks
            structure_result = self._validate_data_structure(data, columns, metric_type)
            values_result = self._validate_data_values(data, metric_type)
            consistency_result = self._validate_data_consistency(data)
            freshness_result = self._validate_data_freshness(data, expected_period_type)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                data, structure_result, values_result, consistency_result, freshness_result
            )
            
            # Combine all validation results
            all_issues = (
                structure_result.issues + values_result.issues + 
                consistency_result.issues + freshness_result.issues
            )
            
            all_warnings = (
                structure_result.warnings + values_result.warnings + 
                consistency_result.warnings + freshness_result.warnings
            )
            
            is_valid = (
                structure_result.is_valid and values_result.is_valid and 
                consistency_result.is_valid and freshness_result.is_valid
            )
            
            logger.info(
                "Data validation completed",
                metric_type=metric_type,
                is_valid=is_valid,
                quality_score=quality_metrics.overall_score,
                total_records=len(data),
                issues_count=len(all_issues)
            )
            
            return ValidationResult(
                is_valid=is_valid,
                quality_score=quality_metrics.overall_score,
                issues=all_issues,
                warnings=all_warnings,
                metadata={
                    'quality_metrics': quality_metrics,
                    'total_records': len(data),
                    'validation_timestamp': self.current_date.isoformat()
                }
            )
            
        except Exception as e:
            logger.error("Data validation failed", error=str(e), metric_type=metric_type)
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                issues=[f"Validation error: {str(e)}"],
                warnings=[],
                metadata={'error': str(e)}
            )
    
    def _validate_data_structure(
        self, data: List[Dict[str, Any]], columns: List[str], metric_type: str
    ) -> ValidationResult:
        """Validate data structure and required fields."""
        
        issues = []
        warnings = []
        
        # Check if data is properly structured
        if not isinstance(data, list):
            issues.append("Data is not in expected list format")
            return ValidationResult(False, 0.0, issues, warnings, {})
        
        if not data:
            issues.append("No data records found")
            return ValidationResult(False, 0.0, issues, warnings, {})
        
        # Check required fields based on metric type
        validation_rules = self._get_validation_rules(metric_type)
        required_fields = validation_rules.get('required_fields', [])
        
        missing_fields = []
        for field in required_fields:
            if field not in columns:
                missing_fields.append(field)
        
        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check data consistency across records
        if data:
            first_record_keys = set(data[0].keys())
            for i, record in enumerate(data[1:], 1):
                if set(record.keys()) != first_record_keys:
                    warnings.append(f"Inconsistent fields in record {i}")
        
        # Check for empty records
        empty_records = sum(1 for record in data if not any(record.values()))
        if empty_records > 0:
            warnings.append(f"Found {empty_records} empty records")
        
        is_valid = len(issues) == 0
        quality_score = 1.0 - (len(issues) * 0.3 + len(warnings) * 0.1)
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=max(0.0, quality_score),
            issues=issues,
            warnings=warnings,
            metadata={'empty_records': empty_records}
        )
    
    def _validate_data_values(
        self, data: List[Dict[str, Any]], metric_type: str
    ) -> ValidationResult:
        """Validate individual data values and ranges."""
        
        issues = []
        warnings = []
        validation_rules = self._get_validation_rules(metric_type)
        
        min_value = validation_rules.get('min_value')
        max_value = validation_rules.get('max_value')
        decimal_places = validation_rules.get('decimal_places', 2)
        
        null_count = 0
        invalid_count = 0
        outliers = []
        
        # Extract numeric values for statistical analysis
        numeric_values = []
        
        for i, record in enumerate(data):
            for key, value in record.items():
                if value is None:
                    null_count += 1
                    continue
                
                # Validate numeric financial fields
                if self._is_financial_field(key):
                    try:
                        numeric_value = float(value) if value is not None else None
                        
                        if numeric_value is not None:
                            numeric_values.append(numeric_value)
                            
                            # Range validation
                            if min_value is not None and numeric_value < min_value:
                                issues.append(f"Value {numeric_value} below minimum {min_value} in record {i}")
                                invalid_count += 1
                            
                            if max_value is not None and numeric_value > max_value:
                                issues.append(f"Value {numeric_value} above maximum {max_value} in record {i}")
                                invalid_count += 1
                            
                            # Decimal places validation
                            if isinstance(value, (float, Decimal)):
                                decimal_str = str(value)
                                if '.' in decimal_str:
                                    actual_places = len(decimal_str.split('.')[1])
                                    if actual_places > decimal_places:
                                        warnings.append(f"Excessive decimal places in record {i}: {actual_places}")
                    
                    except (ValueError, TypeError, InvalidOperation):
                        issues.append(f"Invalid numeric value '{value}' in record {i}")
                        invalid_count += 1
                
                # Validate date fields
                elif self._is_date_field(key):
                    if not self._validate_date_format(value):
                        issues.append(f"Invalid date format '{value}' in record {i}")
                        invalid_count += 1
        
        # Outlier detection
        if numeric_values and len(numeric_values) > 3:
            outliers = self._detect_outliers(numeric_values)
            if outliers:
                warnings.append(f"Detected {len(outliers)} potential outliers")
        
        is_valid = len(issues) == 0
        quality_score = 1.0 - (invalid_count / max(len(data), 1)) * 0.5
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=max(0.0, quality_score),
            issues=issues,
            warnings=warnings,
            metadata={
                'null_count': null_count,
                'invalid_count': invalid_count,
                'outlier_count': len(outliers)
            }
        )
    
    def _validate_data_consistency(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """Validate data consistency and logical relationships."""
        
        issues = []
        warnings = []
        
        # Check for duplicate periods
        periods = []
        for record in data:
            period = record.get('period') or record.get('period_date')
            if period:
                periods.append(period)
        
        if len(periods) != len(set(periods)):
            warnings.append("Duplicate time periods detected")
        
        # Check for logical inconsistencies in financial data
        for i, record in enumerate(data):
            # Revenue should generally be positive
            revenue = record.get('revenue')
            if revenue is not None and float(revenue) < 0:
                warnings.append(f"Negative revenue in record {i}: {revenue}")
            
            # Gross profit should not exceed revenue
            gross_profit = record.get('gross_profit')
            if revenue and gross_profit:
                try:
                    if float(gross_profit) > float(revenue):
                        issues.append(f"Gross profit exceeds revenue in record {i}")
                except (ValueError, TypeError):
                    pass
            
            # Check cash flow consistency
            operating_cf = record.get('operating_cash_flow')
            investing_cf = record.get('investing_cash_flow')
            financing_cf = record.get('financing_cash_flow')
            net_cf = record.get('net_cash_flow')
            
            if all(x is not None for x in [operating_cf, investing_cf, financing_cf, net_cf]):
                try:
                    calculated_net = float(operating_cf) + float(investing_cf) + float(financing_cf)
                    actual_net = float(net_cf)
                    if abs(calculated_net - actual_net) > 0.01:  # Allow for rounding
                        warnings.append(f"Cash flow components don't sum to net in record {i}")
                except (ValueError, TypeError):
                    pass
        
        is_valid = len(issues) == 0
        quality_score = 1.0 - (len(issues) * 0.2 + len(warnings) * 0.05)
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=max(0.0, quality_score),
            issues=issues,
            warnings=warnings,
            metadata={'duplicate_periods': len(periods) - len(set(periods))}
        )
    
    def _validate_data_freshness(
        self, data: List[Dict[str, Any]], expected_period_type: str
    ) -> ValidationResult:
        """Validate data freshness and timeliness."""
        
        issues = []
        warnings = []
        
        freshness_threshold = self.FRESHNESS_THRESHOLDS.get(expected_period_type, 31)
        
        # Find the most recent data point
        latest_date = None
        for record in data:
            period_date = record.get('period_date') or record.get('period_start')
            if period_date:
                try:
                    if isinstance(period_date, str):
                        date_obj = datetime.strptime(period_date[:10], '%Y-%m-%d')
                    elif isinstance(period_date, date) and not isinstance(period_date, datetime):
                        # Convert date to datetime for consistent comparison
                        date_obj = datetime.combine(period_date, datetime.min.time())
                    elif isinstance(period_date, datetime):
                        date_obj = period_date
                    else:
                        # Try to convert other types
                        date_obj = datetime.strptime(str(period_date)[:10], '%Y-%m-%d')
                    
                    if latest_date is None or date_obj > latest_date:
                        latest_date = date_obj
                        
                except (ValueError, TypeError):
                    continue
        
        if latest_date:
            # Ensure both dates are datetime objects before subtraction
            if isinstance(latest_date, date) and not isinstance(latest_date, datetime):
                latest_date = datetime.combine(latest_date, datetime.min.time())
            
            days_old = (self.current_date - latest_date).days
            
            if days_old > freshness_threshold * 2:
                issues.append(f"Data is {days_old} days old, exceeds threshold of {freshness_threshold * 2}")
            elif days_old > freshness_threshold:
                warnings.append(f"Data is {days_old} days old, approaching staleness threshold")
        else:
            warnings.append("Could not determine data freshness")
        
        is_valid = len(issues) == 0
        quality_score = 1.0 if latest_date and (self.current_date - latest_date).days <= freshness_threshold else 0.7
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=quality_score,
            issues=issues,
            warnings=warnings,
            metadata={
                'latest_date': latest_date.isoformat() if latest_date else None,
                'days_old': (self.current_date - latest_date).days if latest_date else None
            }
        )
    
    def _calculate_quality_metrics(
        self,
        data: List[Dict[str, Any]],
        structure_result: ValidationResult,
        values_result: ValidationResult,
        consistency_result: ValidationResult,
        freshness_result: ValidationResult
    ) -> DataQualityMetrics:
        """Calculate comprehensive data quality metrics."""
        
        total_records = len(data)
        
        # Calculate completeness (non-null values)
        total_fields = sum(len(record) for record in data)
        null_fields = sum(1 for record in data for value in record.values() if value is None)
        completeness_score = 1.0 - (null_fields / max(total_fields, 1))
        
        # Accuracy score from values validation
        accuracy_score = values_result.quality_score
        
        # Consistency score from consistency validation
        consistency_score = consistency_result.quality_score
        
        # Timeliness score from freshness validation
        timeliness_score = freshness_result.quality_score
        
        # Overall score (weighted average)
        overall_score = (
            completeness_score * 0.25 +
            accuracy_score * 0.35 +
            consistency_score * 0.25 +
            timeliness_score * 0.15
        )
        
        return DataQualityMetrics(
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            consistency_score=consistency_score,
            timeliness_score=timeliness_score,
            overall_score=overall_score,
            total_records=total_records,
            valid_records=total_records - values_result.metadata.get('invalid_count', 0),
            null_count=values_result.metadata.get('null_count', 0),
            outlier_count=values_result.metadata.get('outlier_count', 0)
        )
    
    def _get_validation_rules(self, metric_type: str) -> Dict[str, Any]:
        """Get validation rules for a specific metric type."""
        
        # Map metric types to validation rule categories
        if metric_type in ['revenue', 'sales', 'income', 'turnover']:
            return self.VALIDATION_RULES['revenue']
        elif metric_type in ['profit', 'net_profit', 'gross_profit']:
            return self.VALIDATION_RULES['profit']
        elif 'cash_flow' in metric_type:
            return self.VALIDATION_RULES['cash_flow']
        elif 'ratio' in metric_type or metric_type in ['debt_to_equity', 'current_ratio', 'quick_ratio']:
            return self.VALIDATION_RULES['ratios']
        else:
            # Default rules
            return {
                'min_value': None,
                'max_value': None,
                'required_fields': ['period_date'],
                'decimal_places': 2
            }
    
    def _is_financial_field(self, field_name: str) -> bool:
        """Check if a field contains financial data."""
        financial_keywords = [
            'revenue', 'profit', 'income', 'expense', 'cost', 'cash', 'flow',
            'amount', 'value', 'balance', 'ratio', 'margin', 'roi', 'variance'
        ]
        return any(keyword in field_name.lower() for keyword in financial_keywords)
    
    def _is_date_field(self, field_name: str) -> bool:
        """Check if a field contains date data."""
        date_keywords = ['date', 'period', 'time', 'start', 'end']
        return any(keyword in field_name.lower() for keyword in date_keywords)
    
    def _validate_date_format(self, date_value: Any) -> bool:
        """Validate date format and value."""
        if date_value is None:
            return False
        
        try:
            if isinstance(date_value, datetime):
                return True
            elif isinstance(date_value, str):
                # Try common date formats
                formats = ['%Y-%m-%d', '%Y-%m', '%Y-Q%m', '%Y']
                for fmt in formats:
                    try:
                        datetime.strptime(date_value, fmt)
                        return True
                    except ValueError:
                        continue
                return False
            else:
                return False
        except Exception:
            return False
    
    def _detect_outliers(self, values: List[float]) -> List[int]:
        """Detect outliers using statistical methods."""
        if len(values) < 3:
            return []
        
        # Calculate mean and standard deviation
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        # Find outliers (values beyond threshold standard deviations)
        outliers = []
        for i, value in enumerate(values):
            if abs(value - mean) > self.OUTLIER_THRESHOLD * std_dev:
                outliers.append(i)
        
        return outliers


# Global validator instance
_data_validator: Optional[DataValidator] = None


def get_data_validator() -> DataValidator:
    """Get or create global data validator instance."""
    global _data_validator
    
    if _data_validator is None:
        _data_validator = DataValidator()
    
    return _data_validator