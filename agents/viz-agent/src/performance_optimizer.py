"""
Performance optimization for rendering large financial datasets
"""

import logging
import time
import psutil
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from .models import VisualizationData, PerformanceMetrics, ChartType

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Optimizes chart rendering performance for large datasets"""
    
    def __init__(self):
        self.optimization_thresholds = {
            "large_dataset": 10000,      # Points above which to apply optimizations
            "very_large_dataset": 50000,  # Points requiring aggressive optimization
            "memory_limit_mb": 500,       # Memory limit for chart data
            "processing_timeout_s": 30    # Maximum processing time
        }
        
        self.chart_specific_limits = {
            ChartType.LINE: {"max_points": 5000, "sampling_method": "time_based"},
            ChartType.SCATTER: {"max_points": 2000, "sampling_method": "random"},
            ChartType.BAR: {"max_points": 100, "sampling_method": "top_n"},
            ChartType.PIE: {"max_points": 20, "sampling_method": "top_n"},
            ChartType.HEATMAP: {"max_points": 10000, "sampling_method": "grid_based"},
            ChartType.TABLE: {"max_points": 1000, "sampling_method": "pagination"},
            ChartType.AREA: {"max_points": 3000, "sampling_method": "time_based"},
            ChartType.CANDLESTICK: {"max_points": 2000, "sampling_method": "time_based"}
        }
    
    def optimize_data_for_visualization(self, data: List[Dict[str, Any]], 
                                      chart_type: ChartType) -> Tuple[List[Dict[str, Any]], PerformanceMetrics]:
        """Optimize data for visualization based on chart type and size"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        original_count = len(data)
        
        try:
            # Check if optimization is needed
            if not self._needs_optimization(data, chart_type):
                processing_time = max(1, int((time.time() - start_time) * 1000))  # Ensure minimum 1ms
                return data, PerformanceMetrics(
                    data_processing_time_ms=processing_time,
                    chart_generation_time_ms=0,
                    memory_usage_mb=self._get_memory_usage() - start_memory,
                    data_points_count=original_count
                )
            
            # Apply appropriate optimization strategy
            optimized_data = self._apply_optimization_strategy(data, chart_type)
            
            # Calculate metrics
            processing_time = max(1, int((time.time() - start_time) * 1000))  # Ensure minimum 1ms
            memory_usage = self._get_memory_usage() - start_memory
            
            logger.info(f"Optimized dataset from {original_count} to {len(optimized_data)} points "
                       f"for {chart_type} in {processing_time}ms")
            
            return optimized_data, PerformanceMetrics(
                data_processing_time_ms=processing_time,
                chart_generation_time_ms=0,
                memory_usage_mb=memory_usage,
                data_points_count=len(optimized_data)
            )
            
        except Exception as e:
            logger.error(f"Error optimizing data: {str(e)}")
            # Return original data if optimization fails
            processing_time = max(1, int((time.time() - start_time) * 1000))  # Ensure minimum 1ms
            return data, PerformanceMetrics(
                data_processing_time_ms=processing_time,
                chart_generation_time_ms=0,
                memory_usage_mb=self._get_memory_usage() - start_memory,
                data_points_count=original_count
            )
    
    def _needs_optimization(self, data: List[Dict[str, Any]], chart_type: ChartType) -> bool:
        """Determine if data needs optimization"""
        data_count = len(data)
        
        # Check against chart-specific limits
        if chart_type in self.chart_specific_limits:
            max_points = self.chart_specific_limits[chart_type]["max_points"]
            if data_count > max_points:
                return True
        
        # Check against general thresholds
        if data_count > self.optimization_thresholds["large_dataset"]:
            return True
        
        # Check memory usage
        estimated_memory = self._estimate_memory_usage(data)
        if estimated_memory > self.optimization_thresholds["memory_limit_mb"]:
            return True
        
        return False
    
    def _apply_optimization_strategy(self, data: List[Dict[str, Any]], 
                                   chart_type: ChartType) -> List[Dict[str, Any]]:
        """Apply the appropriate optimization strategy"""
        if chart_type not in self.chart_specific_limits:
            return self._apply_generic_sampling(data)
        
        strategy_config = self.chart_specific_limits[chart_type]
        sampling_method = strategy_config["sampling_method"]
        max_points = strategy_config["max_points"]
        
        if sampling_method == "time_based":
            return self._time_based_sampling(data, max_points)
        elif sampling_method == "random":
            return self._random_sampling(data, max_points)
        elif sampling_method == "top_n":
            return self._top_n_sampling(data, max_points)
        elif sampling_method == "grid_based":
            return self._grid_based_sampling(data, max_points)
        elif sampling_method == "pagination":
            return self._pagination_sampling(data, max_points)
        else:
            return self._apply_generic_sampling(data, max_points)
    
    def _time_based_sampling(self, data: List[Dict[str, Any]], max_points: int) -> List[Dict[str, Any]]:
        """Sample data based on time intervals"""
        df = pd.DataFrame(data)
        
        # Find date/time column
        date_col = self._find_date_column(df)
        if not date_col:
            # Fallback to uniform sampling
            return self._uniform_sampling(data, max_points)
        
        # Convert to datetime if needed
        if df[date_col].dtype != 'datetime64[ns]':
            try:
                df[date_col] = pd.to_datetime(df[date_col])
            except:
                return self._uniform_sampling(data, max_points)
        
        # Sort by date
        df = df.sort_values(date_col)
        
        # Calculate sampling interval
        total_points = len(df)
        if total_points <= max_points:
            return df.to_dict('records')
        
        # Use time-based resampling
        try:
            df.set_index(date_col, inplace=True)
            
            # Determine appropriate frequency
            time_span = df.index.max() - df.index.min()
            if time_span.days > 365:
                freq = 'ME'  # Monthly (updated from deprecated 'M')
            elif time_span.days > 30:
                freq = 'W'  # Weekly
            else:
                freq = 'D'  # Daily
            
            # Resample and aggregate
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            categorical_cols = df.select_dtypes(exclude=[np.number]).columns
            
            resampled = pd.DataFrame()
            
            # Aggregate numeric columns (mean)
            if len(numeric_cols) > 0:
                resampled = df[numeric_cols].resample(freq).mean()
            
            # Aggregate categorical columns (first)
            if len(categorical_cols) > 0:
                cat_resampled = df[categorical_cols].resample(freq).first()
                if resampled.empty:
                    resampled = cat_resampled
                else:
                    resampled = resampled.join(cat_resampled)
            
            # Reset index to get date column back
            resampled.reset_index(inplace=True)
            
            # If still too many points, apply uniform sampling
            if len(resampled) > max_points:
                return self._uniform_sampling(resampled.to_dict('records'), max_points)
            
            return resampled.to_dict('records')
            
        except Exception as e:
            logger.warning(f"Time-based sampling failed: {e}, falling back to uniform sampling")
            return self._uniform_sampling(data, max_points)
    
    def _random_sampling(self, data: List[Dict[str, Any]], max_points: int) -> List[Dict[str, Any]]:
        """Random sampling of data points"""
        if len(data) <= max_points:
            return data
        
        df = pd.DataFrame(data)
        sampled_df = df.sample(n=max_points, random_state=42)
        return sampled_df.to_dict('records')
    
    def _top_n_sampling(self, data: List[Dict[str, Any]], max_points: int) -> List[Dict[str, Any]]:
        """Sample top N values based on a numeric column"""
        if len(data) <= max_points:
            return data
        
        df = pd.DataFrame(data)
        
        # Find the best numeric column for sorting
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            return self._uniform_sampling(data, max_points)
        
        # Use the first numeric column or one that looks like a value/amount
        sort_col = numeric_cols[0]
        for col in numeric_cols:
            if any(keyword in col.lower() for keyword in ['value', 'amount', 'total', 'sum']):
                sort_col = col
                break
        
        # Sort and take top N
        sorted_df = df.nlargest(max_points, sort_col)
        return sorted_df.to_dict('records')
    
    def _grid_based_sampling(self, data: List[Dict[str, Any]], max_points: int) -> List[Dict[str, Any]]:
        """Grid-based sampling for heatmap data"""
        if len(data) <= max_points:
            return data
        
        df = pd.DataFrame(data)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) < 2:
            return self._uniform_sampling(data, max_points)
        
        # Use first two numeric columns for grid
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        
        # Calculate grid dimensions
        grid_size = int(np.sqrt(max_points))
        
        # Create bins for x and y
        x_bins = pd.cut(df[x_col], bins=grid_size, labels=False)
        y_bins = pd.cut(df[y_col], bins=grid_size, labels=False)
        
        # Group by bins and aggregate
        df['x_bin'] = x_bins
        df['y_bin'] = y_bins
        
        # Aggregate by taking mean of numeric columns and first of others
        agg_dict = {}
        for col in df.columns:
            if col in ['x_bin', 'y_bin']:
                continue
            elif col in numeric_cols:
                agg_dict[col] = 'mean'
            else:
                agg_dict[col] = 'first'
        
        if agg_dict:
            aggregated = df.groupby(['x_bin', 'y_bin']).agg(agg_dict).reset_index()
            aggregated.drop(['x_bin', 'y_bin'], axis=1, inplace=True)
            return aggregated.to_dict('records')
        
        return self._uniform_sampling(data, max_points)
    
    def _pagination_sampling(self, data: List[Dict[str, Any]], max_points: int) -> List[Dict[str, Any]]:
        """Return first N points for table pagination"""
        return data[:max_points]
    
    def _uniform_sampling(self, data: List[Dict[str, Any]], max_points: int) -> List[Dict[str, Any]]:
        """Uniform sampling across the dataset"""
        if len(data) <= max_points:
            return data
        
        # Calculate step size for uniform sampling
        step = len(data) / max_points
        indices = [int(i * step) for i in range(max_points)]
        
        return [data[i] for i in indices]
    
    def _apply_generic_sampling(self, data: List[Dict[str, Any]], 
                               max_points: Optional[int] = None) -> List[Dict[str, Any]]:
        """Apply generic sampling when no specific strategy is defined"""
        if max_points is None:
            max_points = self.optimization_thresholds["large_dataset"]
        
        return self._uniform_sampling(data, max_points)
    
    def _find_date_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find date/time column in the dataframe"""
        # Check for datetime columns
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                return col
        
        # Check column names for date-like patterns
        date_keywords = ['date', 'time', 'timestamp', 'period', 'month', 'year', 'day']
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in date_keywords):
                return col
        
        return None
    
    def _estimate_memory_usage(self, data: List[Dict[str, Any]]) -> float:
        """Estimate memory usage of data in MB"""
        if not data:
            return 0.0
        
        # Rough estimation based on data size
        import sys
        sample_size = min(100, len(data))
        sample_memory = sum(sys.getsizeof(item) for item in data[:sample_size])
        estimated_total = (sample_memory / sample_size) * len(data)
        
        return estimated_total / (1024 * 1024)  # Convert to MB
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def optimize_chart_rendering(self, chart_type: ChartType, data_points: int) -> Dict[str, Any]:
        """Get optimization recommendations for chart rendering"""
        recommendations = {
            "use_webgl": False,
            "reduce_markers": False,
            "simplify_lines": False,
            "use_aggregation": False,
            "enable_streaming": False
        }
        
        # WebGL for large scatter plots
        if chart_type == ChartType.SCATTER and data_points > 1000:
            recommendations["use_webgl"] = True
        
        # Reduce markers for large line charts
        if chart_type == ChartType.LINE and data_points > 2000:
            recommendations["reduce_markers"] = True
            recommendations["simplify_lines"] = True
        
        # Use aggregation for very large datasets
        if data_points > self.optimization_thresholds["very_large_dataset"]:
            recommendations["use_aggregation"] = True
        
        # Enable streaming for real-time data
        if data_points > 10000:
            recommendations["enable_streaming"] = True
        
        return recommendations
    
    def monitor_performance(self, operation_name: str) -> 'PerformanceMonitor':
        """Create a performance monitor context manager"""
        return PerformanceMonitor(operation_name)


class PerformanceMonitor:
    """Context manager for monitoring performance metrics"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.start_memory = None
        self.end_time = None
        self.end_memory = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.start_memory = self._get_memory_usage()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.end_memory = self._get_memory_usage()
        
        duration = (self.end_time - self.start_time) * 1000  # Convert to ms
        memory_delta = self.end_memory - self.start_memory
        
        logger.info(f"{self.operation_name} completed in {duration:.2f}ms, "
                   f"memory delta: {memory_delta:.2f}MB")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def get_metrics(self) -> Dict[str, float]:
        """Get performance metrics"""
        if self.start_time is None or self.end_time is None:
            return {}
        
        return {
            "duration_ms": (self.end_time - self.start_time) * 1000,
            "memory_delta_mb": self.end_memory - self.start_memory,
            "start_memory_mb": self.start_memory,
            "end_memory_mb": self.end_memory
        }