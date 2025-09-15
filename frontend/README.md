# Frontend

## Overview
The Frontend for the Agentic BI system provides an intuitive, responsive user interface for interacting with the multi-agent business intelligence system. Built with modern web technologies, it offers real-time data visualization, natural language query capabilities, and interactive dashboards.

## Features
- Natural language query interface
- Real-time data visualization
- Interactive dashboards
- WebSocket-based communication for live updates
- Database connection management
- Responsive design for various devices
- Chart export and sharing capabilities
- Session management

## Technology Stack
- **Framework**: Next.js with React
- **Styling**: Tailwind CSS
- **Charts**: Dynamic charting libraries
- **Communication**: WebSocket for real-time updates
- **UI Components**: Custom component library
- **State Management**: React Context API

## Architecture
The Frontend is organized with a modern, component-based architecture:

### Core Structure
- `app/`: Next.js app router with page components
- `components/`: Reusable UI components
- `contexts/`: React context providers
- `hooks/`: Custom React hooks
- `lib/`: Utility functions and services
- `public/`: Static assets
- `styles/`: Global styles and themes
- `types/`: TypeScript type definitions

### Key Components
- `components/chat/`: Natural language query interface
- `components/charts/`: Chart rendering components
- `components/bento-grid/`: Dashboard layout system
- `components/database-selector-modal.tsx`: Database connection UI
- `components/websocket-connection-control.tsx`: WebSocket management
- `components/query-progress-display.tsx`: Query progress indicators
- `components/streaming-result-display.tsx`: Real-time result visualization

### State Management
- `contexts/DatabaseContext.tsx`: Database connection state
- `contexts/WebSocketContext.tsx`: WebSocket connection management

### Communication
- `hooks/useWebSocketClient.ts`: WebSocket client hook
- `hooks/useWebSocketQuery.ts`: WebSocket query management
- `lib/api.ts`: API client functions

## Setup and Installation
1. Ensure Node.js 18+ is installed
2. Install dependencies:
   ```bash
   npm install
   ```

## Configuration
Configure the Frontend through `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000/ws
NEXT_PUBLIC_NLP_AGENT_URL=http://localhost:8001
NEXT_PUBLIC_ENABLE_CACHE=true
```

## Running the Frontend
For development:
```bash
npm run dev
```

For production build:
```bash
npm run build
npm run start
```

Using Docker:
```bash
# Development
docker build -f Dockerfile.dev -t agentic-bi-frontend .
docker run -p 3000:3000 agentic-bi-frontend

# Production
docker build -t agentic-bi-frontend .
docker run -p 3000:3000 agentic-bi-frontend
```

## User Interface
The Frontend provides these main interface sections:
- **Natural Language Query**: Type business questions in plain English
- **Dashboard View**: Interactive, customizable dashboards
- **Database Management**: Connect and manage database connections
- **Chart Export**: Export and share visualizations
- **Settings**: Customize the user experience

## WebSocket Communication
The Frontend uses WebSockets for real-time updates:
- Live query results streaming
- Real-time chart updates
- Connection status monitoring
- Session management

## Responsive Design
The UI is fully responsive and works across:
- Desktop browsers
- Tablets
- Mobile devices

## Development
For development:
```bash
# Run ESLint
npm run lint

# Run TypeScript type checking
npm run type-check

# Run tests
npm run test
```

## Best Practices
- Use TypeScript for type safety
- Implement responsive design principles
- Use WebSockets for real-time updates
- Implement proper error handling and loading states
- Follow accessibility guidelines
- Use component composition for reusability
