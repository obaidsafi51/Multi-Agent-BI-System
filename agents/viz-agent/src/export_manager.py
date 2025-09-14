"""
Export functionality for PNG, PDF, and CSV formats
"""

import logging
import os
import io
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile
from .models import ExportFormat, ExportConfig

logger = logging.getLogger(__name__)


class ExportManager:
    """Manages chart and data export functionality"""
    
    def __init__(self, export_directory: str = "/tmp/exports"):
        self.export_directory = Path(export_directory)
        self.export_directory.mkdir(parents=True, exist_ok=True)
        
        # Configure Plotly for static image export
        self._configure_plotly_export()
        
        # Supported formats and their handlers
        self.export_handlers = {
            ExportFormat.PNG: self._export_png,
            ExportFormat.PDF: self._export_pdf,
            ExportFormat.SVG: self._export_svg,
            ExportFormat.HTML: self._export_html,
            ExportFormat.CSV: self._export_csv,
            ExportFormat.EXCEL: self._export_excel,
            ExportFormat.JSON: self._export_json
        }
    
    def _configure_plotly_export(self):
        """Configure Plotly for static image export"""
        try:
            # Plotly configuration - modern approach
            # Kaleido is the default engine since v5.0
            pio.kaleido.scope.default_format = "png"
            logger.info("Plotly export engine configured successfully")
        except AttributeError:
            try:
                # Alternative configuration for older versions
                pio.orca.config.default_format = "png"
                logger.info("Plotly export engine configured with Orca")
            except AttributeError:
                # If neither work, just log a warning but don't fail
                logger.warning("Could not configure Plotly export engine - using default settings")
        except Exception as e:
            logger.warning(f"Could not configure Plotly export engine: {e}")
    
    def export_chart(self, fig: go.Figure, config: ExportConfig, 
                    data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Export chart in the specified format"""
        try:
            if config.format not in self.export_handlers:
                raise ValueError(f"Unsupported export format: {config.format}")
            
            # Generate filename with timestamp if not provided
            if not config.filename:
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                config.filename = f"chart_{timestamp}.{config.format.value}"
            
            # Ensure filename has correct extension
            if not config.filename.endswith(f".{config.format.value}"):
                config.filename = f"{config.filename}.{config.format.value}"
            
            # Call appropriate export handler
            handler = self.export_handlers[config.format]
            result = handler(fig, config, data)
            
            logger.info(f"Successfully exported chart as {config.format.value}: {config.filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error exporting chart: {str(e)}")
            raise
    
    def export_multiple_formats(self, fig: go.Figure, formats: List[ExportFormat],
                               base_filename: str, data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        """Export chart in multiple formats"""
        results = {}
        
        for format_type in formats:
            try:
                config = ExportConfig(
                    format=format_type,
                    filename=f"{base_filename}.{format_type.value}"
                )
                result = self.export_chart(fig, config, data)
                results[format_type.value] = result
            except Exception as e:
                logger.error(f"Failed to export {format_type.value}: {str(e)}")
                results[format_type.value] = {"error": str(e)}
        
        return results
    
    def _export_png(self, fig: go.Figure, config: ExportConfig, 
                   data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Export chart as PNG image"""
        filepath = self.export_directory / config.filename
        
        # Configure image dimensions
        width = config.width or 800
        height = config.height or 600
        scale = config.scale
        
        # Export using Plotly
        fig.write_image(
            str(filepath),
            format="png",
            width=width,
            height=height,
            scale=scale
        )
        
        # Get file size
        file_size = filepath.stat().st_size
        
        return {
            "format": "png",
            "filepath": str(filepath),
            "filename": config.filename,
            "file_size": file_size,
            "dimensions": {"width": width, "height": height},
            "scale": scale,
            "success": True
        }
    
    def _export_svg(self, fig: go.Figure, config: ExportConfig, 
                   data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Export chart as SVG vector image"""
        filepath = self.export_directory / config.filename
        
        # Configure image dimensions
        width = config.width or 800
        height = config.height or 600
        
        # Export using Plotly
        fig.write_image(
            str(filepath),
            format="svg",
            width=width,
            height=height
        )
        
        file_size = filepath.stat().st_size
        
        return {
            "format": "svg",
            "filepath": str(filepath),
            "filename": config.filename,
            "file_size": file_size,
            "dimensions": {"width": width, "height": height},
            "success": True
        }
    
    def _export_html(self, fig: go.Figure, config: ExportConfig, 
                    data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Export chart as interactive HTML"""
        filepath = self.export_directory / config.filename
        
        # Configure HTML export
        html_config = {
            'include_plotlyjs': True,
            'div_id': 'chart-div',
            'config': {
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
            }
        }
        
        # Generate HTML
        html_content = fig.to_html(**html_config)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        file_size = filepath.stat().st_size
        
        return {
            "format": "html",
            "filepath": str(filepath),
            "filename": config.filename,
            "file_size": file_size,
            "interactive": True,
            "success": True
        }
    
    def _export_pdf(self, fig: go.Figure, config: ExportConfig, 
                   data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Export chart as PDF with optional data table"""
        filepath = self.export_directory / config.filename
        
        # Create PDF document
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        chart_title = getattr(fig.layout, 'title', {}).get('text', 'Financial Chart')
        story.append(Paragraph(chart_title, title_style))
        story.append(Spacer(1, 12))
        
        # Export chart as PNG first, then embed in PDF
        temp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        try:
            fig.write_image(temp_png.name, format="png", width=600, height=400, scale=2)
            
            # Add chart image to PDF
            img = Image(temp_png.name, width=6*inch, height=4*inch)
            story.append(img)
            story.append(Spacer(1, 12))
            
        finally:
            os.unlink(temp_png.name)
        
        # Add data table if requested and data is provided
        if config.include_data and data:
            story.append(Paragraph("Data Table", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Convert data to table
            df = pd.DataFrame(data)
            table_data = [df.columns.tolist()] + df.head(20).values.tolist()  # Limit to 20 rows
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        
        # Build PDF
        doc.build(story)
        
        file_size = filepath.stat().st_size
        
        return {
            "format": "pdf",
            "filepath": str(filepath),
            "filename": config.filename,
            "file_size": file_size,
            "includes_data": config.include_data and data is not None,
            "success": True
        }
    
    def _export_csv(self, fig: go.Figure, config: ExportConfig, 
                   data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Export data as CSV file"""
        if not data:
            raise ValueError("No data provided for CSV export")
        
        filepath = self.export_directory / config.filename
        
        # Convert to DataFrame and export
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        file_size = filepath.stat().st_size
        row_count = len(df)
        column_count = len(df.columns)
        
        return {
            "format": "csv",
            "filepath": str(filepath),
            "filename": config.filename,
            "file_size": file_size,
            "row_count": row_count,
            "column_count": column_count,
            "success": True
        }
    
    def _export_excel(self, fig: go.Figure, config: ExportConfig, 
                     data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Export data as Excel file with chart"""
        if not data:
            raise ValueError("No data provided for Excel export")
        
        filepath = self.export_directory / config.filename
        
        # Create Excel writer
        with pd.ExcelWriter(str(filepath), engine='openpyxl') as writer:
            # Write data to first sheet
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Data', index=False)
            
            # If chart image is requested, add it to a separate sheet
            if hasattr(fig, 'layout') and fig.layout.title:
                # Export chart as image and embed
                temp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                try:
                    fig.write_image(temp_png.name, format="png", width=800, height=600)
                    
                    # Add chart sheet
                    workbook = writer.book
                    chart_sheet = workbook.create_sheet('Chart')
                    
                    # Load and insert image
                    from openpyxl.drawing import image
                    img = image.Image(temp_png.name)
                    chart_sheet.add_image(img, 'A1')
                    
                finally:
                    os.unlink(temp_png.name)
        
        file_size = filepath.stat().st_size
        
        return {
            "format": "excel",
            "filepath": str(filepath),
            "filename": config.filename,
            "file_size": file_size,
            "sheets": ["Data", "Chart"] if hasattr(fig, 'layout') else ["Data"],
            "success": True
        }
    
    def _export_json(self, fig: go.Figure, config: ExportConfig, 
                    data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Export chart configuration and data as JSON"""
        filepath = self.export_directory / config.filename
        
        # Create comprehensive JSON export
        export_data = {
            "chart_config": fig.to_dict(),
            "data": data if data else [],
            "metadata": {
                "export_timestamp": pd.Timestamp.now().isoformat(),
                "chart_type": self._detect_chart_type(fig),
                "data_points": len(data) if data else 0
            }
        }
        
        # Write JSON file
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        file_size = filepath.stat().st_size
        
        return {
            "format": "json",
            "filepath": str(filepath),
            "filename": config.filename,
            "file_size": file_size,
            "includes_chart_config": True,
            "includes_data": data is not None,
            "success": True
        }
    
    def get_export_url(self, filename: str) -> str:
        """Generate URL for accessing exported file"""
        # This would typically be a web-accessible URL
        # For now, return the file path
        return f"/exports/{filename}"
    
    def cleanup_old_exports(self, max_age_hours: int = 24):
        """Clean up old export files"""
        import time
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        cleaned_count = 0
        for filepath in self.export_directory.iterdir():
            if filepath.is_file() and filepath.stat().st_mtime < cutoff_time:
                try:
                    filepath.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Could not delete old export file {filepath}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} old export files")
        return cleaned_count
    
    def get_export_info(self, filename: str) -> Dict[str, Any]:
        """Get information about an exported file"""
        filepath = self.export_directory / filename
        
        if not filepath.exists():
            return {"error": "File not found"}
        
        stat = filepath.stat()
        
        return {
            "filename": filename,
            "filepath": str(filepath),
            "file_size": stat.st_size,
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
            "format": filepath.suffix[1:] if filepath.suffix else "unknown"
        }
    
    def _detect_chart_type(self, fig: go.Figure) -> str:
        """Detect the type of chart from the figure"""
        if not fig.data:
            return "unknown"
        
        trace_types = [trace.type for trace in fig.data if hasattr(trace, 'type')]
        
        if 'scatter' in trace_types:
            # Check if it's a line chart (scatter with lines)
            for trace in fig.data:
                if hasattr(trace, 'mode') and 'lines' in str(trace.mode):
                    return "line"
            return "scatter"
        elif 'bar' in trace_types:
            return "bar"
        elif 'pie' in trace_types:
            return "pie"
        elif 'heatmap' in trace_types:
            return "heatmap"
        elif 'table' in trace_types:
            return "table"
        else:
            return trace_types[0] if trace_types else "unknown"