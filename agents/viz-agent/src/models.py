"""
Data models for the Visualization Agent
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum


class ChartType(str, Enum):
    """Supported chart types for financial data visualization"""
    LINE = "line"
    BAR = "bar"
    COLUMN = "column"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    TABLE = "table"
    WATERFALL = "waterfall"
    GAUGE = "gauge"
    CANDLESTICK = "candlestick"


class DataCharacteristics(BaseModel):
    """Analysis of data characteristics for chart type selection"""
    data_type: str = Field(..., description="Type of data (time_series, categorical, numerical)")
    row_count: int = Field(..., description="Number of data rows")
    column_count: int = Field(..., description="Number of data columns")
    has_time_dimension: bool = Field(..., description="Whether data includes time dimension")
    has_categorical_data: bool = Field(..., description="Whether data includes categorical variables")
    has_numerical_data: bool = Field(..., description="Whether data includes numerical variables")
    metric_type: str = Field(..., description="Type of financial metric")
    comparison_type: Optional[str] = Field(None, description="Type of comparison if applicable")


class ChartConfiguration(BaseModel):
    """Configuration for chart generation"""
    chart_type: ChartType = Field(..., description="Selected chart type")
    title: str = Field(..., description="Chart title")
    x_axis_label: str = Field(..., description="X-axis label")
    y_axis_label: str = Field(..., description="Y-axis label")
    color_scheme: str = Field(default="corporate", description="Color scheme to use")
    show_legend: bool = Field(default=True, description="Whether to show legend")
    show_grid: bool = Field(default=True, description="Whether to show grid lines")
    interactive: bool = Field(default=True, description="Whether chart should be interactive")
    height: int = Field(default=400, description="Chart height in pixels")
    width: int = Field(default=600, description="Chart width in pixels")


class InteractiveConfig(BaseModel):
    """Configuration for interactive chart elements"""
    enable_zoom: bool = Field(default=True, description="Enable zoom functionality")
    enable_pan: bool = Field(default=True, description="Enable pan functionality")
    enable_select: bool = Field(default=True, description="Enable data selection")
    enable_hover: bool = Field(default=True, description="Enable hover tooltips")
    enable_crossfilter: bool = Field(default=False, description="Enable crossfilter interactions")
    drill_down_enabled: bool = Field(default=False, description="Enable drill-down functionality")
    drill_down_levels: List[str] = Field(default_factory=list, description="Available drill-down levels")


class ExportFormat(str, Enum):
    """Supported export formats"""
    PNG = "png"
    PDF = "pdf"
    SVG = "svg"
    HTML = "html"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


class ExportConfig(BaseModel):
    """Configuration for chart export"""
    format: ExportFormat = Field(..., description="Export format")
    filename: str = Field(..., description="Output filename")
    width: Optional[int] = Field(None, description="Export width in pixels")
    height: Optional[int] = Field(None, description="Export height in pixels")
    scale: float = Field(default=1.0, description="Export scale factor")
    include_data: bool = Field(default=False, description="Include raw data in export")


class VisualizationData(BaseModel):
    """Processed data ready for visualization"""
    data: List[Dict[str, Any]] = Field(..., description="Chart data")
    columns: List[str] = Field(..., description="Column names")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Data metadata")
    data_characteristics: DataCharacteristics = Field(..., description="Data analysis results")


class ChartSpecification(BaseModel):
    """Complete chart specification"""
    chart_config: ChartConfiguration = Field(..., description="Chart configuration")
    interactive_config: InteractiveConfig = Field(..., description="Interactive features")
    data: VisualizationData = Field(..., description="Chart data")
    styling: Dict[str, Any] = Field(default_factory=dict, description="Custom styling options")


class VisualizationRequest(BaseModel):
    """Request for visualization generation"""
    request_id: str = Field(..., description="Unique request identifier")
    user_id: str = Field(..., description="User making the request")
    query_intent: Dict[str, Any] = Field(..., description="Original query intent")
    data: List[Dict[str, Any]] = Field(..., description="Raw data to visualize")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    export_config: Optional[ExportConfig] = Field(None, description="Export configuration")
    database_context: Optional[Dict[str, Any]] = Field(None, description="Database context information")


class VisualizationResponse(BaseModel):
    """Response from visualization generation"""
    request_id: str = Field(..., description="Request identifier")
    chart_spec: ChartSpecification = Field(..., description="Generated chart specification")
    chart_html: str = Field(..., description="HTML representation of chart")
    chart_json: Dict[str, Any] = Field(..., description="JSON representation of chart")
    export_urls: Dict[str, str] = Field(default_factory=dict, description="Export file URLs")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    success: bool = Field(..., description="Whether generation was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class PerformanceMetrics(BaseModel):
    """Performance metrics for visualization generation"""
    data_processing_time_ms: int = Field(..., description="Data processing time")
    chart_generation_time_ms: int = Field(..., description="Chart generation time")
    export_time_ms: int = Field(default=0, description="Export processing time")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    data_points_count: int = Field(..., description="Number of data points processed")