"""
Unit tests for chart generation and CFO styling
"""

import pytest
import plotly.graph_objects as go
import pandas as pd
from src.chart_generator import ChartGenerator, CFOChartStyler
from src.models import ChartType, ChartConfiguration, InteractiveConfig, VisualizationData, ChartSpecification, DataCharacteristics


class TestCFOChartStyler:
    """Test CFO-specific styling functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.styler = CFOChartStyler()
    
    def test_get_corporate_color_scheme(self):
        """Test corporate color scheme retrieval"""
        scheme = self.styler.get_color_scheme("corporate")
        
        assert "primary" in scheme
        assert "secondary" in scheme
        assert "colors" in scheme
        assert len(scheme["colors"]) >= 7
    
    def test_get_financial_color_scheme(self):
        """Test financial color scheme retrieval"""
        scheme = self.styler.get_color_scheme("financial")
        
        assert scheme["primary"] == "#2E86AB"
        assert len(scheme["colors"]) >= 7
    
    def test_apply_cfo_styling(self):
        """Test application of CFO styling to a figure"""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 4, 2], name="Test"))
        
        config = ChartConfiguration(
            chart_type=ChartType.LINE,
            title="Test Chart",
            x_axis_label="X Axis",
            y_axis_label="Y Axis",
            color_scheme="corporate"
        )
        
        styled_fig = self.styler.apply_cfo_styling(fig, config)
        
        assert styled_fig.layout.title.text == "Test Chart"
        assert styled_fig.layout.xaxis.title.text == "X Axis"
        assert styled_fig.layout.yaxis.title.text == "Y Axis"
        assert styled_fig.layout.font.family == "Arial, sans-serif"


class TestChartGenerator:
    """Test chart generation functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.generator = ChartGenerator()
    
    def create_sample_chart_spec(self, chart_type: ChartType, data: list) -> ChartSpecification:
        """Create a sample chart specification for testing"""
        data_characteristics = DataCharacteristics(
            data_type="time_series",
            row_count=len(data),
            column_count=len(data[0].keys()) if data else 0,
            has_time_dimension=True,
            has_categorical_data=False,
            has_numerical_data=True,
            metric_type="revenue"
        )
        
        viz_data = VisualizationData(
            data=data,
            columns=list(data[0].keys()) if data else [],
            data_characteristics=data_characteristics
        )
        
        chart_config = ChartConfiguration(
            chart_type=chart_type,
            title="Test Chart",
            x_axis_label="Date",
            y_axis_label="Revenue"
        )
        
        interactive_config = InteractiveConfig()
        
        return ChartSpecification(
            chart_config=chart_config,
            interactive_config=interactive_config,
            data=viz_data
        )
    
    def test_generate_line_chart(self):
        """Test line chart generation"""
        data = [
            {"date": "2023-01-01", "revenue": 100000},
            {"date": "2023-02-01", "revenue": 120000},
            {"date": "2023-03-01", "revenue": 110000}
        ]
        
        chart_spec = self.create_sample_chart_spec(ChartType.LINE, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "scatter"
        assert "lines" in str(fig.data[0].mode)
        assert metadata["chart_type"] == "line"
        assert metadata["data_points"] == 3
    
    def test_generate_bar_chart(self):
        """Test bar chart generation"""
        data = [
            {"department": "Sales", "budget": 100000},
            {"department": "Marketing", "budget": 80000},
            {"department": "IT", "budget": 60000}
        ]
        
        chart_spec = self.create_sample_chart_spec(ChartType.BAR, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "bar"
        assert fig.data[0].orientation == "h"
    
    def test_generate_pie_chart(self):
        """Test pie chart generation"""
        data = [
            {"category": "Product A", "sales": 300000},
            {"category": "Product B", "sales": 200000},
            {"category": "Product C", "sales": 100000}
        ]
        
        chart_spec = self.create_sample_chart_spec(ChartType.PIE, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "pie"
        assert fig.data[0].hole == 0.3  # Donut style
    
    def test_generate_table(self):
        """Test table generation"""
        data = [
            {"account": "Cash", "balance": 50000},
            {"account": "Receivables", "balance": 30000},
            {"account": "Inventory", "balance": 20000}
        ]
        
        chart_spec = self.create_sample_chart_spec(ChartType.TABLE, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "table"
    
    def test_generate_gauge_chart(self):
        """Test gauge chart generation"""
        data = [{"kpi": "Revenue Growth", "value": 15.5}]
        
        chart_spec = self.create_sample_chart_spec(ChartType.GAUGE, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "indicator"
        assert "gauge" in fig.data[0].mode
    
    def test_generate_waterfall_chart(self):
        """Test waterfall chart generation"""
        data = [
            {"category": "Starting Revenue", "value": 100000},
            {"category": "New Sales", "value": 20000},
            {"category": "Returns", "value": -5000},
            {"category": "Ending Revenue", "value": 115000}
        ]
        
        chart_spec = self.create_sample_chart_spec(ChartType.WATERFALL, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "waterfall"
    
    def test_generate_area_chart(self):
        """Test area chart generation"""
        data = [
            {"month": "Jan", "cumulative_revenue": 100000},
            {"month": "Feb", "cumulative_revenue": 220000},
            {"month": "Mar", "cumulative_revenue": 330000}
        ]
        
        chart_spec = self.create_sample_chart_spec(ChartType.AREA, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "scatter"
        assert fig.data[0].fill is not None
    
    def test_generate_scatter_chart(self):
        """Test scatter chart generation"""
        data = [
            {"marketing_spend": 10000, "revenue": 100000},
            {"marketing_spend": 15000, "revenue": 150000},
            {"marketing_spend": 20000, "revenue": 180000}
        ]
        
        chart_spec = self.create_sample_chart_spec(ChartType.SCATTER, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "scatter"
        assert fig.data[0].mode == "markers"
    
    def test_generate_heatmap(self):
        """Test heatmap generation"""
        data = [
            {"product": "A", "region": "North", "sales": 100},
            {"product": "A", "region": "South", "sales": 150},
            {"product": "B", "region": "North", "sales": 120},
            {"product": "B", "region": "South", "sales": 180}
        ]
        
        chart_spec = self.create_sample_chart_spec(ChartType.HEATMAP, data)
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "heatmap"
    
    def test_unsupported_chart_type(self):
        """Test handling of unsupported chart types"""
        data = [{"x": 1, "y": 2}]
        
        # Create chart spec with invalid chart type
        chart_spec = self.create_sample_chart_spec(ChartType.LINE, data)
        chart_spec.chart_config.chart_type = "invalid_type"
        
        with pytest.raises(ValueError):
            self.generator.generate_chart(chart_spec)
    
    def test_empty_data_handling(self):
        """Test handling of empty data"""
        chart_spec = self.create_sample_chart_spec(ChartType.LINE, [])
        
        # Should handle empty data gracefully
        fig, metadata = self.generator.generate_chart(chart_spec)
        assert isinstance(fig, go.Figure)
    
    def test_chart_metadata_generation(self):
        """Test chart metadata generation"""
        data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}]
        chart_spec = self.create_sample_chart_spec(ChartType.LINE, data)
        
        fig, metadata = self.generator.generate_chart(chart_spec)
        
        assert "chart_type" in metadata
        assert "data_points" in metadata
        assert "traces" in metadata
        assert "interactive_features" in metadata
        assert "styling" in metadata
        
        assert metadata["data_points"] == 2
        assert metadata["chart_type"] == "line"