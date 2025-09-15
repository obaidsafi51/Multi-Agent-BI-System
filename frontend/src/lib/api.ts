import { BentoGridCard, CardType, CardSize } from "@/types/dashboard";
import { ChartType, ChartConfig } from "@/types/chart";
import { ChartConfigBuilder } from "@/lib/chartUtils";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Standardized interface matching backend models exactly
export interface QueryRequest {
  query: string;
  context?: Record<string, unknown>;
  user_id?: string;
  session_id?: string;
  metadata?: Record<string, unknown>;
}

export interface QueryIntent {
  metric_type: string;
  time_period: string;
  aggregation_level: string;
  filters?: Record<string, unknown>;
  comparison_periods?: string[];
  visualization_hint?: string;
  confidence_score?: number;
}

export interface QueryResult {
  data: unknown[];
  columns: string[];
  row_count: number;
  processing_time_ms: number;
  data_quality_score?: number;
  query_metadata?: Record<string, unknown>;
}

export interface ErrorResponse {
  error_type: string;
  message: string;
  recovery_action: string;
  suggestions?: string[];
  error_code?: string;
  context?: Record<string, unknown>;
}

export interface ProcessingMetadata {
  query_id: string;
  workflow_path: string[];
  agent_performance: Record<string, unknown>;
  total_processing_time_ms: number;
  cache_hit?: boolean;
  database_queries?: number;
}

export interface PerformanceMetrics {
  response_time_ms: number;
  memory_usage_mb?: number;
  cpu_usage_percent?: number;
  cache_hit_rate?: number;
  throughput_qps?: number;
  error_rate?: number;
}

export interface QueryResponse {
  query_id: string;
  intent: QueryIntent;
  result?: QueryResult;
  visualization?: {
    chart_type: string;
    title: string;
    config: Record<string, unknown>;
  };
  error?: ErrorResponse;
  processing_metadata?: ProcessingMetadata;
  performance_metrics?: PerformanceMetrics;
}



