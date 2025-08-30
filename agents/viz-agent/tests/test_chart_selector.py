"""
Unit tests for chart type selection logic
"""

import pytest
from src.chart_selector import ChartTypeSelector
from src.models import ChartType, DataCharacteristics


class TestChartTypeSelector:
    """Test chart type selection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.selector = ChartTypeSelector()
    
    def test_analyze_time_series_data(self):
        """Test analysis of time series data"""
        data = [
            {"date": "2023-01-01", "revenue": 100000},
            {"date": "2023-02-01", "revenue": 120000},
            {"date": "2023-03-01", "revenue": 110000}
        ]
        
        characteristics = self.selector.analyze_data_characteristics(data)
        
        assert characteristics.has_time_dimension is True
        assert characteristics.has_numerical_data is True
        assert characteristics.data_type == "time_series"
        assert characteristics.row_count == 3
        assert characteristics.column_count == 2
    
    def test_analyze_categorical_data(self):
        """Test analysis of categorical data"""
        data = [
            {"department": "Sales", "budget": 50000},
            {"department": "Marketing", "budget": 30000},
            {"department": "IT", "budget": 40000}
        ]
        
        characteristics = self.selector.analyze_data_characteristics(data)
        
        assert characteristics.has_categorical_data is True
        assert characteristics.has_numerical_data is True
        assert characteristics.data_type == "categorical"
        assert characteristics.row_count == 3
    
    def test_select_chart_type_for_revenue(self):
        """Test chart type selection for revenue data"""
        data = [
            {"month": "Jan", "revenue": 100000},
            {"month": "Feb", "revenue": 120000}
        ]
        
        characteristics = self.selector.analyze_data_characteristics(data)
        chart_type = self.selector.select_chart_type(characteristics)
        
        # Revenue data should typically use line charts
        assert chart_type in [ChartType.LINE, ChartType.BAR, ChartType.COLUMN]
    
    def test_select_chart_type_with_user_preference(self):
        """Test chart type selection with user preferences"""
        data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}]
        characteristics = self.selector.analyze_data_characteristics(data)
        
        preferences = {"preferred_chart_type": "bar"}
        chart_type = self.selector.select_chart_type(characteristics, preferences)
        
        assert chart_type == ChartType.BAR
    
    def test_get_alternative_chart_types(self):
        """Test getting alternative chart types"""
        data = [
            {"date": "2023-01-01", "value": 100},
            {"date": "2023-02-01", "value": 200}
        ]
        
        characteristics = self.selector.analyze_data_characteristics(data)
        alternatives = self.selector.get_alternative_chart_types(characteristics)
        
        assert len(alternatives) > 0
        assert ChartType.LINE in alternatives or ChartType.AREA in alternatives
    
    def test_infer_metric_type_revenue(self):
        """Test metric type inference for revenue data"""
        data = [{"revenue": 100000, "month": "Jan"}]
        characteristics = self.selector.analyze_data_characteristics(data)
        
        assert characteristics.metric_type == "revenue"
    
    def test_infer_metric_type_cash_flow(self):
        """Test metric type inference for cash flow data"""
        data = [{"cash_flow": 50000, "period": "Q1"}]
        characteristics = self.selector.analyze_data_characteristics(data)
        
        assert characteristics.metric_type == "cash_flow"
    
    def test_empty_data_handling(self):
        """Test handling of empty data"""
        with pytest.raises(ValueError):
            self.selector.analyze_data_characteristics([])
    
    def test_large_dataset_handling(self):
        """Test handling of large datasets"""
        # Create large dataset
        data = [{"x": i, "y": i * 2} for i in range(200)]
        characteristics = self.selector.analyze_data_characteristics(data)
        
        assert characteristics.row_count == 200
        alternatives = self.selector.get_alternative_chart_types(characteristics)
        assert ChartType.TABLE in alternatives  # Should suggest table for large data
    
    def test_pie_chart_suitability(self):
        """Test pie chart suitability for small categorical data"""
        data = [
            {"category": "A", "value": 30},
            {"category": "B", "value": 40},
            {"category": "C", "value": 30}
        ]
        
        characteristics = self.selector.analyze_data_characteristics(data)
        alternatives = self.selector.get_alternative_chart_types(characteristics)
        
        # Small categorical data should include pie chart option
        assert ChartType.PIE in alternatives
    
    def test_financial_ratio_detection(self):
        """Test detection of financial ratio data"""
        data = [
            {"ratio_name": "Debt to Equity", "value": 0.5},
            {"ratio_name": "Current Ratio", "value": 1.2}
        ]
        
        characteristics = self.selector.analyze_data_characteristics(data)
        assert characteristics.metric_type == "financial_ratios"
    
    def test_budget_variance_detection(self):
        """Test detection of budget variance data"""
        data = [
            {"department": "Sales", "budget": 100000, "actual": 95000, "variance": -5000}
        ]
        
        characteristics = self.selector.analyze_data_characteristics(data)
        assert characteristics.metric_type == "budget_variance"