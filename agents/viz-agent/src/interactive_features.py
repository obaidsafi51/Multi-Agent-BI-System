"""
Interactive chart configuration with zoom, filter, and drill-down capabilities
"""

import logging
from typing import Dict, List, Any, Optional, Callable
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from .models import InteractiveConfig, ChartType

logger = logging.getLogger(__name__)


class InteractiveFeatureManager:
    """Manages interactive features for charts"""
    
    def __init__(self):
        self.drill_down_handlers = {}
        self.filter_handlers = {}
        self.zoom_configurations = {}
    
    def configure_interactivity(self, fig: go.Figure, config: InteractiveConfig, 
                              chart_type: ChartType) -> go.Figure:
        """Configure interactive features for a chart"""
        try:
            # Configure zoom and pan
            if config.enable_zoom or config.enable_pan:
                fig = self._configure_zoom_pan(fig, config)
            
            # Configure hover tooltips
            if config.enable_hover:
                fig = self._configure_hover(fig, chart_type)
            
            # Configure selection
            if config.enable_select:
                fig = self._configure_selection(fig, chart_type)
            
            # Configure drill-down if enabled
            if config.drill_down_enabled:
                fig = self._configure_drill_down(fig, config)
            
            # Configure crossfilter if enabled
            if config.enable_crossfilter:
                fig = self._configure_crossfilter(fig, config)
            
            logger.info(f"Configured interactive features for {chart_type}")
            return fig
            
        except Exception as e:
            logger.error(f"Error configuring interactivity: {str(e)}")
            return fig
    
    def _configure_zoom_pan(self, fig: go.Figure, config: InteractiveConfig) -> go.Figure:
        """Configure zoom and pan functionality"""
        dragmode = 'zoom' if config.enable_zoom else 'pan' if config.enable_pan else False
        
        fig.update_layout(
            dragmode=dragmode,
            xaxis=dict(
                fixedrange=not config.enable_zoom,
                rangeslider=dict(visible=False) if not config.enable_zoom else None
            ),
            yaxis=dict(
                fixedrange=not config.enable_zoom
            )
        )
        
        # Add range slider for time series data
        if config.enable_zoom and self._is_time_series_chart(fig):
            fig.update_layout(
                xaxis=dict(
                    rangeslider=dict(
                        visible=True,
                        thickness=0.1
                    ),
                    type='date'
                )
            )
        
        return fig
    
    def _configure_hover(self, fig: go.Figure, chart_type: ChartType) -> go.Figure:
        """Configure hover tooltips based on chart type"""
        hover_templates = {
            ChartType.LINE: "%{x}<br>%{y:,.2f}<br><extra></extra>",
            ChartType.BAR: "%{y}<br>%{x:,.2f}<br><extra></extra>",
            ChartType.COLUMN: "%{x}<br>%{y:,.2f}<br><extra></extra>",
            ChartType.PIE: "%{label}<br>%{value:,.2f} (%{percent})<br><extra></extra>",
            ChartType.SCATTER: "%{x:,.2f}, %{y:,.2f}<br><extra></extra>",
            ChartType.AREA: "%{x}<br>%{y:,.2f}<br><extra></extra>",
            ChartType.HEATMAP: "%{x}<br>%{y}<br>%{z:,.2f}<br><extra></extra>"
        }
        
        template = hover_templates.get(chart_type, "%{x}<br>%{y}<br><extra></extra>")
        
        # Update hover template for all traces
        for trace in fig.data:
            if hasattr(trace, 'hovertemplate'):
                trace.update(hovertemplate=template)
        
        fig.update_layout(hovermode='closest')
        
        return fig
    
    def _configure_selection(self, fig: go.Figure, chart_type: ChartType) -> go.Figure:
        """Configure data selection capabilities"""
        # Enable selection for scatter plots and line charts
        if chart_type in [ChartType.SCATTER, ChartType.LINE, ChartType.BAR, ChartType.COLUMN]:
            fig.update_layout(
                selectdirection='d',
                dragmode='select'
            )
            
            # Add selection styling
            for trace in fig.data:
                if hasattr(trace, 'selected'):
                    trace.update(
                        selected=dict(marker=dict(color='red', size=8)),
                        unselected=dict(marker=dict(opacity=0.3))
                    )
        
        return fig
    
    def _configure_drill_down(self, fig: go.Figure, config: InteractiveConfig) -> go.Figure:
        """Configure drill-down functionality"""
        if not config.drill_down_levels:
            return fig
        
        # Add click event handling for drill-down
        # This would typically be handled on the frontend with JavaScript
        # Here we prepare the data structure for drill-down
        
        drill_down_data = {
            'levels': config.drill_down_levels,
            'current_level': 0,
            'enabled': True
        }
        
        # Store drill-down configuration in the figure
        if not hasattr(fig, 'meta'):
            fig.meta = {}
        fig.meta['drill_down'] = drill_down_data
        
        # Add visual indicators for drillable elements
        for trace in fig.data:
            if hasattr(trace, 'marker'):
                trace.update(
                    marker=dict(
                        line=dict(width=2, color='rgba(0,0,0,0.3)'),
                        opacity=0.8
                    )
                )
        
        return fig
    
    def _configure_crossfilter(self, fig: go.Figure, config: InteractiveConfig) -> go.Figure:
        """Configure crossfilter interactions between charts"""
        # Crossfilter is typically implemented on the frontend
        # Here we prepare the chart for crossfilter integration
        
        crossfilter_config = {
            'enabled': True,
            'dimensions': [],
            'groups': []
        }
        
        # Identify potential crossfilter dimensions
        for trace in fig.data:
            if hasattr(trace, 'x') and hasattr(trace, 'y'):
                crossfilter_config['dimensions'].extend(['x', 'y'])
        
        if not hasattr(fig, 'meta'):
            fig.meta = {}
        fig.meta['crossfilter'] = crossfilter_config
        
        return fig
    
    def add_range_selector(self, fig: go.Figure, periods: List[str] = None) -> go.Figure:
        """Add range selector buttons for time series charts"""
        if not periods:
            periods = ['1M', '3M', '6M', '1Y', 'YTD', 'All']
        
        buttons = []
        for period in periods:
            if period == 'All':
                buttons.append(dict(step='all', label=period))
            elif period == 'YTD':
                buttons.append(dict(count=1, label=period, step='year', stepmode='todate'))
            elif period.endswith('M'):
                count = int(period[:-1])
                buttons.append(dict(count=count, label=period, step='month', stepmode='backward'))
            elif period.endswith('Y'):
                count = int(period[:-1])
                buttons.append(dict(count=count, label=period, step='year', stepmode='backward'))
        
        fig.update_layout(
            xaxis=dict(
                rangeselector=dict(
                    buttons=buttons,
                    bgcolor='rgba(150, 150, 150, 0.1)',
                    bordercolor='rgba(150, 150, 150, 0.2)',
                    borderwidth=1
                ),
                rangeslider=dict(visible=True, thickness=0.1),
                type='date'
            )
        )
        
        return fig
    
    def add_annotation_tools(self, fig: go.Figure) -> go.Figure:
        """Add annotation and drawing tools"""
        fig.update_layout(
            dragmode='drawrect',
            newshape=dict(
                line_color='red',
                line_width=2,
                opacity=0.8
            ),
            modebar=dict(
                add=['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape']
            )
        )
        
        return fig
    
    def configure_responsive_design(self, fig: go.Figure) -> go.Figure:
        """Configure responsive design for different screen sizes"""
        fig.update_layout(
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50),
            font=dict(size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        
        # Configure responsive modebar
        fig.update_layout(
            modebar=dict(
                orientation='v',
                bgcolor='rgba(255,255,255,0.8)',
                color='rgba(0,0,0,0.3)',
                activecolor='rgba(0,0,0,0.9)'
            )
        )
        
        return fig
    
    def add_custom_controls(self, fig: go.Figure, controls: Dict[str, Any]) -> go.Figure:
        """Add custom interactive controls"""
        if 'buttons' in controls:
            # Add custom buttons
            buttons = []
            for button_config in controls['buttons']:
                buttons.append(dict(
                    label=button_config.get('label', 'Button'),
                    method=button_config.get('method', 'update'),
                    args=button_config.get('args', [{}])
                ))
            
            fig.update_layout(
                updatemenus=[dict(
                    type="buttons",
                    direction="left",
                    buttons=buttons,
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    x=0.01,
                    xanchor="left",
                    y=1.02,
                    yanchor="top"
                )]
            )
        
        if 'sliders' in controls:
            # Add sliders for parameter control
            sliders = []
            for slider_config in controls['sliders']:
                slider = dict(
                    active=slider_config.get('active', 0),
                    currentvalue={"prefix": slider_config.get('prefix', '')},
                    pad={"t": 50},
                    steps=slider_config.get('steps', [])
                )
                sliders.append(slider)
            
            fig.update_layout(sliders=sliders)
        
        return fig
    
    def _is_time_series_chart(self, fig: go.Figure) -> bool:
        """Check if the chart contains time series data"""
        for trace in fig.data:
            if hasattr(trace, 'x') and trace.x is not None:
                # Check if x-axis data looks like dates
                x_data = trace.x
                if len(x_data) > 0:
                    first_value = x_data[0]
                    if isinstance(first_value, str) and self._looks_like_date(first_value):
                        return True
        return False
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if a string value looks like a date"""
        date_indicators = ['-', '/', ':', 'T', 'Z']
        return any(indicator in value for indicator in date_indicators) and len(value) >= 8


class DrillDownManager:
    """Manages drill-down functionality for hierarchical data"""
    
    def __init__(self):
        self.drill_paths = {}
        self.current_levels = {}
    
    def setup_drill_down(self, chart_id: str, hierarchy: List[str], data: pd.DataFrame) -> Dict[str, Any]:
        """Setup drill-down hierarchy for a chart"""
        self.drill_paths[chart_id] = {
            'hierarchy': hierarchy,
            'data': data,
            'current_level': 0
        }
        
        return {
            'chart_id': chart_id,
            'levels': hierarchy,
            'current_level': 0,
            'can_drill_down': len(hierarchy) > 1,
            'can_drill_up': False
        }
    
    def drill_down(self, chart_id: str, selected_value: Any) -> Dict[str, Any]:
        """Perform drill-down operation"""
        if chart_id not in self.drill_paths:
            raise ValueError(f"Chart {chart_id} not configured for drill-down")
        
        drill_path = self.drill_paths[chart_id]
        current_level = drill_path['current_level']
        hierarchy = drill_path['hierarchy']
        
        if current_level >= len(hierarchy) - 1:
            return {'error': 'Already at lowest level'}
        
        # Filter data based on selected value
        next_level = current_level + 1
        current_column = hierarchy[current_level]
        filtered_data = drill_path['data'][drill_path['data'][current_column] == selected_value]
        
        # Update drill path
        drill_path['current_level'] = next_level
        drill_path['filtered_data'] = filtered_data
        
        return {
            'chart_id': chart_id,
            'current_level': next_level,
            'level_name': hierarchy[next_level],
            'filtered_data': filtered_data.to_dict('records'),
            'can_drill_down': next_level < len(hierarchy) - 1,
            'can_drill_up': True,
            'breadcrumb': self._generate_breadcrumb(chart_id)
        }
    
    def drill_up(self, chart_id: str) -> Dict[str, Any]:
        """Perform drill-up operation"""
        if chart_id not in self.drill_paths:
            raise ValueError(f"Chart {chart_id} not configured for drill-down")
        
        drill_path = self.drill_paths[chart_id]
        current_level = drill_path['current_level']
        
        if current_level <= 0:
            return {'error': 'Already at highest level'}
        
        # Move up one level
        new_level = current_level - 1
        drill_path['current_level'] = new_level
        
        # Reset to original data if at top level
        if new_level == 0:
            drill_path.pop('filtered_data', None)
        
        return {
            'chart_id': chart_id,
            'current_level': new_level,
            'level_name': drill_path['hierarchy'][new_level],
            'can_drill_down': True,
            'can_drill_up': new_level > 0,
            'breadcrumb': self._generate_breadcrumb(chart_id)
        }
    
    def _generate_breadcrumb(self, chart_id: str) -> List[str]:
        """Generate breadcrumb navigation for current drill-down state"""
        drill_path = self.drill_paths[chart_id]
        hierarchy = drill_path['hierarchy']
        current_level = drill_path['current_level']
        
        return hierarchy[:current_level + 1]