# Visualization Agent

The Visualization Agent is a sophisticated component of the Agentic BI system that provides dynamic chart generation with business intelligence styling and interactive features.

## Features

### 🎯 Chart Type Selection

- **Intelligent Selection**: Automatically selects appropriate chart types based on financial data characteristics
- **Financial Metrics Mapping**: Maps business terminology to optimal visualization types
- **User Preferences**: Respects user-defined chart type preferences
- **Alternative Suggestions**: Provides alternative chart types for the same data

### 📊 Dynamic Chart Generation

- **Plotly Integration**: Uses Plotly for high-quality, interactive charts
- **Business-Specific Styling**: Professional styling with corporate, financial, and professional color schemes
- **Multiple Chart Types**: Supports line, bar, pie, area, scatter, heatmap, table, waterfall, gauge, and candlestick charts
- **Responsive Design**: Charts adapt to different screen sizes

### 🎮 Interactive Features

- **Zoom & Pan**: Enable/disable zoom and pan functionality
- **Hover Tooltips**: Customizable hover information
- **Data Selection**: Interactive data point selection
- **Drill-Down**: Hierarchical data exploration
- **Range Selectors**: Time period selection for time series data
- **Annotation Tools**: Drawing and annotation capabilities

### 📤 Export Functionality

- **Multiple Formats**: PNG, PDF, SVG, HTML, CSV, Excel, JSON
- **Batch Export**: Export charts in multiple formats simultaneously
- **Data Inclusion**: Option to include raw data in exports
- **Custom Sizing**: Configurable export dimensions and scaling

### ⚡ Performance Optimization

- **Large Dataset Handling**: Automatic data sampling for large datasets
- **Chart-Specific Limits**: Optimized limits for different chart types
- **Memory Management**: Memory usage monitoring and optimization
- **Caching**: Response caching for improved performance

## Architecture

```
src/
├── models.py                    # Data models and types
├── chart_selector.py           # Chart type selection logic
├── chart_generator.py          # Chart generation with Plotly
├── interactive_features.py     # Interactive functionality
├── export_manager.py           # Export functionality
├── performance_optimizer.py    # Performance optimization
└── visualization_agent.py      # Main agent orchestration
```

## Usage

### Basic Usage

```python
from src.visualization_agent import VisualizationAgent
from src.models import VisualizationRequest

# Create agent
agent = VisualizationAgent()

# Create request
request = VisualizationRequest(
    request_id="example_001",
    user_id="business_user",
    query_intent={
        "metric_type": "revenue",
        "time_period": "monthly"
    },
    data=[
        {"month": "Jan", "revenue": 100000},
        {"month": "Feb", "revenue": 120000},
        {"month": "Mar", "revenue": 110000}
    ]
)

# Process request
response = await agent.process_visualization_request(request)

if response.success:
    print(f"Chart generated successfully!")
    print(f"Processing time: {response.processing_time_ms}ms")
    # Use response.chart_html for display
    # Use response.chart_json for programmatic access
```

### With User Preferences

```python
request = VisualizationRequest(
    request_id="example_002",
    user_id="business_user",
    query_intent={"metric_type": "budget_variance"},
    data=[
        {"department": "Sales", "budget": 100000, "actual": 95000},
        {"department": "Marketing", "budget": 50000, "actual": 55000}
    ],
    preferences={
        "preferred_chart_type": "bar",
        "color_scheme": "financial",
        "enable_zoom": True,
        "show_legend": True
    }
)
```

### With Export Configuration

```python
from src.models import ExportConfig, ExportFormat

request = VisualizationRequest(
    request_id="example_003",
    user_id="business_user",
    query_intent={"metric_type": "cash_flow"},
    data=cash_flow_data,
    export_config=ExportConfig(
        format=ExportFormat.PDF,
        filename="cash_flow_report.pdf",
        include_data=True
    )
)
```

## Chart Types and Use Cases

| Chart Type  | Best For              | Financial Use Cases                  |
| ----------- | --------------------- | ------------------------------------ |
| Line        | Time series trends    | Revenue over time, stock prices      |
| Bar/Column  | Category comparisons  | Department budgets, regional sales   |
| Pie         | Composition           | Expense breakdown, market share      |
| Area        | Cumulative values     | Cumulative revenue, portfolio growth |
| Scatter     | Correlations          | Marketing spend vs revenue           |
| Heatmap     | Matrix data           | Performance by region/product        |
| Table       | Detailed data         | Financial statements, transactions   |
| Waterfall   | Flow analysis         | Cash flow changes, profit bridges    |
| Gauge       | KPIs                  | Performance indicators, ratios       |
| Candlestick | Financial time series | Stock price movements                |

## Performance Optimization

The agent automatically optimizes performance based on data size:

- **Small datasets** (< 10,000 points): No optimization
- **Large datasets** (> 10,000 points): Intelligent sampling
- **Very large datasets** (> 50,000 points): Aggressive optimization

### Optimization Strategies

- **Time-based sampling**: For time series data
- **Top-N sampling**: For categorical data (bars, pies)
- **Random sampling**: For scatter plots
- **Grid-based sampling**: For heatmaps
- **Pagination**: For tables

## Testing

Run the validation script to check implementation:

```bash
python3 validate_implementation.py
```

Run unit tests (requires dependencies):

```bash
python3 run_tests.py
```

## Dependencies

- **plotly**: Chart generation
- **pandas**: Data manipulation
- **numpy**: Numerical operations
- **pydantic**: Data validation
- **redis**: Caching
- **pika**: Message queuing
- **reportlab**: PDF generation
- **openpyxl**: Excel export
- **psutil**: Performance monitoring
- **kaleido**: Static image export

## Configuration

Environment variables:

- `REDIS_URL`: Redis connection URL
- `RABBITMQ_URL`: RabbitMQ connection URL

## Error Handling

The agent provides comprehensive error handling:

- **Data validation errors**: Invalid or empty data
- **Chart generation errors**: Unsupported chart types
- **Export errors**: File system or format issues
- **Performance errors**: Memory or timeout issues

All errors are logged and returned in the response with descriptive messages.

## Integration

The Visualization Agent integrates with:

- **NLP Agent**: Receives processed query intents
- **Data Agent**: Receives structured data
- **Personalization Agent**: Applies user preferences
- **Frontend**: Provides HTML and JSON chart representations

## Future Enhancements

- Real-time data streaming
- Advanced statistical visualizations
- Custom chart templates
- Collaborative features
- Mobile optimization
- Accessibility improvements
