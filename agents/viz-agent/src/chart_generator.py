"""
Dynamic chart generation using Plotly with CFO-specific styling
"""

import logging
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from .models import (
    ChartType, ChartConfiguration, InteractiveConfig, 
    VisualizationData, ChartSpecification
)

logger = logging.getLogger(__name__)


class CFOChartStyler:
    """CFO-specific styling and theming for charts"""
    
    def __init__(self):
        self.color_schemes = {
            "corporate": {
                "primary": "#1f77b4",
                "secondary": "#ff7f0e", 
                "success": "#2ca02c",
                "warning": "#d62728",
                "info": "#9467bd",
                "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
            },
            "financial": {
                "primary": "#2E86AB",
                "secondary": "#A23B72",
                "success": "#F18F01",
                "warning": "#C73E1D",
                "info": "#592E83",
                "colors": ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#592E83", "#4A5D23", "#8B2635"]
            },
            "professional": {
                "primary": "#003f5c",
                "secondary": "#2f4b7c",
                "success": "#665191",
                "warning": "#a05195",
                "info": "#d45087",
                "colors": ["#003f5c", "#2f4b7c", "#665191", "#a05195", "#d45087", "#f95d6a", "#ff7c43", "#ffa600"]
            }
        }
        
        self.cfo_layout_defaults = {
            "font": {"family": "Arial, sans-serif", "size": 12, "color": "#2c3e50"},
            "title_font": {"family": "Arial, sans-serif", "size": 16, "color": "#2c3e50"},
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
            "showlegend": True,
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": -0.2,
                "xanchor": "center",
                "x": 0.5
            },
            "margin": {"l": 60, "r": 60, "t": 80, "b": 80},
            "hovermode": "closest"
        }
    
    def get_color_scheme(self, scheme_name: str = "corporate") -> Dict[str, Any]:
        """Get color scheme configuration"""
        return self.color_schemes.get(scheme_name, self.color_schemes["corporate"])
    
    def apply_cfo_styling(self, fig: go.Figure, config: ChartConfiguration) -> go.Figure:
        """Apply CFO-specific styling to a Plotly figure"""
        color_scheme = self.get_color_scheme(config.color_scheme)
        
        # Create layout updates without conflicts
        layout_updates = {
            **{k: v for k, v in self.cfo_layout_defaults.items() if k != 'showlegend'},
            "title": {
                "text": config.title,
                "x": 0.5,
                "xanchor": "center",
                "font": self.cfo_layout_defaults["title_font"]
            },
            "xaxis_title": config.x_axis_label,
            "yaxis_title": config.y_axis_label,
            "showlegend": config.show_legend,
            "width": config.width,
            "height": config.height
        }
        
        # Update layout with CFO styling
        fig.update_layout(**layout_updates)
        
        # Apply grid styling
        if config.show_grid:
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.2)")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.2)")
        else:
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=False)
        
        # Update trace colors safely
        for i, trace in enumerate(fig.data):
            color_index = i % len(color_scheme["colors"])
            color = color_scheme["colors"][color_index]
            
            # Apply colors based on trace type, handling different chart types
            try:
                if trace.type in ['scatter', 'line', 'bar']:
                    trace.update(marker_color=color, line_color=color)
                elif trace.type == 'pie':
                    trace.update(marker=dict(colors=color_scheme["colors"]))
                elif trace.type == 'heatmap':
                    # Heatmaps use colorscale, not marker colors
                    pass
                elif trace.type == 'table':
                    # Tables don't use marker colors
                    pass
                elif trace.type == 'indicator':
                    # Gauges have their own color schemes
                    pass
                elif trace.type == 'waterfall':
                    trace.update(marker_color=color)
                else:
                    # Try to apply colors, but catch any errors
                    try:
                        trace.update(marker_color=color)
                    except:
                        pass
                    try:
                        trace.update(line_color=color)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"Could not apply color to trace {i}: {e}")
        
        return fig


