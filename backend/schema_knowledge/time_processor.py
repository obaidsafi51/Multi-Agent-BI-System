"""
Intelligent time period processing for quarterly, yearly, and monthly queries.
"""

from __future__ import annotations
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Union, Any
import calendar


from .types import PeriodType, TimePeriod, ComparisonPeriod


class TimeProcessor:
    """Intelligent time period processing for financial queries"""
    
    def __init__(self, fiscal_year_start_month: int = 1):
        """
        Initialize time processor with fiscal year configuration.

        Args:
            fiscal_year_start_month: Month when fiscal year starts (1-12, where 1=January)

        Raises:
            TypeError: If fiscal_year_start_month is not an integer
            ValueError: If fiscal_year_start_month is not between 1 and 12
        """
        # Validate fiscal_year_start_month
        if not isinstance(fiscal_year_start_month, int):
            raise TypeError(f"fiscal_year_start_month must be an integer, got {type(fiscal_year_start_month)}")
        if not (1 <= fiscal_year_start_month <= 12):
            raise ValueError(f"fiscal_year_start_month must be between 1 and 12, got {fiscal_year_start_month}")
        self.fiscal_year_start_month = fiscal_year_start_month
        self.current_date = datetime.now().date()
        # Validate fiscal_year_start_month and initialize patterns
        self._validate_fiscal_year_start_month()
        # Common time period patterns
        self.period_patterns = {
            # Relative patterns (most specific first)
            r'\bthis quarter\b|\bcurrent quarter\b': ('quarterly', 'current'),
            r'\blast quarter\b|\bprevious quarter\b': ('quarterly', 'previous'),
            r'\bthis month\b|\bcurrent month\b': ('monthly', 'current'),
            r'\blast month\b|\bprevious month\b': ('monthly', 'previous'),
            r'\bthis year\b|\bcurrent year\b': ('yearly', 'current'),
            r'\blast year\b|\bprevious year\b': ('yearly', 'previous'),
            
            # Quarterly patterns
            r'\bq1\b|\bfirst quarter\b|\b1st quarter\b': ('quarterly', 1),
            r'\bq2\b|\bsecond quarter\b|\b2nd quarter\b': ('quarterly', 2),
            r'\bq3\b|\bthird quarter\b|\b3rd quarter\b': ('quarterly', 3),
            r'\bq4\b|\bfourth quarter\b|\b4th quarter\b': ('quarterly', 4),
            r'\bquarter\b|\bquarterly\b|\bqtd\b|\bquarter to date\b': ('quarterly', None),
            
            # Monthly patterns
            r'\bjanuary\b|\bjan\b': ('monthly', 1),
            r'\bfebruary\b|\bfeb\b': ('monthly', 2),
            r'\bmarch\b|\bmar\b': ('monthly', 3),
            r'\bapril\b|\bapr\b': ('monthly', 4),
            r'\bmay\b': ('monthly', 5),
            r'\bjune\b|\bjun\b': ('monthly', 6),
            r'\bjuly\b|\bjul\b': ('monthly', 7),
            r'\baugust\b|\baug\b': ('monthly', 8),
            r'\bseptember\b|\bsep\b|\bsept\b': ('monthly', 9),
            r'\boctober\b|\boct\b': ('monthly', 10),
            r'\bnovember\b|\bnov\b': ('monthly', 11),
            r'\bdecember\b|\bdec\b': ('monthly', 12),
            r'\bmonth\b|\bmonthly\b|\bmtd\b|\bmonth to date\b': ('monthly', None),
            
            # Yearly patterns
            r'\byear\b|\byearly\b|\bannual\b|\bannually\b|\bytd\b|\byear to date\b': ('yearly', None),
            
            # Range patterns
            r'\blast (\d+) months?\b': ('range_months', None),
            r'\blast (\d+) quarters?\b': ('range_quarters', None),
            r'\blast (\d+) years?\b': ('range_years', None),
            r'\bpast (\d+) months?\b': ('range_months', None),
            r'\bpast (\d+) quarters?\b': ('range_quarters', None),
            r'\bpast (\d+) years?\b': ('range_years', None),
        }
        # Comparison patterns
        self.comparison_patterns = {
            r'\bvs?\s+last year\b|\bcompared to last year\b|\byear over year\b|\byoy\b': 'year_over_year',
            r'\bvs?\s+last quarter\b|\bcompared to last quarter\b|\bquarter over quarter\b|\bqoq\b': 'quarter_over_quarter',
            r'\bvs?\s+last month\b|\bcompared to last month\b|\bmonth over month\b|\bmom\b': 'month_over_month',
            r'\bvs?\s+previous period\b|\bcompared to previous\b|\bperiod over period\b|\bpop\b': 'period_over_period',
        }
    
    def _validate_fiscal_year_start_month(self) -> None:
        """Validate that fiscal_year_start_month is an integer between 1 and 12."""
        if not isinstance(self.fiscal_year_start_month, int):
            raise TypeError(f"fiscal_year_start_month must be an integer, got {type(self.fiscal_year_start_month)}")
        if not (1 <= self.fiscal_year_start_month <= 12):
            raise ValueError(f"fiscal_year_start_month must be between 1 and 12, got {self.fiscal_year_start_month}")
        
    
    def parse_time_period(self, time_expression: str, reference_date: Optional[date] = None) -> TimePeriod:
        """Parse a natural language time expression into a structured time period"""
        if reference_date is None:
            reference_date = self.current_date
        
        time_expr = time_expression.lower().strip()
        
        # Extract year if present
        year = self._extract_year(time_expr, reference_date.year)
        # Standalone 4-digit year: treat as full-year period
        if re.fullmatch(r'\d{4}', time_expr):
            return self._create_period('yearly', None, year, reference_date, time_expr)
        
        # Try to match patterns
        for pattern, (period_type, period_value) in self.period_patterns.items():
            if re.search(pattern, time_expr, re.IGNORECASE):
                return self._create_period(period_type, period_value, year, reference_date, time_expr)
        
        # Try to parse specific date ranges
        date_range = self._parse_date_range(time_expr, reference_date)
        if date_range:
            return date_range
        
        # Default to current year if no pattern matches
        return self._create_period('yearly', 'current', year, reference_date, time_expr)
    
    def _extract_year(self, time_expr: str, default_year: int) -> int:
        """Extract year from time expression"""
        # Look for 4-digit years
        year_match = re.search(r'\b(20\d{2})\b', time_expr)
        if year_match:
            return int(year_match.group(1))
        
        # Look for 2-digit years (assume 20xx)
        year_match = re.search(r'\b(\d{2})\b', time_expr)
        if year_match:
            year_2digit = int(year_match.group(1))
            if year_2digit <= 50:  # Assume 2000-2050
                return 2000 + year_2digit
            else:  # Assume 1951-1999
                return 1900 + year_2digit
        
        return default_year
    
    def _create_period(self, period_type: str, period_value: Union[int, str, None], year: int,
                      reference_date: date, original_expr: str) -> TimePeriod:
        """Create a TimePeriod object based on parsed components"""
        
        if period_type == 'quarterly':
            return self._create_quarterly_period(period_value, year, reference_date, original_expr)
        elif period_type == 'monthly':
            return self._create_monthly_period(period_value, year, reference_date, original_expr)
        elif period_type == 'yearly':
            return self._create_yearly_period(period_value, year, reference_date, original_expr)
        elif period_type.startswith('range_'):
            return self._create_range_period(period_type, original_expr, reference_date)
        else:
            # Default to yearly
            return self._create_yearly_period('current', year, reference_date, original_expr)
    
    def _create_quarterly_period(self, quarter_value: Union[int, str, None], year: int,
                               reference_date: date, original_expr: str) -> TimePeriod:
        """Create quarterly time period"""
        
        # Store the original quarter_value to check for partial periods later
        original_quarter_value = quarter_value
        
        if quarter_value == 'current':
            quarter = self._get_current_quarter(reference_date)
        elif quarter_value == 'previous':
            current_quarter = self._get_current_quarter(reference_date)
            if current_quarter == 1:
                quarter = 4
                year = year - 1
            else:
                quarter = current_quarter - 1
        elif isinstance(quarter_value, int):
            quarter = quarter_value
        else:
            quarter = self._get_current_quarter(reference_date)
        
        # Calculate quarter start and end dates
        start_month = (quarter - 1) * 3 + self.fiscal_year_start_month
        if start_month > 12:
            start_month -= 12
            fiscal_year = year + 1
        else:
            fiscal_year = year
        
        start_date = date(fiscal_year, start_month, 1)
        
        # Calculate end month
        end_month = start_month + 2
        if end_month > 12:
            end_month -= 12
            end_year = fiscal_year + 1
        else:
            end_year = fiscal_year
        
        # Get last day of end month
        last_day = calendar.monthrange(end_year, end_month)[1]
        end_date = date(end_year, end_month, last_day)
        
        # Check if it's a partial period (current quarter not yet complete)
        is_partial = (original_quarter_value == 'current' and reference_date < end_date)
        
        return TimePeriod(
            start_date=start_date,
            end_date=end_date,
            period_type=PeriodType.QUARTERLY,
            period_label=f"Q{quarter} {fiscal_year}",
            fiscal_year=fiscal_year,
            quarter=quarter,
            year=fiscal_year,
            is_partial=is_partial,
            confidence=0.95
        )
    
    def _create_monthly_period(self, month_value: Union[int, str, None], year: int,
                             reference_date: date, original_expr: str) -> TimePeriod:
        """Create monthly time period"""
        
        if month_value == 'current':
            month = reference_date.month
        elif month_value == 'previous':
            if reference_date.month == 1:
                month = 12
                year = year - 1
            else:
                month = reference_date.month - 1
        elif isinstance(month_value, int):
            month = month_value
        else:
            month = reference_date.month
        
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        
        # Check if it's a partial period
        is_partial = (month_value == 'current' and reference_date.day < last_day)
        
        month_name = calendar.month_name[month]
        
        return TimePeriod(
            start_date=start_date,
            end_date=end_date,
            period_type=PeriodType.MONTHLY,
            period_label=f"{month_name} {year}",
            month=month,
            year=year,
            is_partial=is_partial,
            confidence=0.95
        )
    
    def _create_yearly_period(self, year_value: Union[int, str, None], year: int,
                            reference_date: date, original_expr: str) -> TimePeriod:
        """Create yearly time period"""
        
        if year_value == 'current':
            target_year = reference_date.year
        elif year_value == 'previous':
            target_year = reference_date.year - 1
        else:
            target_year = year
        
        # Handle fiscal year vs calendar year
        if self.fiscal_year_start_month == 1:
            # Calendar year
            start_date = date(target_year, 1, 1)
            end_date = date(target_year, 12, 31)
            fiscal_year = target_year
        else:
            # Fiscal year
            start_date = date(target_year, self.fiscal_year_start_month, 1)
            if self.fiscal_year_start_month > 1:
                end_date = date(target_year + 1, self.fiscal_year_start_month - 1, 
                              calendar.monthrange(target_year + 1, self.fiscal_year_start_month - 1)[1])
            else:
                end_date = date(target_year, 12, 31)
            fiscal_year = target_year
        
        # Check if it's a partial period
        is_partial = (year_value == 'current' and reference_date < end_date)
        
        return TimePeriod(
            start_date=start_date,
            end_date=end_date,
            period_type=PeriodType.YEARLY,
            period_label=f"FY {fiscal_year}" if self.fiscal_year_start_month != 1 else str(target_year),
            fiscal_year=fiscal_year,
            year=target_year,
            is_partial=is_partial,
            confidence=0.95
        )
    
    def _create_range_period(self, range_type: str, original_expr: str, 
                           reference_date: date) -> TimePeriod:
        """Create range-based time period (last N months/quarters/years)"""
        
        # Extract number from expression
        number_match = re.search(r'(\d+)', original_expr)
        if not number_match:
            return self._create_yearly_period('current', reference_date.year, reference_date, original_expr)
        
        count = int(number_match.group(1))
        
        if range_type == 'range_months':
            end_date = reference_date
            start_date = end_date - timedelta(days=count * 30)  # Approximate
            period_label = f"Last {count} months"
            period_type = PeriodType.MONTHLY
            
        elif range_type == 'range_quarters':
            end_date = reference_date
            start_date = end_date - timedelta(days=count * 90)  # Approximate
            period_label = f"Last {count} quarters"
            period_type = PeriodType.QUARTERLY
            
        elif range_type == 'range_years':
            end_date = reference_date
            start_date = end_date - timedelta(days=count * 365)  # Approximate
            period_label = f"Last {count} years"
            period_type = PeriodType.YEARLY
            
        else:
            return self._create_yearly_period('current', reference_date.year, reference_date, original_expr)
        
        return TimePeriod(
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            period_label=period_label,
            year=reference_date.year,
            is_partial=False,
            confidence=0.9
        )
    
    def _parse_date_range(self, time_expr: str, reference_date: date) -> Optional[TimePeriod]:
        """Parse explicit date ranges"""
        
        # Look for date patterns like "2024-01-01 to 2024-03-31"
        date_range_pattern = r'(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})'
        match = re.search(date_range_pattern, time_expr)
        
        if match:
            try:
                start_date = datetime.strptime(match.group(1), '%Y-%m-%d').date()
                end_date = datetime.strptime(match.group(2), '%Y-%m-%d').date()
                
                return TimePeriod(
                    start_date=start_date,
                    end_date=end_date,
                    period_type=PeriodType.CUSTOM,
                    period_label=f"{start_date} to {end_date}",
                    year=start_date.year,
                    is_partial=False,
                    confidence=1.0
                )
            except ValueError:
                pass
        
        return None
    
    def _get_current_quarter(self, reference_date: date) -> int:
        """
        Get current quarter based on fiscal year settings.
        
    Handles edge cases:
    - Validates fiscal_year_start_month is in range (1-12) and raises ValueError if not
    - fiscal_month calculations that underflow or overflow month boundaries
    - Proper modular arithmetic for fiscal year boundary calculations
        """
        month = reference_date.month
        
        # Validate fiscal_year_start_month is in valid range
        if not (1 <= self.fiscal_year_start_month <= 12):
            raise ValueError(f"fiscal_year_start_month must be between 1 and 12, got {self.fiscal_year_start_month}")
        
        # Calculate fiscal month using proper modular arithmetic
        # This handles both negative and > 12 cases correctly
        # In Python, (-3) % 12 yields 9, so months before fiscal_year_start_month are mapped correctly
        fiscal_month = ((month - self.fiscal_year_start_month) % 12) + 1
        
        # Calculate quarter (1-4) from fiscal month (1-12)
        quarter = ((fiscal_month - 1) // 3) + 1
        
        # Ensure quarter is in valid range (defensive programming)
        if not (1 <= quarter <= 4):
            raise ValueError(f"Calculated quarter {quarter} is outside valid range 1-4")
        
        return quarter
    
    def parse_comparison(self, time_expression: str, base_period: TimePeriod) -> Optional[ComparisonPeriod]:
        """Parse comparison expressions and create comparison periods"""
        
        time_expr = time_expression.lower().strip()
        
        # Find comparison type
        comparison_type = None
        for pattern, comp_type in self.comparison_patterns.items():
            if re.search(pattern, time_expr, re.IGNORECASE):
                comparison_type = comp_type
                break
        
        if not comparison_type:
            return None
        
        # Create comparison period based on type
        if comparison_type == 'year_over_year':
            comparison_period = self._create_yoy_comparison(base_period)
        elif comparison_type == 'quarter_over_quarter':
            comparison_period = self._create_qoq_comparison(base_period)
        elif comparison_type == 'month_over_month':
            comparison_period = self._create_mom_comparison(base_period)
        elif comparison_type == 'period_over_period':
            comparison_period = self._create_pop_comparison(base_period)
        else:
            return None
        
        if comparison_period:
            return ComparisonPeriod(
                current_period=base_period,
                comparison_period=comparison_period,
                comparison_type=comparison_type,
                growth_calculation=self._get_growth_calculation(comparison_type)
            )
        
        return None
    
    def _create_yoy_comparison(self, base_period: TimePeriod) -> TimePeriod:
        """Create year-over-year comparison period"""
        start_date = date(base_period.start_date.year - 1, 
                         base_period.start_date.month, 
                         base_period.start_date.day)
        end_date = date(base_period.end_date.year - 1, 
                       base_period.end_date.month, 
                       base_period.end_date.day)
        
        return TimePeriod(
            start_date=start_date,
            end_date=end_date,
            period_type=base_period.period_type,
            period_label=f"{base_period.period_label} (Previous Year)",
            fiscal_year=base_period.fiscal_year - 1 if base_period.fiscal_year else None,
            quarter=base_period.quarter,
            month=base_period.month,
            year=base_period.year - 1 if base_period.year else None,
            is_partial=False,
            confidence=base_period.confidence
        )
    
    def _create_qoq_comparison(self, base_period: TimePeriod) -> TimePeriod:
        """Create quarter-over-quarter comparison period"""
        if base_period.period_type != PeriodType.QUARTERLY:
            # Convert to quarterly if not already
            quarter = self._get_current_quarter(base_period.start_date)
        else:
            quarter = base_period.quarter
        
        if quarter == 1:
            prev_quarter = 4
            year_offset = -1
        else:
            prev_quarter = quarter - 1
            year_offset = 0
        
        # Create previous quarter period
        return self._create_quarterly_period(
            prev_quarter, 
            base_period.year + year_offset, 
            base_period.start_date, 
            f"Q{prev_quarter}"
        )
    
    def _create_mom_comparison(self, base_period: TimePeriod) -> TimePeriod:
        """Create month-over-month comparison period"""
        if base_period.start_date.month == 1:
            prev_month = 12
            year_offset = -1
        else:
            prev_month = base_period.start_date.month - 1
            year_offset = 0
        
        return self._create_monthly_period(
            prev_month,
            base_period.year + year_offset,
            base_period.start_date,
            f"Previous month"
        )
    
    def _create_pop_comparison(self, base_period: TimePeriod) -> TimePeriod:
        """Create period-over-period comparison (same period type, previous instance)"""
        if base_period.period_type == PeriodType.QUARTERLY:
            return self._create_qoq_comparison(base_period)
        elif base_period.period_type == PeriodType.MONTHLY:
            return self._create_mom_comparison(base_period)
        elif base_period.period_type == PeriodType.YEARLY:
            return self._create_yoy_comparison(base_period)
        else:
            # For custom periods, go back by the same duration
            duration = base_period.end_date - base_period.start_date
            start_date = base_period.start_date - duration - timedelta(days=1)
            end_date = base_period.end_date - duration - timedelta(days=1)
            
            return TimePeriod(
                start_date=start_date,
                end_date=end_date,
                period_type=base_period.period_type,
                period_label=f"Previous {base_period.period_label}",
                year=start_date.year,
                is_partial=False,
                confidence=base_period.confidence
            )
    
    def _get_growth_calculation(self, comparison_type: str) -> str:
        """Get SQL formula for growth calculation"""
        formulas = {
            'year_over_year': "((current_value - previous_value) / previous_value) * 100",
            'quarter_over_quarter': "((current_value - previous_value) / previous_value) * 100",
            'month_over_month': "((current_value - previous_value) / previous_value) * 100",
            'period_over_period': "((current_value - previous_value) / previous_value) * 100"
        }
        return formulas.get(comparison_type, "((current_value - previous_value) / previous_value) * 100")
    
    def validate_time_period(self, time_period: TimePeriod) -> Dict[str, Any]:
        """Validate a time period for reasonableness"""
        warnings = []
        errors = []
        
        # Check if dates are in reasonable range
        min_date = date(2000, 1, 1)
        max_date = date(2030, 12, 31)
        
        if time_period.start_date < min_date or time_period.start_date > max_date:
            warnings.append(f"Start date {time_period.start_date} is outside reasonable range")
        
        if time_period.end_date < min_date or time_period.end_date > max_date:
            warnings.append(f"End date {time_period.end_date} is outside reasonable range")
        
        # Check if start date is before end date
        if time_period.start_date > time_period.end_date:
            errors.append("Start date is after end date")
        
        # Check if period is too long
        duration = time_period.end_date - time_period.start_date
        if duration.days > 365 * 5:  # More than 5 years
            warnings.append("Time period is very long (>5 years)")
        
        # Check if period is in the future
        if time_period.start_date > self.current_date:
            warnings.append("Time period is in the future")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "duration_days": duration.days,
            "is_future": time_period.start_date > self.current_date
        }
    
    def get_period_suggestions(self, partial_expression: str) -> List[str]:
        """Get suggestions for partial time expressions"""
        partial = partial_expression.lower().strip()
        suggestions = []
        
        # Common suggestions based on partial input
        if 'q' in partial:
            suggestions.extend(['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024', 'this quarter', 'last quarter'])
        
        if 'month' in partial:
            suggestions.extend(['this month', 'last month', 'last 6 months', 'last 12 months'])
        
        if 'year' in partial:
            suggestions.extend(['this year', 'last year', 'year to date', 'last 2 years'])
        
        if not suggestions:
            # Default suggestions
            suggestions = [
                'this quarter', 'last quarter', 'this year', 'last year',
                'year to date', 'last 6 months', 'Q1 2024', 'Q2 2024'
            ]
        
        return suggestions[:8]  # Return top 8 suggestions