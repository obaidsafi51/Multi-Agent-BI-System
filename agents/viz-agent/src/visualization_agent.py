"""
Main Visualization Agent implementation
"""

import logging
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
from .models import (
    VisualizationRequest, VisualizationResponse, ChartSpecification,
    ChartConfiguration, InteractiveConfig, VisualizationData,
    ExportConfig, PerformanceMetrics
)
from .chart_selector import ChartTypeSelector
from .chart_generator import ChartGenerator
from .interactive_features import InteractiveFeatureManager
from .export_manager import ExportManager
from .performance_optimizer import PerformanceOptimizer

logger = logging.getLogger(__name__)


class VisualizationAgent:
    """Main visualization agent that orchestrates chart generation"""
    
    def __init__(self):
        self.chart_selector = ChartTypeSelector()
        self.chart_generator = ChartGenerator()
        self.interactive_manager = InteractiveFeatureManager()
        self.export_manager = ExportManager()
        self.performance_optimizer = PerformanceOptimizer()
        
        # Cache for generated charts
        self.chart_cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def process_visualization_request(self, request: VisualizationRequest) -> VisualizationResponse:
        """Process a visualization request and generate chart"""
        start_time = time.time()
        
        try:
            logger.info(f"Processing visualization request {request.request_id} for user {request.user_id}")
            
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                logger.info(f"Returning cached response for request {request.request_id}")
                return cached_response
            
            # Analyze data characteristics
            data_characteristics = self.chart_selector.analyze_data_characteristics(request.data)
            
            # Optimize data for visualization
            optimized_data, perf_metrics = self.performance_optimizer.optimize_data_for_visualization(
                request.data, 
                self.chart_selector.select_chart_type(data_characteristics, request.preferences)
            )
            
            # Create visualization data object
            viz_data = VisualizationData(
                data=optimized_data,
                columns=list(optimized_data[0].keys()) if optimized_data else [],
                data_characteristics=data_characteristics
            )
            
            # Select appropriate chart type
            chart_type = self.chart_selector.select_chart_type(data_characteristics, request.preferences)
            
            # Create chart configuration
            chart_config = self._create_chart_configuration(
                chart_type, request.query_intent, request.preferences
            )
            
            # Create interactive configuration
            interactive_config = self._create_interactive_configuration(request.preferences)
            
            # Create chart specification
            chart_spec = ChartSpecification(
                chart_config=chart_config,
                interactive_config=interactive_config,
                data=viz_data
            )
            
            # Generate chart
            fig, chart_metadata = self.chart_generator.generate_chart(chart_spec)
            
            # Apply interactive features
            fig = self.interactive_manager.configure_interactivity(
                fig, interactive_config, chart_type
            )
            
            # Update performance metrics
            perf_metrics.chart_generation_time_ms = int((time.time() - start_time) * 1000) - perf_metrics.data_processing_time_ms
            
            # Handle export if requested
            export_urls = {}
            if request.export_config:
                export_result = self.export_manager.export_chart(fig, request.export_config, optimized_data)
                export_urls[request.export_config.format.value] = self.export_manager.get_export_url(
                    export_result["filename"]
                )
                perf_metrics.export_time_ms = export_result.get("processing_time_ms", 0)
            
            # Create response
            response = VisualizationResponse(
                request_id=request.request_id,
                chart_spec=chart_spec,
                chart_html=fig.to_html(include_plotlyjs=True, div_id=f"chart-{request.request_id}"),
                chart_json=fig.to_dict(),
                export_urls=export_urls,
                processing_time_ms=int((time.time() - start_time) * 1000),
                success=True
            )
            
            # Cache the response
            self._cache_response(cache_key, response)
            
            logger.info(f"Successfully processed visualization request {request.request_id} "
                       f"in {response.processing_time_ms}ms")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing visualization request {request.request_id}: {str(e)}")
            
            return VisualizationResponse(
                request_id=request.request_id,
                chart_spec=None,
                chart_html="",
                chart_json={},
                export_urls={},
                processing_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e)
            )
    
    def _create_chart_configuration(self, chart_type, query_intent: Dict[str, Any], 
                                  preferences: Dict[str, Any]) -> ChartConfiguration:
        """Create chart configuration based on query intent and preferences"""
        
        # Extract title from query intent
        title = query_intent.get("title", "Financial Chart")
        if "metric_type" in query_intent:
            title = f"{query_intent['metric_type'].replace('_', ' ').title()}"
            if "time_period" in query_intent:
                title += f" - {query_intent['time_period']}"
        
        # Determine axis labels
        x_axis_label = query_intent.get("x_axis", "Period")
        y_axis_label = query_intent.get("y_axis", "Value")
        
        # Get user preferences
        color_scheme = preferences.get("color_scheme", "corporate")
        chart_height = preferences.get("chart_height", 400)
        chart_width = preferences.get("chart_width", 600)
        
        return ChartConfiguration(
            chart_type=chart_type,
            title=title,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            color_scheme=color_scheme,
            show_legend=preferences.get("show_legend", True),
            show_grid=preferences.get("show_grid", True),
            interactive=preferences.get("interactive", True),
            height=chart_height,
            width=chart_width
        )
    
    def _create_interactive_configuration(self, preferences: Dict[str, Any]) -> InteractiveConfig:
        """Create interactive configuration based on user preferences"""
        return InteractiveConfig(
            enable_zoom=preferences.get("enable_zoom", True),
            enable_pan=preferences.get("enable_pan", True),
            enable_select=preferences.get("enable_select", True),
            enable_hover=preferences.get("enable_hover", True),
            enable_crossfilter=preferences.get("enable_crossfilter", False),
            drill_down_enabled=preferences.get("drill_down_enabled", False),
            drill_down_levels=preferences.get("drill_down_levels", [])
        )
    
    def _generate_cache_key(self, request: VisualizationRequest) -> str:
        """Generate cache key for the request"""
        # Create a hash of the request data for caching
        import hashlib
        
        cache_data = {
            "user_id": request.user_id,
            "query_intent": request.query_intent,
            "data_hash": hashlib.md5(json.dumps(request.data, sort_keys=True).encode()).hexdigest(),
            "preferences": request.preferences
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[VisualizationResponse]:
        """Get cached response if available and not expired"""
        if cache_key not in self.chart_cache:
            return None
        
        cached_item = self.chart_cache[cache_key]
        if time.time() - cached_item["timestamp"] > self.cache_ttl:
            del self.chart_cache[cache_key]
            return None
        
        return cached_item["response"]
    
    def _cache_response(self, cache_key: str, response: VisualizationResponse):
        """Cache the response"""
        self.chart_cache[cache_key] = {
            "response": response,
            "timestamp": time.time()
        }
        
        # Clean up old cache entries
        self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.chart_cache.items()
            if current_time - value["timestamp"] > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.chart_cache[key]
    
    async def get_chart_alternatives(self, request: VisualizationRequest) -> List[Dict[str, Any]]:
        """Get alternative chart types for the given data"""
        try:
            data_characteristics = self.chart_selector.analyze_data_characteristics(request.data)
            alternative_types = self.chart_selector.get_alternative_chart_types(data_characteristics)
            
            alternatives = []
            for chart_type in alternative_types:
                alternatives.append({
                    "chart_type": chart_type.value,
                    "name": chart_type.value.replace("_", " ").title(),
                    "description": self._get_chart_type_description(chart_type),
                    "suitable_for": self._get_chart_suitability(chart_type, data_characteristics)
                })
            
            return alternatives
            
        except Exception as e:
            logger.error(f"Error getting chart alternatives: {str(e)}")
            return []
    
    def _get_chart_type_description(self, chart_type) -> str:
        """Get description for chart type"""
        descriptions = {
            "line": "Best for showing trends over time",
            "bar": "Good for comparing categories",
            "column": "Ideal for comparing values across categories",
            "pie": "Perfect for showing composition and percentages",
            "area": "Great for showing cumulative values over time",
            "scatter": "Excellent for showing correlations between variables",
            "heatmap": "Ideal for showing patterns in matrix data",
            "table": "Best for detailed data examination",
            "waterfall": "Perfect for showing financial flows and changes",
            "gauge": "Ideal for displaying KPIs and performance metrics"
        }
        return descriptions.get(chart_type.value, "Suitable for various data types")
    
    def _get_chart_suitability(self, chart_type, data_characteristics) -> List[str]:
        """Get suitability reasons for chart type"""
        suitability = []
        
        if data_characteristics.has_time_dimension and chart_type.value in ["line", "area"]:
            suitability.append("Time series data")
        
        if data_characteristics.has_categorical_data and chart_type.value in ["bar", "column", "pie"]:
            suitability.append("Categorical data")
        
        if data_characteristics.row_count > 100 and chart_type.value == "table":
            suitability.append("Large dataset")
        
        if data_characteristics.row_count <= 10 and chart_type.value == "pie":
            suitability.append("Small number of categories")
        
        return suitability
    
    async def export_chart_multiple_formats(self, request: VisualizationRequest, 
                                          formats: List[str]) -> Dict[str, Any]:
        """Export chart in multiple formats"""
        try:
            # First generate the chart
            response = await self.process_visualization_request(request)
            
            if not response.success:
                return {"error": "Failed to generate chart"}
            
            # Reconstruct the figure from the response
            fig = go.Figure(response.chart_json)
            
            # Export in multiple formats
            from .models import ExportFormat
            export_formats = [ExportFormat(fmt) for fmt in formats if fmt in [e.value for e in ExportFormat]]
            
            results = self.export_manager.export_multiple_formats(
                fig, export_formats, f"chart_{request.request_id}", request.data
            )
            
            # Generate URLs for each export
            export_urls = {}
            for fmt, result in results.items():
                if "error" not in result:
                    export_urls[fmt] = self.export_manager.get_export_url(result["filename"])
            
            return {
                "success": True,
                "exports": results,
                "urls": export_urls
            }
            
        except Exception as e:
            logger.error(f"Error exporting chart in multiple formats: {str(e)}")
            return {"error": str(e)}
    
    def get_performance_recommendations(self, data_size: int, chart_type: str) -> Dict[str, Any]:
        """Get performance optimization recommendations"""
        try:
            from .models import ChartType
            chart_enum = ChartType(chart_type)
            return self.performance_optimizer.optimize_chart_rendering(chart_enum, data_size)
        except ValueError:
            return {"error": f"Unsupported chart type: {chart_type}"}
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the visualization agent"""
        try:
            # Test basic functionality
            test_data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}, {"x": 3, "y": 15}]
            test_request = VisualizationRequest(
                request_id="health_check",
                user_id="system",
                query_intent={"metric_type": "test"},
                data=test_data
            )
            
            response = await self.process_visualization_request(test_request)
            
            return {
                "status": "healthy" if response.success else "unhealthy",
                "components": {
                    "chart_selector": "ok",
                    "chart_generator": "ok",
                    "interactive_manager": "ok",
                    "export_manager": "ok",
                    "performance_optimizer": "ok"
                },
                "cache_size": len(self.chart_cache),
                "test_processing_time_ms": response.processing_time_ms
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }