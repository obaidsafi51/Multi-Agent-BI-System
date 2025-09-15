/**
 * WebSocket Types for Real-time Communication
 * Frontend types for WebSocket-based query processing and progress updates
 */

// Connection States
export enum WebSocketConnectionState {
  CONNECTING = "connecting",
  CONNECTED = "connected",
  DISCONNECTED = "disconnected",
  ERROR = "error",
  RECONNECTING = "reconnecting"
}

// Message Types matching backend implementation
export enum WebSocketMessageType {
  // System messages
  SYSTEM = "system",
  PING = "ping",
  PONG = "pong",
  
  // Query processing
  QUERY = "query",
  QUERY_PROGRESS = "query_progress",
  QUERY_RESULT = "query_result",
  QUERY_ERROR = "query_error",
  
  // Metrics and monitoring
  METRICS = "metrics",
  CONNECTION_STATUS = "connection_status"
}

// Base WebSocket Message
export interface WebSocketMessage {
  type: WebSocketMessageType;
  timestamp: string;
  data?: Record<string, unknown>;
}

// System Messages
export interface SystemMessage extends WebSocketMessage {
  type: WebSocketMessageType.SYSTEM;
  message: string;
}

export interface PingMessage extends WebSocketMessage {
  type: WebSocketMessageType.PING;
}

export interface PongMessage extends WebSocketMessage {
  type: WebSocketMessageType.PONG;
}

// Query Messages
export interface QueryMessage extends WebSocketMessage {
  type: WebSocketMessageType.QUERY;
  message: string;
  query_id?: string;
  session_id?: string;
  database_context?: {
    database_name: string;
    session_id: string;
    [key: string]: unknown;
  };
}

export interface QueryProgressMessage extends WebSocketMessage {
  type: WebSocketMessageType.QUERY_PROGRESS;
  query_id: string;
  step: string;
  status: QueryProgressStatus;
  progress: number; // 0-100
  estimated_time_remaining?: number; // seconds
  data?: {
    current_agent?: string;
    processing_stage?: string;
    error?: string;
    [key: string]: unknown;
  };
}

export interface QueryResultMessage extends WebSocketMessage {
  type: WebSocketMessageType.QUERY_RESULT;
  query_id: string;
  result: {
    response: string;
    chart_type?: string;
    chart_data?: unknown;
    table_data?: {
      headers: string[];
      rows: unknown[][];
    };
    sql_query?: string;
    execution_time?: number;
    [key: string]: unknown;
  };
}

export interface QueryErrorMessage extends WebSocketMessage {
  type: WebSocketMessageType.QUERY_ERROR;
  query_id: string;
  error: string;
  step?: string;
  error_code?: string;
}

// Connection and Metrics
export interface ConnectionStatusMessage extends WebSocketMessage {
  type: WebSocketMessageType.CONNECTION_STATUS;
  status: WebSocketConnectionState;
  user_id: string;
}

export interface MetricsMessage extends WebSocketMessage {
  type: WebSocketMessageType.METRICS;
  data: {
    total_queries: number;
    successful_queries: number;
    failed_queries: number;
    average_response_time: number;
    connection_uptime: number;
    [key: string]: unknown;
  };
}

// Query Progress Status
export enum QueryProgressStatus {
  QUEUED = "queued",
  PROCESSING = "processing",
  ANALYZING = "analyzing",
  GENERATING_SQL = "generating_sql",
  EXECUTING_QUERY = "executing_query",
  GENERATING_VISUALIZATION = "generating_visualization",
  COMPLETED = "completed",
  ERROR = "error"
}

// Progress Step Information
export interface QueryProgressStep {
  step: string;
  label: string;
  description: string;
  estimated_duration: number; // seconds
  icon?: string;
}

// Predefined progress steps matching backend orchestration
export const QUERY_PROGRESS_STEPS: Record<string, QueryProgressStep> = {
  nlp_processing: {
    step: "nlp_processing",
    label: "Understanding Query",
    description: "AI is analyzing your request",
    estimated_duration: 2,
    icon: "🧠"
  },
  schema_discovery: {
    step: "schema_discovery",
    label: "Discovering Data",
    description: "Finding relevant tables and columns",
    estimated_duration: 1,
    icon: "🔍"
  },
  sql_generation: {
    step: "sql_generation",
    label: "Generating SQL",
    description: "Creating optimized database query",
    estimated_duration: 8,
    icon: "⚡"
  },
  query_execution: {
    step: "query_execution",
    label: "Executing Query",
    description: "Running query against database",
    estimated_duration: 3,
    icon: "🔄"
  },
  data_processing: {
    step: "data_processing",
    label: "Processing Results",
    description: "Analyzing and formatting data",
    estimated_duration: 2,
    icon: "📊"
  },
  visualization: {
    step: "visualization",
    label: "Creating Visualization",
    description: "Generating charts and insights",
    estimated_duration: 2,
    icon: "📈"
  }
};

// WebSocket Client Configuration
export interface WebSocketClientConfig {
  url: string;
  user_id: string;
  reconnectInterval: number; // milliseconds
  maxReconnectAttempts: number;
  pingInterval: number; // milliseconds
  connectionTimeout: number; // milliseconds
}

// WebSocket Client State
export interface WebSocketClientState {
  connectionState: WebSocketConnectionState;
  isConnected: boolean;
  reconnectAttempts: number;
  lastPingTime: number | null;
  latency: number | null;
  metrics: {
    messagesReceived: number;
    messagesSent: number;
    reconnectCount: number;
    connectionUptime: number;
  };
}

// Query State Management
export interface QueryState {
  query_id: string;
  query_text: string;
  status: QueryProgressStatus;
  progress: number;
  current_step?: string;
  estimated_time_remaining?: number;
  start_time: number;
  result?: QueryResultMessage['result'];
  error?: string;
}

// WebSocket Hook Return Type
export interface UseWebSocketReturn {
  // Connection state
  connectionState: WebSocketConnectionState;
  isConnected: boolean;
  metrics: WebSocketClientState['metrics'];
  latency: number | null;
  
  // Query management
  activeQueries: Map<string, QueryState>;
  sendQuery: (query: string, sessionId?: string, databaseContext?: { database_name: string; session_id: string; [key: string]: unknown }) => string; // returns query_id
  cancelQuery: (queryId: string) => void;
  
  // Connection management
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  
  // Utilities
  sendMessage: (message: WebSocketMessage) => void;
  requestMetrics: () => void;
}

// Streaming Result Types
export interface StreamingResultData {
  query_id: string;
  type: 'partial' | 'complete';
  data: {
    rows?: unknown[][];
    chart_data?: unknown;
    progress?: number;
    [key: string]: unknown;
  };
}

// Real-time Progress Display Props
export interface QueryProgressDisplayProps {
  queryState: QueryState;
  showEstimatedTime?: boolean;
  showDetailedSteps?: boolean;
  compact?: boolean;
}

// Connection Status Indicator Props
export interface WebSocketConnectionStatusProps {
  connectionState: WebSocketConnectionState;
  latency?: number | null;
  showDetails?: boolean;
  size?: 'sm' | 'md' | 'lg';
}