class ChartGenerator:
    """Dynamic chart generation with Plotly"""
    
    def __init__(self):
        self.styler = CFOChartStyler()
        self.chart_generators = {
            ChartType.LINE: self._generate_line_chart,
            ChartType.BAR: self._generate_bar_chart,
            ChartType.COLUMN: self._generate_column_chart,
            ChartType.PIE: self._generate_pie_chart,
            ChartType.AREA: self._generate_area_chart,
            ChartType.SCATTER: self._generate_scatter_chart,
            ChartType.HEATMAP: self._generate_heatmap,
            ChartType.TABLE: self._generate_table,
            ChartType.WATERFALL: self._generate_waterfall_chart,
            ChartType.GAUGE: self._generate_gauge_chart,
            ChartType.CANDLESTICK: self._generate_candlestick_chart
        }
    
    def generate_chart(self, chart_spec: ChartSpecification) -> Tuple[go.Figure, Dict[str, Any]]:
        """Generate a chart based on the specification"""
        try:
            chart_type = chart_spec.chart_config.chart_type
            
            if chart_type not in self.chart_generators:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            # Convert data to DataFrame for easier manipulation
            df = pd.DataFrame(chart_spec.data.data)
            
            # Generate the chart
            generator_func = self.chart_generators[chart_type]
            fig = generator_func(df, chart_spec.chart_config)
            
            # Apply CFO styling
            fig = self.styler.apply_cfo_styling(fig, chart_spec.chart_config)
            
            # Apply interactive configuration
            fig = self._apply_interactive_config(fig, chart_spec.interactive_config)
            
            # Generate chart metadata
            metadata = self._generate_chart_metadata(fig, chart_spec)
            
            logger.info(f"Successfully generated {chart_type} chart with {len(df)} data points")
            return fig, metadata
            
        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            raise
    
    def _generate_line_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate line chart for time series data"""
        fig = go.Figure()
        
        # Determine x and y columns
        x_col, y_cols = self._determine_chart_columns(df, "line")
        
        for y_col in y_cols:
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode='lines+markers',
                name=y_col,
                line=dict(width=2),
                marker=dict(size=6)
            ))
        
        return fig
    
    def _generate_bar_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate horizontal bar chart"""
        fig = go.Figure()
        
        x_col, y_cols = self._determine_chart_columns(df, "bar")
        
        for y_col in y_cols:
            fig.add_trace(go.Bar(
                y=df[x_col],
                x=df[y_col],
                name=y_col,
                orientation='h'
            ))
        
        return fig
    
    def _generate_column_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate vertical column chart"""
        fig = go.Figure()
        
        x_col, y_cols = self._determine_chart_columns(df, "column")
        
        for y_col in y_cols:
            fig.add_trace(go.Bar(
                x=df[x_col],
                y=df[y_col],
                name=y_col
            ))
        
        return fig
    
    def _generate_pie_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate pie chart for composition data"""
        # For pie charts, we need labels and values
        label_col, value_col = self._determine_pie_columns(df)
        
        fig = go.Figure(data=[go.Pie(
            labels=df[label_col],
            values=df[value_col],
            hole=0.3,  # Donut style
            textinfo='label+percent',
            textposition='outside'
        )])
        
        return fig
    
    def _generate_area_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate area chart for cumulative data"""
        fig = go.Figure()
        
        x_col, y_cols = self._determine_chart_columns(df, "area")
        
        for y_col in y_cols:
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode='lines',
                name=y_col,
                fill='tonexty' if len(fig.data) > 0 else 'tozeroy',
                stackgroup='one'
            ))
        
        return fig
    
    def _generate_scatter_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate scatter plot for correlation analysis"""
        fig = go.Figure()
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if len(numeric_cols) >= 2:
            x_col, y_col = numeric_cols[0], numeric_cols[1]
            
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode='markers',
                marker=dict(
                    size=8,
                    opacity=0.7,
                    line=dict(width=1, color='white')
                ),
                name=f"{y_col} vs {x_col}"
            ))
        
        return fig
    
    def _generate_heatmap(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate heatmap for correlation or matrix data"""
        # If we have numeric data, create correlation heatmap
        numeric_df = df.select_dtypes(include=['number'])
        
        if len(numeric_df.columns) > 1:
            corr_matrix = numeric_df.corr()
            
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=corr_matrix.round(2).values,
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
        else:
            # Create a simple heatmap from the data
            fig = go.Figure(data=go.Heatmap(
                z=df.select_dtypes(include=['number']).values,
                colorscale='Blues'
            ))
        
        return fig
    
    def _generate_table(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate table for detailed data display"""
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color='lightblue',
                align='left',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color='white',
                align='left',
                font=dict(size=11, color='black'),
                height=30
            )
        )])
        
        return fig
    
    def _generate_waterfall_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate waterfall chart for financial flow analysis"""
        # Waterfall charts need categories and values
        x_col, y_col = self._determine_chart_columns(df, "waterfall")[:2]
        
        fig = go.Figure(go.Waterfall(
            name="Waterfall",
            orientation="v",
            measure=["relative"] * (len(df) - 1) + ["total"],
            x=df[x_col],
            textposition="outside",
            text=[f"{val:,.0f}" if isinstance(val, (int, float)) else str(val) for val in df[y_col]],
            y=df[y_col],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        
        return fig
    
    def _generate_gauge_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate gauge chart for KPI display"""
        # For gauge, we need a single value
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if numeric_cols:
            value = df[numeric_cols[0]].iloc[0] if len(df) > 0 else 0
            max_value = df[numeric_cols[0]].max() * 1.2  # 20% buffer
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=value,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': numeric_cols[0]},
                delta={'reference': max_value * 0.8},
                gauge={
                    'axis': {'range': [None, max_value]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, max_value * 0.5], 'color': "lightgray"},
                        {'range': [max_value * 0.5, max_value * 0.8], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': max_value * 0.9
                    }
                }
            ))
        else:
            fig = go.Figure()
        
        return fig
    
    def _generate_candlestick_chart(self, df: pd.DataFrame, config: ChartConfiguration) -> go.Figure:
        """Generate candlestick chart for financial time series"""
        # Candlestick needs OHLC data
        required_cols = ['open', 'high', 'low', 'close']
        available_cols = [col for col in df.columns if col.lower() in required_cols]
        
        if len(available_cols) >= 4:
            date_col = self._find_date_column(df)
            
            fig = go.Figure(data=go.Candlestick(
                x=df[date_col] if date_col else df.index,
                open=df[available_cols[0]],
                high=df[available_cols[1]],
                low=df[available_cols[2]],
                close=df[available_cols[3]]
            ))
        else:
            # Fallback to line chart
            fig = self._generate_line_chart(df, config)
        
        return fig
    
    def _determine_chart_columns(self, df: pd.DataFrame, chart_type: str) -> Tuple[str, List[str]]:
        """Determine which columns to use for x and y axes"""
        columns = df.columns.tolist()
        
        # Find date/time column for x-axis
        date_col = self._find_date_column(df)
        
        # Find numeric columns for y-axis
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        # Find categorical columns
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if date_col:
            x_col = date_col
            y_cols = numeric_cols
        elif categorical_cols and numeric_cols:
            x_col = categorical_cols[0]
            y_cols = numeric_cols
        elif len(columns) >= 2:
            x_col = columns[0]
            y_cols = columns[1:]
        else:
            x_col = columns[0] if columns else 'index'
            y_cols = numeric_cols if numeric_cols else columns[1:] if len(columns) > 1 else []
        
        return x_col, y_cols
    
    def _determine_pie_columns(self, df: pd.DataFrame) -> Tuple[str, str]:
        """Determine label and value columns for pie chart"""
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if categorical_cols and numeric_cols:
            return categorical_cols[0], numeric_cols[0]
        elif len(df.columns) >= 2:
            return df.columns[0], df.columns[1]
        else:
            return df.columns[0], df.columns[0]
    
    def _find_date_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find date/time column in the dataframe"""
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                return col
            
            # Check if column name suggests it's a date
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['date', 'time', 'period', 'month', 'year']):
                return col
        
        return None
    
    def _apply_interactive_config(self, fig: go.Figure, interactive_config: InteractiveConfig) -> go.Figure:
        """Apply interactive configuration to the chart"""
        config = {}
        
        if not interactive_config.enable_zoom:
            config['scrollZoom'] = False
        
        if not interactive_config.enable_pan:
            config['doubleClick'] = False
        
        # Update layout for interactivity
        fig.update_layout(
            dragmode='zoom' if interactive_config.enable_zoom else False,
            hovermode='closest' if interactive_config.enable_hover else False
        )
        
        # Add selection capabilities
        if interactive_config.enable_select:
            fig.update_layout(selectdirection='d')  # 'd' for diagonal
        
        return fig
    
    def _generate_chart_metadata(self, fig: go.Figure, chart_spec: ChartSpecification) -> Dict[str, Any]:
        """Generate metadata about the chart"""
        return {
            "chart_type": chart_spec.chart_config.chart_type.value,
            "data_points": len(chart_spec.data.data),
            "traces": len(fig.data),
            "interactive_features": {
                "zoom": chart_spec.interactive_config.enable_zoom,
                "pan": chart_spec.interactive_config.enable_pan,
                "hover": chart_spec.interactive_config.enable_hover,
                "select": chart_spec.interactive_config.enable_select
            },
            "styling": {
                "color_scheme": chart_spec.chart_config.color_scheme,
                "dimensions": {
                    "width": chart_spec.chart_config.width,
                    "height": chart_spec.chart_config.height
                }
            }
        }