"""
Chart type selection logic based on financial data characteristics
"""

import logging
from typing import Dict, List, Any, Optional
from .models import ChartType, DataCharacteristics, VisualizationData

logger = logging.getLogger(__name__)


class ChartTypeSelector:
    """Intelligent chart type selection based on data characteristics"""
    
    def __init__(self):
        self.financial_metric_mappings = {
            # Time series metrics - best with line charts
            "revenue": ChartType.LINE,
            "cash_flow": ChartType.LINE,
            "profit": ChartType.LINE,
            "expenses": ChartType.LINE,
            "growth_rate": ChartType.LINE,
            
            # Comparative metrics - best with bar charts
            "budget_variance": ChartType.BAR,
            "department_spending": ChartType.BAR,
            "quarterly_comparison": ChartType.BAR,
            "regional_performance": ChartType.BAR,
            
            # Composition metrics - best with pie charts
            "expense_breakdown": ChartType.PIE,
            "revenue_by_segment": ChartType.PIE,
            "asset_allocation": ChartType.PIE,
            
            # Ratio and performance metrics - best with gauge or bar
            "financial_ratios": ChartType.GAUGE,
            "kpi_dashboard": ChartType.GAUGE,
            "performance_indicators": ChartType.BAR,
            
            # Investment and portfolio data - specialized charts
            "stock_performance": ChartType.CANDLESTICK,
            "portfolio_returns": ChartType.AREA,
            "investment_correlation": ChartType.HEATMAP,
            
            # Detailed data - tables
            "transaction_details": ChartType.TABLE,
            "financial_statements": ChartType.TABLE,
        }
        
        self.data_type_rules = {
            "time_series": [ChartType.LINE, ChartType.AREA, ChartType.BAR],
            "categorical": [ChartType.BAR, ChartType.PIE, ChartType.COLUMN],
            "numerical": [ChartType.SCATTER, ChartType.HEATMAP, ChartType.BAR],
            "comparison": [ChartType.BAR, ChartType.COLUMN, ChartType.WATERFALL],
            "composition": [ChartType.PIE, ChartType.AREA],
            "correlation": [ChartType.HEATMAP, ChartType.SCATTER],
            "detailed": [ChartType.TABLE]
        }
    
    def analyze_data_characteristics(self, data: List[Dict[str, Any]]) -> DataCharacteristics:
        """Analyze data to determine its characteristics"""
        if not data:
            raise ValueError("Cannot analyze empty data")
        
        row_count = len(data)
        columns = list(data[0].keys()) if data else []
        column_count = len(columns)
        
        # Analyze column types
        has_time_dimension = self._has_time_columns(columns, data[0])
        has_categorical_data = self._has_categorical_columns(data)
        has_numerical_data = self._has_numerical_columns(data)
        
        # Determine data type
        data_type = self._determine_data_type(
            has_time_dimension, has_categorical_data, has_numerical_data, columns
        )
        
        # Infer metric type from column names and data patterns
        metric_type = self._infer_metric_type(columns, data)
        
        # Determine comparison type if applicable
        comparison_type = self._determine_comparison_type(columns, data)
        
        return DataCharacteristics(
            data_type=data_type,
            row_count=row_count,
            column_count=column_count,
            has_time_dimension=has_time_dimension,
            has_categorical_data=has_categorical_data,
            has_numerical_data=has_numerical_data,
            metric_type=metric_type,
            comparison_type=comparison_type
        )
    
    def select_chart_type(self, data_characteristics: DataCharacteristics, 
                         user_preferences: Optional[Dict[str, Any]] = None) -> ChartType:
        """Select the most appropriate chart type based on data characteristics"""
        
        # Check user preferences first
        if user_preferences and "preferred_chart_type" in user_preferences:
            preferred_type = user_preferences["preferred_chart_type"]
            if self._is_chart_type_suitable(preferred_type, data_characteristics):
                logger.info(f"Using user preferred chart type: {preferred_type}")
                return ChartType(preferred_type)
        
        # Use financial metric mapping if available
        if data_characteristics.metric_type in self.financial_metric_mappings:
            chart_type = self.financial_metric_mappings[data_characteristics.metric_type]
            logger.info(f"Selected chart type {chart_type} based on metric type {data_characteristics.metric_type}")
            return chart_type
        
        # Use data type rules
        suitable_types = self.data_type_rules.get(data_characteristics.data_type, [])
        
        if not suitable_types:
            # Fallback logic based on data characteristics
            chart_type = self._fallback_chart_selection(data_characteristics)
        else:
            # Select best chart type from suitable options
            chart_type = self._select_best_from_suitable(suitable_types, data_characteristics)
        
        logger.info(f"Selected chart type: {chart_type} for data type: {data_characteristics.data_type}")
        return chart_type
    
    def get_alternative_chart_types(self, data_characteristics: DataCharacteristics) -> List[ChartType]:
        """Get alternative chart types that would work for the given data"""
        suitable_types = self.data_type_rules.get(data_characteristics.data_type, [])
        
        # Add additional suitable types based on specific characteristics
        if data_characteristics.has_time_dimension:
            suitable_types.extend([ChartType.LINE, ChartType.AREA])
        
        if data_characteristics.has_categorical_data and data_characteristics.row_count <= 10:
            suitable_types.append(ChartType.PIE)
        
        if data_characteristics.row_count > 100:
            suitable_types.append(ChartType.TABLE)
        
        # Remove duplicates and return
        return list(set(suitable_types))
    
    def _has_time_columns(self, columns: List[str], sample_row: Dict[str, Any]) -> bool:
        """Check if data has time-related columns"""
        time_keywords = ['date', 'time', 'period', 'month', 'year', 'quarter', 'day']
        
        for col in columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in time_keywords):
                return True
            
            # Check if the value looks like a date
            value = sample_row.get(col)
            if isinstance(value, str) and self._looks_like_date(value):
                return True
        
        return False
    
    def _has_categorical_columns(self, data: List[Dict[str, Any]]) -> bool:
        """Check if data has categorical columns"""
        if not data:
            return False
        
        sample_size = min(10, len(data))
        sample_data = data[:sample_size]
        
        for col in data[0].keys():
            values = [row.get(col) for row in sample_data if row.get(col) is not None]
            if values and all(isinstance(v, str) for v in values):
                # For small datasets (<=5 rows), any string column is categorical
                # For larger datasets, check uniqueness ratio
                if len(data) <= 5:
                    return True
                unique_values = set(values)
                if len(unique_values) < len(values) * 0.8:  # Less than 80% unique values
                    return True
        
        return False
    
    def _has_numerical_columns(self, data: List[Dict[str, Any]]) -> bool:
        """Check if data has numerical columns"""
        if not data:
            return False
        
        for col in data[0].keys():
            value = data[0].get(col)
            if isinstance(value, (int, float)):
                return True
            if isinstance(value, str) and self._is_numeric_string(value):
                return True
        
        return False
    
    def _determine_data_type(self, has_time: bool, has_categorical: bool, 
                           has_numerical: bool, columns: List[str]) -> str:
        """Determine the primary data type"""
        if has_time and has_numerical:
            return "time_series"
        elif has_categorical and has_numerical:
            return "categorical"
        elif has_numerical and len(columns) >= 2:
            return "numerical"
        elif "comparison" in " ".join(columns).lower():
            return "comparison"
        elif any(word in " ".join(columns).lower() for word in ["breakdown", "composition", "allocation"]):
            return "composition"
        else:
            return "detailed"
    
    def _infer_metric_type(self, columns: List[str], data: List[Dict[str, Any]]) -> str:
        """Infer the type of financial metric from column names and data"""
        column_text = " ".join(columns).lower()
        
        # Financial metric keywords
        metric_keywords = {
            "revenue": ["revenue", "sales", "income", "turnover"],
            "cash_flow": ["cash", "flow", "liquidity"],
            "profit": ["profit", "margin", "earnings", "net_income"],
            "expenses": ["expense", "cost", "spending", "expenditure"],
            "budget_variance": ["budget", "variance", "actual", "forecast"],
            "financial_ratios": ["ratio", "debt_to_equity", "current_ratio", "quick_ratio"],
            "investment": ["investment", "portfolio", "roi", "return"],
            "kpi": ["kpi", "indicator", "performance", "metric"]
        }
        
        for metric_type, keywords in metric_keywords.items():
            if any(keyword in column_text for keyword in keywords):
                return metric_type
        
        return "general"
    
    def _determine_comparison_type(self, columns: List[str], data: List[Dict[str, Any]]) -> Optional[str]:
        """Determine if this is a comparison and what type"""
        column_text = " ".join(columns).lower()
        
        if any(word in column_text for word in ["vs", "versus", "compared", "comparison"]):
            return "direct_comparison"
        elif any(word in column_text for word in ["previous", "last", "prior", "yoy", "mom"]):
            return "period_comparison"
        elif any(word in column_text for word in ["budget", "forecast", "target", "actual"]):
            return "budget_comparison"
        
        return None
    
    def _is_chart_type_suitable(self, chart_type: str, data_characteristics: DataCharacteristics) -> bool:
        """Check if a chart type is suitable for the given data characteristics"""
        try:
            chart_enum = ChartType(chart_type)
            suitable_types = self.get_alternative_chart_types(data_characteristics)
            return chart_enum in suitable_types
        except ValueError:
            return False
    
    def _fallback_chart_selection(self, data_characteristics: DataCharacteristics) -> ChartType:
        """Fallback chart selection when no specific rules apply"""
        if data_characteristics.row_count > 50:
            return ChartType.TABLE
        elif data_characteristics.has_time_dimension:
            return ChartType.LINE
        elif data_characteristics.has_categorical_data:
            return ChartType.BAR
        else:
            return ChartType.TABLE
    
    def _select_best_from_suitable(self, suitable_types: List[ChartType], 
                                  data_characteristics: DataCharacteristics) -> ChartType:
        """Select the best chart type from suitable options"""
        # Priority rules based on data characteristics
        if data_characteristics.row_count > 100 and ChartType.TABLE in suitable_types:
            return ChartType.TABLE
        
        if data_characteristics.has_time_dimension and ChartType.LINE in suitable_types:
            return ChartType.LINE
        
        if (data_characteristics.has_categorical_data and 
            data_characteristics.row_count <= 8 and 
            ChartType.PIE in suitable_types):
            return ChartType.PIE
        
        # Return first suitable type as default
        return suitable_types[0] if suitable_types else ChartType.BAR
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if a string value looks like a date"""
        date_patterns = ['-', '/', ':', 'T', 'Z']
        return any(pattern in value for pattern in date_patterns) and len(value) >= 8
    
    def _is_numeric_string(self, value: str) -> bool:
        """Check if a string represents a numeric value"""
        try:
            float(value.replace(',', '').replace('$', '').replace('%', ''))
            return True
        except ValueError:
            return False