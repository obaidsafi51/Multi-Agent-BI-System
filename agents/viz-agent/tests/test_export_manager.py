"""
Unit tests for export functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
import plotly.graph_objects as go
from src.export_manager import ExportManager
from src.models import ExportFormat, ExportConfig


class TestExportManager:
    """Test export functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create temporary directory for exports
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = ExportManager(export_directory=self.temp_dir)
        
        # Create sample figure
        self.sample_fig = go.Figure()
        self.sample_fig.add_trace(go.Scatter(
            x=[1, 2, 3, 4],
            y=[10, 11, 12, 13],
            name="Sample Data"
        ))
        self.sample_fig.update_layout(title="Sample Chart")
        
        # Sample data
        self.sample_data = [
            {"x": 1, "y": 10},
            {"x": 2, "y": 11},
            {"x": 3, "y": 12},
            {"x": 4, "y": 13}
        ]
    
    def teardown_method(self):
        """Clean up test fixtures"""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_export_png(self):
        """Test PNG export functionality"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            filename="test_chart.png",
            width=800,
            height=600
        )
        
        result = self.export_manager.export_chart(self.sample_fig, config)
        
        assert result["success"] is True
        assert result["format"] == "png"
        assert result["filename"] == "test_chart.png"
        assert Path(result["filepath"]).exists()
        assert result["file_size"] > 0
        assert result["dimensions"]["width"] == 800
        assert result["dimensions"]["height"] == 600
    
    def test_export_html(self):
        """Test HTML export functionality"""
        config = ExportConfig(
            format=ExportFormat.HTML,
            filename="test_chart.html"
        )
        
        result = self.export_manager.export_chart(self.sample_fig, config)
        
        assert result["success"] is True
        assert result["format"] == "html"
        assert result["interactive"] is True
        assert Path(result["filepath"]).exists()
        
        # Check that HTML file contains expected content
        with open(result["filepath"], 'r') as f:
            content = f.read()
            assert "plotly" in content.lower()
            assert "sample chart" in content.lower()
    
    def test_export_csv(self):
        """Test CSV export functionality"""
        config = ExportConfig(
            format=ExportFormat.CSV,
            filename="test_data.csv"
        )
        
        result = self.export_manager.export_chart(self.sample_fig, config, self.sample_data)
        
        assert result["success"] is True
        assert result["format"] == "csv"
        assert result["row_count"] == 4
        assert result["column_count"] == 2
        assert Path(result["filepath"]).exists()
        
        # Check CSV content
        import pandas as pd
        df = pd.read_csv(result["filepath"])
        assert len(df) == 4
        assert "x" in df.columns
        assert "y" in df.columns
    
    def test_export_json(self):
        """Test JSON export functionality"""
        config = ExportConfig(
            format=ExportFormat.JSON,
            filename="test_chart.json"
        )
        
        result = self.export_manager.export_chart(self.sample_fig, config, self.sample_data)
        
        assert result["success"] is True
        assert result["format"] == "json"
        assert result["includes_chart_config"] is True
        assert result["includes_data"] is True
        assert Path(result["filepath"]).exists()
        
        # Check JSON content
        import json
        with open(result["filepath"], 'r') as f:
            data = json.load(f)
            assert "chart_config" in data
            assert "data" in data
            assert "metadata" in data
            assert len(data["data"]) == 4
    
    def test_export_csv_without_data(self):
        """Test CSV export without data should raise error"""
        config = ExportConfig(
            format=ExportFormat.CSV,
            filename="test_no_data.csv"
        )
        
        with pytest.raises(ValueError, match="No data provided for CSV export"):
            self.export_manager.export_chart(self.sample_fig, config)
    
    def test_export_multiple_formats(self):
        """Test exporting in multiple formats"""
        formats = [ExportFormat.PNG, ExportFormat.HTML, ExportFormat.CSV]
        base_filename = "multi_export_test"
        
        results = self.export_manager.export_multiple_formats(
            self.sample_fig, formats, base_filename, self.sample_data
        )
        
        assert len(results) == 3
        assert "png" in results
        assert "html" in results
        assert "csv" in results
        
        for format_name, result in results.items():
            if "error" not in result:
                assert result["success"] is True
                assert Path(result["filepath"]).exists()
    
    def test_filename_extension_handling(self):
        """Test automatic filename extension handling"""
        config = ExportConfig(
            format=ExportFormat.PNG,
            filename="test_chart"  # No extension
        )
        
        result = self.export_manager.export_chart(self.sample_fig, config)
        
        assert result["filename"] == "test_chart.png"
        assert result["filepath"].endswith(".png")
    
    def test_get_export_url(self):
        """Test export URL generation"""
        filename = "test_chart.png"
        url = self.export_manager.get_export_url(filename)
        
        assert url == f"/exports/{filename}"
    
    def test_get_export_info(self):
        """Test getting export file information"""
        # First create an export
        config = ExportConfig(
            format=ExportFormat.PNG,
            filename="info_test.png"
        )
        
        result = self.export_manager.export_chart(self.sample_fig, config)
        
        # Then get info about it
        info = self.export_manager.get_export_info("info_test.png")
        
        assert "error" not in info
        assert info["filename"] == "info_test.png"
        assert info["file_size"] > 0
        assert info["format"] == "png"
    
    def test_get_export_info_nonexistent_file(self):
        """Test getting info for non-existent file"""
        info = self.export_manager.get_export_info("nonexistent.png")
        
        assert "error" in info
        assert info["error"] == "File not found"
    
    def test_cleanup_old_exports(self):
        """Test cleanup of old export files"""
        # Create some test files
        test_files = ["old1.png", "old2.html", "old3.csv"]
        
        for filename in test_files:
            filepath = Path(self.temp_dir) / filename
            filepath.write_text("test content")
            
            # Modify file time to make it appear old
            old_time = os.path.getmtime(filepath) - 25 * 3600  # 25 hours ago
            os.utime(filepath, (old_time, old_time))
        
        # Run cleanup
        cleaned_count = self.export_manager.cleanup_old_exports(max_age_hours=24)
        
        assert cleaned_count == 3
        
        # Check that files were deleted
        for filename in test_files:
            filepath = Path(self.temp_dir) / filename
            assert not filepath.exists()
    
    def test_unsupported_export_format(self):
        """Test handling of unsupported export format"""
        # This would require modifying the ExportConfig to accept invalid format
        # For now, test with a mock invalid format
        config = ExportConfig(
            format=ExportFormat.PNG,  # Valid format
            filename="test.png"
        )
        
        # Temporarily modify the format to invalid
        config.format = "invalid_format"
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            self.export_manager.export_chart(self.sample_fig, config)
    
    def test_detect_chart_type(self):
        """Test chart type detection"""
        # Test line chart detection
        line_fig = go.Figure()
        line_fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3], mode='lines'))
        chart_type = self.export_manager._detect_chart_type(line_fig)
        assert chart_type == "line"
        
        # Test bar chart detection
        bar_fig = go.Figure()
        bar_fig.add_trace(go.Bar(x=[1, 2, 3], y=[1, 2, 3]))
        chart_type = self.export_manager._detect_chart_type(bar_fig)
        assert chart_type == "bar"
        
        # Test pie chart detection
        pie_fig = go.Figure()
        pie_fig.add_trace(go.Pie(labels=['A', 'B', 'C'], values=[1, 2, 3]))
        chart_type = self.export_manager._detect_chart_type(pie_fig)
        assert chart_type == "pie"
        
        # Test empty figure
        empty_fig = go.Figure()
        chart_type = self.export_manager._detect_chart_type(empty_fig)
        assert chart_type == "unknown"