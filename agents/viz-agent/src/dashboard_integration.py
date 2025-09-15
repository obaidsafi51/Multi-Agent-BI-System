"""
Dashboard Integration Module for Viz Agent

Handles real-time dashboard updates, visualization delivery, and frontend communication.
This module bridges the gap between viz-agent chart generation and frontend dashboard display.
"""

import logging
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
import websockets
import websockets.exceptions

from .models import VisualizationResponse, ChartSpecification

logger = logging.getLogger(__name__)


@dataclass
class DashboardCard:
    """Dashboard card specification for frontend display"""
    id: str
    card_type: str  # "chart", "kpi", "table", "insight"
    title: str
    position: Dict[str, int]  # {"row": 0, "col": 0}
    size: str  # "small", "medium", "large", "medium_h", "medium_v"
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class DashboardUpdate:
    """Dashboard update message"""
    update_type: str  # "add_card", "update_card", "remove_card", "refresh_dashboard"
    session_id: str
    user_id: str
    query_id: Optional[str] = None
    cards: Optional[List[DashboardCard]] = None
    timestamp: Optional[str] = None
    source: str = "viz-agent"


class DashboardIntegrationManager:
    """
    Manages dashboard integration for the viz-agent.
    Handles real-time updates, card generation, and frontend communication.
    """
    
    def __init__(self):
        self.dashboard_connections: Dict[str, Any] = {}  # session_id -> connection info
        self.active_cards: Dict[str, List[DashboardCard]] = {}  # session_id -> cards list
        self.update_callbacks: List[Callable[[DashboardUpdate], None]] = []
        self.websocket_backend_connection: Optional[Any] = None
        
        # Performance tracking
        self.cards_generated = 0
        self.updates_sent = 0
        self.start_time = time.time()
    
    def register_update_callback(self, callback: Callable[[DashboardUpdate], None]):
        """Register a callback function for dashboard updates"""
        self.update_callbacks.append(callback)
        logger.info(f"Registered dashboard update callback: {callback.__name__}")
    
    async def initialize_backend_connection(self, backend_ws_url: str = None):
        """Initialize connection to backend for dashboard updates"""
        if not backend_ws_url:
            # Try to connect to backend WebSocket endpoint
            backend_ws_url = "ws://backend:8000/ws/viz-dashboard-updates"
        
        try:
            logger.info(f"Attempting to connect to backend dashboard WebSocket: {backend_ws_url}")
            # Note: This would need to be implemented in the backend
            # For now, we'll use the callback system instead
            logger.info("Backend WebSocket connection initialized (using callback system)")
        except Exception as e:
            logger.warning(f"Failed to connect to backend WebSocket: {e}")
            logger.info("Will use callback system for dashboard updates")
    
    async def create_visualization_card(
        self, 
        viz_response: VisualizationResponse,
        session_id: str,
        user_id: str,
        query_context: Dict[str, Any] = None
    ) -> DashboardCard:
        """
        Create a dashboard card from a visualization response.
        This is the key method that transforms viz-agent output into dashboard-ready format.
        """
        try:
            # Determine card type and content based on visualization
            chart_type = self._determine_chart_type(viz_response)
            card_type = self._map_chart_to_card_type(chart_type)
            
            # Generate unique card ID
            card_id = f"viz_card_{viz_response.request_id}_{int(time.time())}"
            
            # Determine position (this could be enhanced with intelligent positioning)
            position = self._calculate_card_position(session_id, card_type)
            
            # Determine card size based on chart type and data complexity
            size = self._determine_card_size(chart_type, viz_response.chart_spec)
            
            # Build card content
            content = await self._build_card_content(viz_response, query_context)
            
            # Create dashboard card
            card = DashboardCard(
                id=card_id,
                card_type=card_type,
                title=content.get("title", "Visualization"),
                position=position,
                size=size,
                content=content,
                metadata={
                    "query_id": viz_response.request_id,
                    "chart_type": chart_type,
                    "processing_time_ms": viz_response.processing_time_ms,
                    "data_points": len(viz_response.chart_spec.data.data) if viz_response.chart_spec and viz_response.chart_spec.data else 0,
                    "viz_agent_version": "1.0.0"
                },
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            
            # Track the card for this session
            if session_id not in self.active_cards:
                self.active_cards[session_id] = []
            self.active_cards[session_id].append(card)
            
            self.cards_generated += 1
            logger.info(f"Created dashboard card {card_id} for session {session_id}")
            
            return card
            
        except Exception as e:
            logger.error(f"Error creating visualization card: {e}")
            # Return a fallback error card
            return self._create_error_card(viz_response.request_id, str(e), session_id)
    
    async def send_dashboard_update(
        self, 
        update_type: str,
        session_id: str, 
        user_id: str,
        cards: List[DashboardCard] = None,
        query_id: str = None
    ):
        """
        Send dashboard update to frontend.
        This method handles the communication to display data on the dashboard.
        """
        try:
            # Create dashboard update message
            update = DashboardUpdate(
                update_type=update_type,
                session_id=session_id,
                user_id=user_id,
                query_id=query_id,
                cards=cards,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Send to all registered callbacks
            for callback in self.update_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(update)
                    else:
                        callback(update)
                except Exception as e:
                    logger.error(f"Error in dashboard update callback: {e}")
            
            self.updates_sent += 1
            logger.info(f"Sent dashboard update '{update_type}' for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error sending dashboard update: {e}")
    
    def _determine_chart_type(self, viz_response: VisualizationResponse) -> str:
        """Determine the chart type from visualization response"""
        if viz_response.chart_spec and viz_response.chart_spec.chart_config:
            return viz_response.chart_spec.chart_config.chart_type.value
        return "table"  # fallback
    
    def _map_chart_to_card_type(self, chart_type: str) -> str:
        """Map chart type to dashboard card type"""
        if chart_type in ["line", "bar", "column", "area", "pie", "scatter", "heatmap"]:
            return "chart"
        elif chart_type == "table":
            return "table"
        elif chart_type in ["gauge", "metric"]:
            return "kpi"
        else:
            return "chart"  # default to chart
    
    def _calculate_card_position(self, session_id: str, card_type: str) -> Dict[str, int]:
        """Calculate the best position for a new card"""
        existing_cards = self.active_cards.get(session_id, [])
        
        if not existing_cards:
            return {"row": 0, "col": 0}
        
        # Simple positioning logic - place in next available spot
        max_row = max(card.position.get("row", 0) for card in existing_cards)
        max_col = max(card.position.get("col", 0) for card in existing_cards if card.position.get("row", 0) == max_row)
        
        # Try to place in same row if space available (assuming 3 columns max)
        if max_col < 2:
            return {"row": max_row, "col": max_col + 1}
        else:
            return {"row": max_row + 1, "col": 0}
    
    def _determine_card_size(self, chart_type: str, chart_spec: ChartSpecification = None) -> str:
        """Determine appropriate card size based on chart type and complexity"""
        if chart_type in ["gauge", "metric"]:
            return "small"
        elif chart_type == "table":
            # Determine table size based on data volume
            if chart_spec and chart_spec.data:
                row_count = len(chart_spec.data.data)
                if row_count > 10:
                    return "large"
                elif row_count > 5:
                    return "medium"
                else:
                    return "small"
            return "medium"
        elif chart_type in ["line", "area"]:
            return "medium_h"  # Horizontal medium for time series
        elif chart_type in ["bar", "column"]:
            return "medium_v"  # Vertical medium for categorical data
        else:
            return "medium"  # default
    
    async def _build_card_content(
        self, 
        viz_response: VisualizationResponse, 
        query_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Build the content section of the dashboard card"""
        content = {}
        
        # Extract basic information
        if viz_response.chart_spec and viz_response.chart_spec.chart_config:
            config = viz_response.chart_spec.chart_config
            content.update({
                "title": config.title,
                "chart_type": config.chart_type.value.replace("_", " ").title(),
                "x_axis_label": config.x_axis_label,
                "y_axis_label": config.y_axis_label,
                "color_scheme": config.color_scheme
            })
        
        # Add chart data and configuration
        if viz_response.chart_html:
            content["chart_html"] = viz_response.chart_html
        
        if viz_response.chart_json:
            content["chart_data"] = viz_response.chart_json
        
        # Add raw data for table cards
        if viz_response.chart_spec and viz_response.chart_spec.data:
            data = viz_response.chart_spec.data
            content.update({
                "data": data.data,
                "columns": data.columns,
                "row_count": len(data.data) if data.data else 0
            })
        
        # Add query context information
        if query_context:
            content["query_context"] = query_context
            if "query" in query_context:
                content["description"] = f"Results for: {query_context['query']}"
        
        # Add export options
        content["export_options"] = {
            "formats": ["png", "pdf", "svg", "json"],
            "sizes": ["small", "medium", "large"]
        }
        
        return content
    
    def _create_error_card(self, request_id: str, error_message: str, session_id: str) -> DashboardCard:
        """Create an error card when visualization fails"""
        return DashboardCard(
            id=f"error_card_{request_id}",
            card_type="insight",
            title="Visualization Error",
            position=self._calculate_card_position(session_id, "insight"),
            size="medium",
            content={
                "title": "Visualization Error",
                "description": f"Failed to create visualization: {error_message}",
                "error": True,
                "suggestions": [
                    "Try a different chart type",
                    "Check your data format",
                    "Reduce data complexity"
                ]
            },
            metadata={
                "error": True,
                "request_id": request_id
            },
            created_at=datetime.utcnow().isoformat()
        )
    
    async def process_query_for_dashboard(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        query: str,
        query_id: str,
        session_id: str,
        user_id: str = "anonymous",
        intent: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process query data and create dashboard visualization.
        This is the main entry point from the backend/websocket handler.
        """
        try:
            logger.info(f"Processing query for dashboard: {query_id}")
            
            # Create a mock VisualizationRequest (since we're getting processed data)
            from .models import VisualizationRequest, VisualizationData, DataCharacteristics
            
            # Analyze data characteristics
            data_characteristics = self._analyze_data_for_dashboard(data, columns)
            
            # Create visualization data object
            viz_data = VisualizationData(
                data=data,
                columns=columns,
                data_characteristics=data_characteristics
            )
            
            # Create visualization request
            viz_request = VisualizationRequest(
                request_id=query_id,
                user_id=user_id,
                query_intent=intent or {},
                data=data,
                preferences={
                    "auto_select_chart_type": True,
                    "responsive": True,
                    "color_scheme": "corporate"
                },
                database_context=None  # This would come from session
            )
            
            # Use the main visualization agent to process the request
            from .visualization_agent import VisualizationAgent
            viz_agent = VisualizationAgent()
            viz_response = await viz_agent.process_visualization_request(viz_request)
            
            if viz_response.success:
                # Create dashboard card
                card = await self.create_visualization_card(
                    viz_response,
                    session_id,
                    user_id,
                    {"query": query, "intent": intent}
                )
                
                # Send dashboard update
                await self.send_dashboard_update(
                    update_type="add_card",
                    session_id=session_id,
                    user_id=user_id,
                    cards=[card],
                    query_id=query_id
                )
                
                # Return success response with dashboard information
                return {
                    "success": True,
                    "query_id": query_id,
                    "chart_config": asdict(card) if card else None,
                    "dashboard_updated": True,
                    "processing_time_ms": viz_response.processing_time_ms
                }
            else:
                # Handle visualization failure
                error_card = self._create_error_card(query_id, viz_response.error_message or "Unknown error", session_id)
                
                await self.send_dashboard_update(
                    update_type="add_card",
                    session_id=session_id,
                    user_id=user_id,
                    cards=[error_card],
                    query_id=query_id
                )
                
                return {
                    "success": False,
                    "query_id": query_id,
                    "error": viz_response.error_message,
                    "dashboard_updated": True,
                    "fallback_card": asdict(error_card)
                }
                
        except Exception as e:
            logger.error(f"Error processing query for dashboard: {e}")
            return {
                "success": False,
                "query_id": query_id,
                "error": str(e),
                "dashboard_updated": False
            }
    
    def _analyze_data_for_dashboard(self, data: List[Dict[str, Any]], columns: List[str]) -> DataCharacteristics:
        """Analyze data characteristics for dashboard display"""
        from .models import DataCharacteristics
        
        if not data or not columns:
            return DataCharacteristics(
                data_type="empty",
                row_count=0,
                column_count=0,
                has_time_dimension=False,
                has_categorical_data=False,
                has_numerical_data=False,
                metric_type="unknown"
            )
        
        # Basic analysis
        row_count = len(data)
        column_count = len(columns)
        
        # Check for time dimensions
        has_time_dimension = any(
            col.lower() in ["date", "time", "period", "month", "year", "day"] or
            "date" in col.lower() or "time" in col.lower()
            for col in columns
        )
        
        # Check for categorical vs numerical data
        has_numerical_data = False
        has_categorical_data = False
        
        if data:
            first_row = data[0]
            for col in columns:
                value = first_row.get(col)
                if isinstance(value, (int, float)):
                    has_numerical_data = True
                elif isinstance(value, str):
                    has_categorical_data = True
        
        # Determine metric type from column names
        metric_type = "unknown"
        for col in columns:
            col_lower = col.lower()
            if "revenue" in col_lower or "sales" in col_lower:
                metric_type = "revenue"
                break
            elif "profit" in col_lower or "income" in col_lower:
                metric_type = "profit"
                break
            elif "expense" in col_lower or "cost" in col_lower:
                metric_type = "expenses"
                break
            elif "cash" in col_lower and "flow" in col_lower:
                metric_type = "cash_flow"
                break
        
        return DataCharacteristics(
            data_type="financial" if metric_type != "unknown" else "general",
            row_count=row_count,
            column_count=column_count,
            has_time_dimension=has_time_dimension,
            has_categorical_data=has_categorical_data,
            has_numerical_data=has_numerical_data,
            metric_type=metric_type
        )
    
    def get_session_cards(self, session_id: str) -> List[DashboardCard]:
        """Get all cards for a session"""
        return self.active_cards.get(session_id, [])
    
    def clear_session_cards(self, session_id: str):
        """Clear all cards for a session"""
        if session_id in self.active_cards:
            del self.active_cards[session_id]
            logger.info(f"Cleared dashboard cards for session {session_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dashboard integration statistics"""
        uptime = time.time() - self.start_time
        total_sessions = len(self.active_cards)
        total_cards = sum(len(cards) for cards in self.active_cards.values())
        
        return {
            "dashboard_integration": {
                "uptime": uptime,
                "active_sessions": total_sessions,
                "total_cards": total_cards,
                "cards_generated": self.cards_generated,
                "updates_sent": self.updates_sent,
                "callbacks_registered": len(self.update_callbacks)
            }
        }


# Global dashboard integration manager instance
dashboard_integration_manager = DashboardIntegrationManager()
