"""
Unit tests for performance optimization
"""

import pytest
import time
from src.performance_optimizer import PerformanceOptimizer, PerformanceMonitor
from src.models import ChartType


class TestPerformanceOptimizer:
    """Test performance optimization functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.optimizer = PerformanceOptimizer()
    
    def test_small_dataset_no_optimization(self):
        """Test that small datasets don't get optimized"""
        data = [{"x": i, "y": i * 2} for i in range(100)]  # Small dataset
        
        optimized_data, metrics = self.optimizer.optimize_data_for_visualization(data, ChartType.LINE)
        
        assert len(optimized_data) == len(data)  # No optimization applied
        assert metrics.data_points_count == 100
        assert metrics.data_processing_time_ms > 0
    
    def test_large_dataset_optimization(self):
        """Test optimization of large datasets"""
        data = [{"x": i, "y": i * 2} for i in range(15000)]  # Large dataset
        
        optimized_data, metrics = self.optimizer.optimize_data_for_visualization(data, ChartType.LINE)
        
        assert len(optimized_data) < len(data)  # Optimization applied
        assert len(optimized_data) <= 5000  # Within line chart limits
        assert metrics.data_points_count == len(optimized_data)
        assert metrics.data_processing_time_ms > 0
    
    def test_time_based_sampling(self):
        """Test time-based sampling for time series data"""
        # Create time series data
        import pandas as pd
        dates = pd.date_range('2023-01-01', periods=10000, freq='D')
        data = [{"date": str(date), "value": i} for i, date in enumerate(dates)]
        
        optimized_data, metrics = self.optimizer.optimize_data_for_visualization(data, ChartType.LINE)
        
        assert len(optimized_data) < len(data)
        assert len(optimized_data) <= 5000  # Line chart limit
        
        # Check that dates are still in order
        if len(optimized_data) > 1:
            first_date = optimized_data[0]["date"]
            last_date = optimized_data[-1]["date"]
            assert first_date <= last_date
    
    def test_top_n_sampling_for_bar_chart(self):
        """Test top-N sampling for bar charts"""
        data = [{"category": f"Cat_{i}", "value": i * 10} for i in range(200)]
        
        optimized_data, metrics = self.optimizer.optimize_data_for_visualization(data, ChartType.BAR)
        
        assert len(optimized_data) <= 100  # Bar chart limit
        
        # Check that highest values are preserved
        if len(optimized_data) > 0:
            values = [item["value"] for item in optimized_data]
            assert max(values) == 1990  # Highest value should be preserved
    
    def test_pie_chart_optimization(self):
        """Test optimization for pie charts"""
        data = [{"category": f"Cat_{i}", "value": i} for i in range(50)]
        
        optimized_data, metrics = self.optimizer.optimize_data_for_visualization(data, ChartType.PIE)
        
        assert len(optimized_data) <= 20  # Pie chart limit
    
    def test_table_pagination(self):
        """Test pagination for table data"""
        data = [{"col1": i, "col2": i * 2, "col3": i * 3} for i in range(2000)]
        
        optimized_data, metrics = self.optimizer.optimize_data_for_visualization(data, ChartType.TABLE)
        
        assert len(optimized_data) <= 1000  # Table limit
        
        # Check that first N records are preserved (pagination)
        for i in range(min(10, len(optimized_data))):
            assert optimized_data[i]["col1"] == i
    
    def test_random_sampling_for_scatter(self):
        """Test random sampling for scatter plots"""
        data = [{"x": i, "y": i * 2 + (i % 10)} for i in range(5000)]
        
        optimized_data, metrics = self.optimizer.optimize_data_for_visualization(data, ChartType.SCATTER)
        
        assert len(optimized_data) <= 2000  # Scatter chart limit
        assert len(optimized_data) < len(data)
    
    def test_needs_optimization_logic(self):
        """Test the logic for determining if optimization is needed"""
        # Small dataset - no optimization needed
        small_data = [{"x": i, "y": i} for i in range(100)]
        assert not self.optimizer._needs_optimization(small_data, ChartType.LINE)
        
        # Large dataset - optimization needed
        large_data = [{"x": i, "y": i} for i in range(15000)]
        assert self.optimizer._needs_optimization(large_data, ChartType.LINE)
        
        # Chart-specific limits
        bar_data = [{"x": i, "y": i} for i in range(150)]
        assert self.optimizer._needs_optimization(bar_data, ChartType.BAR)  # Over 100 limit
    
    def test_uniform_sampling(self):
        """Test uniform sampling fallback"""
        data = [{"x": i, "y": i} for i in range(1000)]
        
        sampled_data = self.optimizer._uniform_sampling(data, 100)
        
        assert len(sampled_data) == 100
        assert sampled_data[0]["x"] == 0  # First element
        assert sampled_data[-1]["x"] == 990  # Last element (approximately)
    
    def test_optimize_chart_rendering_recommendations(self):
        """Test chart rendering optimization recommendations"""
        # Test WebGL recommendation for large scatter plots
        recommendations = self.optimizer.optimize_chart_rendering(ChartType.SCATTER, 2000)
        assert recommendations["use_webgl"] is True
        
        # Test marker reduction for large line charts
        recommendations = self.optimizer.optimize_chart_rendering(ChartType.LINE, 3000)
        assert recommendations["reduce_markers"] is True
        assert recommendations["simplify_lines"] is True
        
        # Test aggregation for very large datasets
        recommendations = self.optimizer.optimize_chart_rendering(ChartType.BAR, 60000)
        assert recommendations["use_aggregation"] is True
        assert recommendations["enable_streaming"] is True
    
    def test_memory_estimation(self):
        """Test memory usage estimation"""
        data = [{"x": i, "y": i * 2} for i in range(1000)]
        
        memory_mb = self.optimizer._estimate_memory_usage(data)
        
        assert memory_mb > 0
        assert isinstance(memory_mb, float)
    
    def test_find_date_column(self):
        """Test date column detection"""
        import pandas as pd
        
        # DataFrame with datetime column
        df_with_datetime = pd.DataFrame({
            "date": pd.date_range('2023-01-01', periods=10),
            "value": range(10)
        })
        
        date_col = self.optimizer._find_date_column(df_with_datetime)
        assert date_col == "date"
        
        # DataFrame with date-like column name
        df_with_date_name = pd.DataFrame({
            "transaction_date": ["2023-01-01", "2023-01-02"],
            "amount": [100, 200]
        })
        
        date_col = self.optimizer._find_date_column(df_with_date_name)
        assert date_col == "transaction_date"
        
        # DataFrame without date columns
        df_no_date = pd.DataFrame({
            "category": ["A", "B"],
            "value": [1, 2]
        })
        
        date_col = self.optimizer._find_date_column(df_no_date)
        assert date_col is None
    
    def test_empty_data_handling(self):
        """Test handling of empty data"""
        optimized_data, metrics = self.optimizer.optimize_data_for_visualization([], ChartType.LINE)
        
        assert len(optimized_data) == 0
        assert metrics.data_points_count == 0


class TestPerformanceMonitor:
    """Test performance monitoring functionality"""
    
    def test_performance_monitor_context_manager(self):
        """Test performance monitor as context manager"""
        with PerformanceMonitor("test_operation") as monitor:
            time.sleep(0.01)  # Small delay
        
        metrics = monitor.get_metrics()
        
        assert "duration_ms" in metrics
        assert "memory_delta_mb" in metrics
        assert metrics["duration_ms"] > 0
    
    def test_performance_monitor_metrics(self):
        """Test performance metrics collection"""
        monitor = PerformanceMonitor("test_operation")
        
        with monitor:
            # Simulate some work
            data = [i for i in range(1000)]
            sum(data)
        
        metrics = monitor.get_metrics()
        
        assert isinstance(metrics["duration_ms"], float)
        assert isinstance(metrics["memory_delta_mb"], float)
        assert isinstance(metrics["start_memory_mb"], float)
        assert isinstance(metrics["end_memory_mb"], float)
    
    def test_performance_monitor_without_context(self):
        """Test performance monitor without using context manager"""
        monitor = PerformanceMonitor("test_operation")
        
        metrics = monitor.get_metrics()
        
        assert metrics == {}  # Should be empty if not used as context manager