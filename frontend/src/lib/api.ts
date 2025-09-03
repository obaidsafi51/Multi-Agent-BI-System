import { BentoGridCard, ChatMessage, QuerySuggestion } from "@/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface QueryRequest {
  query: string;
  context?: Record<string, any>;
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
    data: any[];
    columns: string[];
    row_count: number;
    processing_time_ms: number;
  };
  visualization?: {
    chart_type: string;
    title: string;
    config: Record<string, any>;
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
    sample_data: any[];
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
    return this.fetchWithErrorHandling<QueryResponse>(
      `${this.baseUrl}/api/query`,
      {
        method: "POST",
        body: JSON.stringify(request),
      }
    );
  }

  async getSuggestions(): Promise<string[]> {
    return this.fetchWithErrorHandling<string[]>(
      `${this.baseUrl}/api/suggestions`
    );
  }

  async getDashboardLayout(layoutId: string): Promise<any> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/dashboard/${layoutId}`
    );
  }

  async saveDashboardLayout(layoutId: string, layout: any): Promise<any> {
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

  async testDatabase(): Promise<any> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/database/test`
    );
  }

  async getUserProfile(): Promise<any> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/profile`
    );
  }

  async submitFeedback(feedback: {
    query_id: string;
    rating: number;
    feedback_text?: string;
  }): Promise<any> {
    return this.fetchWithErrorHandling(
      `${this.baseUrl}/api/feedback`,
      {
        method: "POST",
        body: JSON.stringify(feedback),
      }
    );
  }

  async checkHealth(): Promise<any> {
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
    data: any,
    title: string,
    position: { row: number; col: number }
  ): BentoGridCard {
    return {
      id: `kpi_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      cardType: "kpi" as const,
      size: "1x1" as const,
      position,
      content: {
        title,
        value: this.formatValue(data.value),
        label: data.label || "Current",
        change: data.change_percent ? `${data.change_percent > 0 ? "+" : ""}${data.change_percent}%` : undefined,
        trend: data.change_percent ? (data.change_percent > 0 ? "up" : "down") : undefined,
      },
    };
  }

  transformToChartCard(
    queryResponse: QueryResponse,
    position: { row: number; col: number }
  ): BentoGridCard {
    return {
      id: `chart_${queryResponse.query_id}`,
      cardType: "chart" as const,
      size: "2x1" as const,
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
    data: any[],
    headers: string[],
    title: string,
    position: { row: number; col: number }
  ): BentoGridCard {
    return {
      id: `table_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      cardType: "table" as const,
      size: "2x2" as const,
      position,
      content: {
        title,
        headers,
        rows: data.map(row => headers.map(header => row[header] || "")),
      },
    };
  }

  transformToInsightCard(
    text: string,
    title: string,
    position: { row: number; col: number }
  ): BentoGridCard {
    return {
      id: `insight_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      cardType: "insight" as const,
      size: "1x2" as const,
      position,
      content: {
        title,
        description: text,
      },
    };
  }

  private formatValue(value: any): string {
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
      confidence: 0.85 + Math.random() * 0.15, // Random confidence between 0.85-1.0
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
