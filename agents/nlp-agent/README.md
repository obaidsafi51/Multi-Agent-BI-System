# NLP Agent with KIMI Integration

This is the Natural Language Processing (NLP) Agent for the AI-Powered CFO BI Agent system. It provides natural language query understanding, financial entity recognition, and intent extraction using the KIMI LLM API.

## Features

- **KIMI LLM Integration**: Uses KIMI API for advanced natural language understanding
- **Financial Query Parsing**: Specialized in CFO-specific financial terminology and queries
- **Intent Extraction**: Extracts structured financial intents from natural language
- **Entity Recognition**: Identifies financial entities, metrics, time periods, and departments
- **Ambiguity Detection**: Detects unclear queries and suggests clarifications
- **Context Building**: Creates structured contexts for other agents (Data, Visualization, Personalization)
- **Multi-Protocol Communication**: Supports MCP, A2A, and ACP protocols
- **Comprehensive Error Handling**: Robust error handling with retry logic and fallbacks

## Architecture

### Core Components

1. **KimiClient**: KIMI API client with authentication, retry logic, and error handling
2. **QueryParser**: Natural language query parser with preprocessing and validation
3. **ContextBuilder**: Builds structured contexts for inter-agent communication
4. **NLPAgent**: Main service orchestrating all components

### Data Models

- **QueryIntent**: Structured representation of user query intent
- **FinancialEntity**: Recognized financial terms and metrics
- **QueryContext**: Complete context information for query processing
- **ProcessingResult**: Result of NLP processing with metadata

## Installation

```bash
# Install dependencies
uv sync

# Install development dependencies
uv sync --dev
```

## Configuration

The agent uses environment variables for configuration:

```bash
# Required
KIMI_API_KEY=your_kimi_api_key
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://localhost:5672

# Optional
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-8k
```

Configuration can also be provided via `config/nlp_config.json`.

## Usage

### Running the Agent

```bash
# Start the NLP Agent
python main.py
```

### Using the NLP Agent Programmatically

```python
from src.nlp_agent import NLPAgent

# Initialize the agent
agent = NLPAgent(
    kimi_api_key="your_api_key",
    redis_url="redis://localhost:6379",
    rabbitmq_url="amqp://localhost:5672"
)

# Start the agent
await agent.start()

# Process a query
result = await agent.process_query(
    query="Show me quarterly revenue for this year",
    user_id="user123",
    session_id="session456"
)

# Get personalized suggestions
suggestions = await agent.get_query_suggestions("user123")

# Health check
health = await agent.health_check()
```

## Query Processing Flow

1. **Preprocessing**: Clean and normalize the query text
2. **Intent Extraction**: Use KIMI to extract financial intent
3. **Entity Recognition**: Identify financial entities and terms
4. **Ambiguity Detection**: Detect unclear parts and suggest clarifications
5. **Context Building**: Create structured contexts for other agents
6. **Context Storage**: Store contexts in MCP (Redis) for persistence
7. **Agent Communication**: Send contexts to other agents via A2A protocol

## Supported Financial Queries

The NLP Agent understands various types of financial queries:

### Revenue and Profit Queries

- "Show me quarterly revenue for this year"
- "Compare profit margins this quarter vs last quarter"
- "What's our gross profit trend over the last 6 months?"

### Cash Flow Queries

- "Show me operating cash flow for Q1"
- "Compare cash flow this year vs last year"
- "What's our net cash flow by month?"

### Budget and Variance Queries

- "Show me budget variance by department"
- "How are we performing against budget this quarter?"
- "Which departments are over budget?"

### Investment and ROI Queries

- "Show me investment performance"
- "What's our ROI on recent investments?"
- "Compare investment returns by category"

### Financial Ratios

- "Show me debt-to-equity ratio trend"
- "What's our current ratio?"
- "Compare financial ratios to industry benchmarks"

## Financial Terminology Support

The agent supports extensive CFO-specific terminology:

### Abbreviations

- Q1, Q2, Q3, Q4 → quarters
- YTD → year to date
- MTD → month to date
- QTD → quarter to date
- ROI → return on investment
- EBITDA → earnings before interest, taxes, depreciation, and amortization

### Metrics

- Revenue, sales, income, turnover
- Profit, net profit, gross profit
- Cash flow, operating cash flow, free cash flow
- Budget, forecast, actual vs budget
- Ratios, margins, percentages

### Time Periods

- Relative: this year, last year, this quarter, last month
- Absolute: Q1 2024, January 2024, FY2024
- Ranges: last 6 months, past 12 months, YTD

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_kimi_client.py -v
python -m pytest tests/test_query_parser.py -v
python -m pytest tests/test_context_builder.py -v
python -m pytest tests/test_integration.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Error Handling

The agent provides comprehensive error handling:

### KIMI API Errors

- Authentication errors
- Rate limiting
- Timeout handling
- Retry logic with exponential backoff

### Query Processing Errors

- Unknown financial terms → similarity matching
- Ambiguous queries → clarification suggestions
- Low confidence → validation warnings
- Missing entities → improvement suggestions

### Communication Errors

- Redis connection failures
- RabbitMQ message failures
- Context storage errors
- Agent communication timeouts

## Performance

### Response Time Targets

- 95% of queries processed in < 10 seconds
- Simple queries: < 3 seconds
- Complex queries: < 8 seconds

### Scalability

- Horizontal scaling support
- Connection pooling for Redis and RabbitMQ
- Async processing throughout
- Memory-efficient context management

## Monitoring and Observability

### Health Checks

- KIMI API connectivity
- Redis connection status
- RabbitMQ connection status
- Overall agent health

### Metrics

- Query processing times
- KIMI API usage and costs
- Error rates by type
- User satisfaction scores

### Logging

- Structured logging with context
- Query processing traces
- Error details and stack traces
- Performance metrics

## Development

### Code Structure

```
src/
├── __init__.py
├── models.py           # Pydantic data models
├── kimi_client.py      # KIMI API client
├── query_parser.py     # Query parsing logic
├── context_builder.py  # Context building for agents
└── nlp_agent.py       # Main agent service

tests/
├── test_kimi_client.py
├── test_query_parser.py
├── test_context_builder.py
├── test_nlp_agent.py
└── test_integration.py

config/
└── nlp_config.json    # Configuration file
```

### Contributing

1. Follow the existing code style (Black, isort)
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure all tests pass before submitting

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## License

This project is part of the AI-Powered CFO BI Agent system.