class ApiService {
  private baseUrl: string;
  private requestCache: Map<string, Promise<unknown>> = new Map();

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async fetchWithErrorHandling<T>(
    url: string,
    options: RequestInit = {}
  ): Promise<T> {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${url}:`, error);
      throw error;
    }
  }

  private async fetchWithDeduplication<T>(
    url: string,
    options: RequestInit = {},
    cacheKey?: string
  ): Promise<T> {
    // Create cache key from URL and method
    const key = cacheKey || `${options.method || 'GET'}:${url}`;
    
    // Check if request is already in flight
    if (this.requestCache.has(key)) {
      console.log(`Deduplicating request: ${key}`);
      return this.requestCache.get(key) as Promise<T>;
    }
    
    // Create and cache the request promise
    const requestPromise = this.fetchWithErrorHandling<T>(url, options);
    this.requestCache.set(key, requestPromise);
    
    try {
      const result = await requestPromise;
      return result;
    } finally {
      // Clean up cache after request completes
      setTimeout(() => {
        this.requestCache.delete(key);
      }, 1000); // Keep cache for 1 second to catch rapid duplicate calls
    }
  }

  async processQuery(request: QueryRequest): Promise<QueryResponse> {
    // Enhanced request with standardized format
    const enhancedRequest: QueryRequest = {
      ...request,
      user_id: request.user_id || "demo_user",
      session_id: request.session_id || crypto.randomUUID().slice(0, 8),
      metadata: {
        timestamp: Date.now(),
        source: "frontend",
        platform: "web",
        user_agent: navigator.userAgent.slice(0, 100), // Truncate for safety
        ...request.metadata
      }
    };
    
    return this.fetchWithErrorHandling<QueryResponse>(
      `${this.baseUrl}/api/query`,
      {
        method: "POST",
        body: JSON.stringify(enhancedRequest),
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      }
    );
  }

  async getDashboardLayout(layoutId: string): Promise<Record<string, unknown>> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/dashboard/${layoutId}`
    );
  }

  async saveDashboardLayout(layoutId: string, layout: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/dashboard/${layoutId}`,
      {
        method: "POST",
        body: JSON.stringify(layout),
      }
    );
  }



  async testDatabase(): Promise<Record<string, unknown>> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/database/test`
    );
  }

  async getUserProfile(): Promise<Record<string, unknown>> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/profile`
    );
  }

  async submitFeedback(feedback: {
    query_id: string;
    rating: number;
    feedback_text?: string;
  }): Promise<Record<string, unknown>> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/feedback`,
      {
        method: "POST",
        body: JSON.stringify(feedback),
      }
    );
  }

  async checkHealth(): Promise<Record<string, unknown>> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/health`
    );
  }

  // Dashboard-specific API methods
  async getDashboardCards(sessionId: string): Promise<{
    success: boolean;
    cards: BentoGridCard[];
    total_cards: number;
  }> {
    try {
      // Try to get cards from viz-agent directly
      const vizAgentUrl = process.env.NEXT_PUBLIC_VIZ_AGENT_URL || "http://localhost:8003";
      
      interface VizAgentCard {
        id: string;
        card_type: string;
        title: string;
        position: { row: number; col: number };
        size: string;
        content: Record<string, unknown>;
        metadata?: Record<string, unknown>;
      }
      
      const response = await this.fetchWithErrorHandling<{
        success: boolean;
        session_id: string;
        cards: VizAgentCard[];
        total_cards: number;
      }>(`${vizAgentUrl}/dashboard/cards/${sessionId}`);
      
      if (response.success) {
        // Transform viz-agent cards to frontend format
        const transformedCards = response.cards.map(card => this.transformVizAgentCard(card));
        
        return {
          success: true,
          cards: transformedCards,
          total_cards: response.total_cards
        };
      } else {
        return {
          success: false,
          cards: [],
          total_cards: 0
        };
      }
    } catch (error) {
      console.warn("Failed to fetch dashboard cards from viz-agent:", error);
      return {
        success: false,
        cards: [],
        total_cards: 0
      };
    }
  }

  async clearDashboardCards(sessionId: string): Promise<{ success: boolean; message: string }> {
    try {
      const vizAgentUrl = process.env.NEXT_PUBLIC_VIZ_AGENT_URL || "http://localhost:8003";
      
      const response = await this.fetchWithErrorHandling<{
        success: boolean;
        message: string;
      }>(`${vizAgentUrl}/dashboard/cards/${sessionId}`, {
        method: "DELETE"
      });
      
      return response;
    } catch (error) {
      console.warn("Failed to clear dashboard cards:", error);
      return {
        success: false,
        message: "Failed to clear dashboard cards"
      };
    }
  }

  private transformVizAgentCard(vizCard: {
    id: string;
    card_type: string;
    title: string;
    position: { row: number; col: number };
    size: string;
    content: Record<string, unknown>;
    metadata?: Record<string, unknown>;
  }): BentoGridCard {
    // Transform viz-agent card format to frontend BentoGridCard format
    const cardTypeMap: Record<string, CardType> = {
      'chart': CardType.CHART,
      'kpi': CardType.KPI,
      'table': CardType.TABLE,
      'insight': CardType.INSIGHT
    };

    const cardSizeMap: Record<string, CardSize> = {
      'small': CardSize.SMALL,
      'medium_h': CardSize.MEDIUM_H,
      'medium_v': CardSize.MEDIUM_V,
      'large': CardSize.LARGE
    };

    return {
      id: vizCard.id,
      cardType: cardTypeMap[vizCard.card_type] || CardType.CHART,
      size: cardSizeMap[vizCard.size] || CardSize.MEDIUM_H,
      position: vizCard.position,
      content: {
        ...vizCard.content,
        // Ensure required fields are present
        title: (vizCard.content.title as string) || vizCard.title,
        description: (vizCard.content.description as string) || `Generated from query ${vizCard.metadata?.query_id || 'unknown'}`
      }
    };
  }

  // WebSocket connection for real-time chat
  createWebSocketConnection(userId: string): WebSocket {
    const wsUrl = this.baseUrl.replace("http", "ws");
    return new WebSocket(`${wsUrl}/ws/chat/${userId}`);
  }

  // Transform API response data to frontend format
  transformToKpiCard(
    data: { value: number; change_percent?: number } | number,
    title: string,
    position: { row: number; col: number }
  ): BentoGridCard {
    // Handle both object and direct number input
    const value = typeof data === 'number' ? data : data.value;
    const changePercent = typeof data === 'object' && data.change_percent ? data.change_percent : 0;
    
    return {
      id: `kpi_${crypto.randomUUID()}`,
      cardType: CardType.KPI,
      size: CardSize.SMALL,
      position,
      content: {
        title,
        value: this.formatValue(value),
        label: "Current",
        change: `${changePercent > 0 ? '+' : ''}${changePercent.toFixed(1)}%`,
        trend: changePercent >= 0 ? "up" as const : "down" as const,
      },
    };
  }

  transformToChartCard(
    queryResponse: QueryResponse,
    position: { row: number; col: number }
  ): BentoGridCard {
    // Enhanced chart card transformation with better visualization support
    const visualization = queryResponse.visualization;
    const result = queryResponse.result;
    
    // Determine size early so we can pass it to the chart config builder
    const inferredSize = this.determineCardSize(visualization?.chart_type || "line", result?.row_count || 0);

    // Build a robust ChartConfig for the frontend renderer
    let chartConfig: ChartConfig | undefined = undefined;
    try {
      const columns = (result?.columns || []) as string[];
      const data = (result?.data || []) as Array<Record<string, unknown>>;

      if (columns.length >= 2 && data.length > 0) {
        const xAxisKey = columns[0];
        const yAxisKeys = columns.slice(1).filter((col) => col !== xAxisKey);

        // Infer chart type if backend didn't provide one
        const chartTypeStr = (visualization?.chart_type || "line").toLowerCase();
        const inferredType: ChartType = chartTypeStr.includes("bar")
          ? ChartType.BAR
          : chartTypeStr.includes("pie")
          ? ChartType.PIE
          : chartTypeStr.includes("area")
          ? ChartType.AREA
          : chartTypeStr.includes("scatter")
          ? ChartType.SCATTER
          : ChartType.LINE;

        chartConfig = new ChartConfigBuilder({
          data,
          xAxisKey,
          yAxisKeys,
        })
          .setType(inferredType)
          .setTitle(visualization?.title || "Chart")
          .setDimensions(inferredSize)
          .setInteractivity({ enableTooltip: true, enableLegend: true, enableAnimation: true })
          .build();
      }
    } catch (e) {
      console.warn("Failed to build chart config from result:", e);
    }

    return {
      id: `chart_${queryResponse.query_id}`,
      cardType: CardType.CHART,
      size: inferredSize,
      position,
      content: {
        title: visualization?.title || "Chart",
        chartType: visualization?.chart_type?.replace("_", " ") || "Line Chart",
        description: `Data from ${result?.row_count || 0} records`,
        data: result?.data || [],
        columns: result?.columns || [],
        chartConfig: chartConfig || (visualization?.config as ChartConfig | undefined),
        interactive: true,
        responsive: true
      },
    };
  }

  private determineCardSize(chartType: string, dataPoints: number): CardSize {
    // Intelligent card sizing based on chart type and data volume
    if (chartType.includes("gauge") || chartType.includes("kpi")) {
      return CardSize.SMALL;
    } else if (chartType.includes("table")) {
      return dataPoints > 10 ? CardSize.LARGE : CardSize.MEDIUM_H;
    } else if (chartType.includes("line") || chartType.includes("area")) {
      return CardSize.MEDIUM_H; // Horizontal medium for time series
    } else if (chartType.includes("bar") || chartType.includes("column")) {
      return CardSize.MEDIUM_V; // Vertical medium for categorical data
    } else {
      return CardSize.MEDIUM_H; // Default
    }
  }

  transformToTableCard(
    data: unknown[],
    columns: string[],
    title: string,
    position: { row: number; col: number }
  ): BentoGridCard {
    return {
      id: `table_${crypto.randomUUID()}`,
      cardType: CardType.TABLE,
      size: CardSize.LARGE,
      position,
      content: {
        title,
        headers: columns,
        rows: data.map(row => columns.map(col => (row as Record<string, unknown>)[col])),
        description: `${data.length} records`,
      },
    };
  }

  transformToInsightCard(
    message: string,
    title: string,
    position: { row: number; col: number }
  ): BentoGridCard {
    return {
      id: `insight_${crypto.randomUUID()}`,
      cardType: CardType.INSIGHT,
      size: CardSize.MEDIUM_V,
      position,
      content: {
        title,
        description: message,
      },
    };
  }

  private formatValue(value: unknown): string {
    if (typeof value === "number") {
      if (value >= 1000000) {
        return `$${(value / 1000000).toFixed(1)}M`;
      } else if (value >= 1000) {
        return `$${(value / 1000).toFixed(1)}K`;
      } else {
        return `$${value.toFixed(0)}`;
      }
    }
    return String(value);
  }
}

export const apiService = new ApiService();
