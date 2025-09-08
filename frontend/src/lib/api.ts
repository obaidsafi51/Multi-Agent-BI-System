import { BentoGridCard, QuerySuggestion, CardType, CardSize } from "@/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface QueryRequest {
  query: string;
  context?: Record<string, unknown>;
}

export interface QueryResponse {
  query_id: string;
  intent: {
    metric_type: string;
    time_period: string;
    aggregation_level: string;
    visualization_hint: string;
  };
  result?: {
    data: unknown[];
    columns: string[];
    row_count: number;
    processing_time_ms: number;
  };
  visualization?: {
    chart_type: string;
    title: string;
    config: Record<string, unknown>;
  };
  error?: {
    error_type: string;
    message: string;
    recovery_action: string;
    suggestions: string[];
  };
}

export interface DatabaseSampleData {
  connection_status: string;
  database_info: {
    name: string;
    type: string;
  };
  tables: Record<string, {
    total_records: number;
    sample_data: unknown[];
    sample_count: number;
    error?: string;
  }>;
}

class ApiService {
  private baseUrl: string;

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

  async processQuery(request: QueryRequest): Promise<QueryResponse> {
    // Simplified request without query modification
    const enhancedRequest = {
      ...request,
      metadata: {
        timestamp: Date.now(),
        source: "frontend",
        user_id: "demo_user",
        session_id: crypto.randomUUID().slice(0, 8)
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

  async getSuggestions(): Promise<string[]> {
    return this.fetchWithErrorHandling<string[]>(
      `${this.baseUrl}/api/suggestions`
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

  async getDatabaseSampleData(): Promise<DatabaseSampleData> {
    return this.fetchWithErrorHandling<DatabaseSampleData>(
      `${this.baseUrl}/api/database/sample-data`
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

  // WebSocket connection for real-time chat
  createWebSocketConnection(userId: string): WebSocket {
    const wsUrl = this.baseUrl.replace("http", "ws");
    return new WebSocket(`${wsUrl}/ws/chat/${userId}`);
  }

  // Transform API response data to frontend format
  transformToKpiCard(
    data: unknown,
    title: string,
    position: { row: number; col: number }
  ): BentoGridCard {
    return {
      id: `kpi_${crypto.randomUUID()}`,
      cardType: CardType.KPI,
      size: CardSize.SMALL,
      position,
      content: {
        title,
        value: this.formatValue(data),
        label: "Current",
        change: "+12.5%",
        trend: "up" as const,
      },
    };
  }

  transformToChartCard(
    queryResponse: QueryResponse,
    position: { row: number; col: number }
  ): BentoGridCard {
    return {
      id: `chart_${queryResponse.query_id}`,
      cardType: CardType.CHART,
      size: CardSize.MEDIUM_H,
      position,
      content: {
        title: queryResponse.visualization?.title || "Chart",
        chartType: queryResponse.visualization?.chart_type || "Line Chart",
        description: `Data from ${queryResponse.result?.row_count || 0} records`,
        data: queryResponse.result?.data || [],
        columns: queryResponse.result?.columns || [],
      },
    };
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

  // Convert API suggestions to frontend format
  transformSuggestions(apiSuggestions: string[]): QuerySuggestion[] {
    return apiSuggestions.map((text, index) => ({
      id: `suggestion_${index}`,
      text,
      category: this.categorizeQuery(text),
      confidence: 0.9, // Use fixed confidence value to avoid hydration mismatch
    }));
  }

  private categorizeQuery(query: string): string {
    const lowerQuery = query.toLowerCase();
    
    if (lowerQuery.includes("revenue") || lowerQuery.includes("sales")) {
      return "Revenue";
    } else if (lowerQuery.includes("cash flow") || lowerQuery.includes("cash")) {
      return "Cash Flow";
    } else if (lowerQuery.includes("budget") || lowerQuery.includes("expense")) {
      return "Budget";
    } else if (lowerQuery.includes("investment") || lowerQuery.includes("roi")) {
      return "Investments";
    } else if (lowerQuery.includes("ratio") || lowerQuery.includes("debt")) {
      return "Financial Ratios";
    } else {
      return "General";
    }
  }
}

export const apiService = new ApiService();
