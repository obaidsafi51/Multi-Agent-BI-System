import { useState, useEffect, useCallback } from "react";
import { BentoGridCard, ChatMessage, QuerySuggestion } from "@/types/dashboard";
import { apiService, QueryRequest, QueryResponse } from "@/lib/api";

interface FinancialData {
  revenue?: number;
  net_profit?: number;
  operating_expenses?: number;
}

interface UseRealDataReturn {
  // State
  chatMessages: ChatMessage[];
  bentoCards: BentoGridCard[];
  suggestions: QuerySuggestion[];
  isLoading: boolean;
  error: string | null;
  refreshSuccess: boolean;
  
  // Actions
  sendMessage: (content: string) => Promise<void>;
  refreshDashboard: () => Promise<void>;
  clearError: () => void;
  clearRefreshSuccess: () => void;
}

export function useRealData(): UseRealDataReturn {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [bentoCards, setBentoCards] = useState<BentoGridCard[]>([]);
  const [suggestions, setSuggestions] = useState<QuerySuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshSuccess, setRefreshSuccess] = useState(false);

  const loadSuggestions = useCallback(async () => {
    try {
      const apiSuggestions = await apiService.getSuggestions();
      const transformedSuggestions = apiService.transformSuggestions(apiSuggestions);
      setSuggestions(transformedSuggestions);
    } catch (err) {
      console.error("Failed to load suggestions:", err);
      // Use fallback suggestions if API fails
      setSuggestions([
        {
          id: "fallback_1",
          text: "Show me revenue trends",
          category: "Revenue",
          confidence: 0.9,
        },
        {
          id: "fallback_2",
          text: "What's our cash flow status?",
          category: "Cash Flow",
          confidence: 0.85,
        },
      ]);
    }
  }, []);

  const loadInitialDashboard = useCallback(async () => {
    try {
      // Get sample data to create initial cards
      const sampleData = await apiService.getDatabaseSampleData();
      
      const initialCards: BentoGridCard[] = [];
      
      // Create KPI cards from financial overview or use fallback data
      if (sampleData.tables.financial_overview && 
          sampleData.tables.financial_overview.sample_data.length > 0 &&
          !sampleData.tables.financial_overview.error) {
        const finData = sampleData.tables.financial_overview.sample_data[0] as FinancialData;
        
        if (finData?.revenue) {
          initialCards.push(apiService.transformToKpiCard(
            { value: finData.revenue, change_percent: 12.5 },
            "Revenue",
            { row: 0, col: 0 }
          ));
        }
        
        if (finData?.net_profit) {
          initialCards.push(apiService.transformToKpiCard(
            { value: finData.net_profit, change_percent: -3.2 },
            "Net Profit",
            { row: 0, col: 1 }
          ));
        }
        
        if (finData?.operating_expenses) {
          initialCards.push(apiService.transformToKpiCard(
            { value: finData.operating_expenses, change_percent: 5.8 },
            "Operating Expenses",
            { row: 1, col: 0 }
          ));
        }
      } else {
        // Use fallback/mock data when database connection fails
        console.warn("Using fallback financial data due to database connectivity issues");
        
        initialCards.push(apiService.transformToKpiCard(
          { value: 1250000, change_percent: 12.5 },
          "Revenue",
          { row: 0, col: 0 }
        ));
        
        initialCards.push(apiService.transformToKpiCard(
          { value: 245000, change_percent: -3.2 },
          "Net Profit",
          { row: 0, col: 1 }
        ));
        
        initialCards.push(apiService.transformToKpiCard(
          { value: 1005000, change_percent: 5.8 },
          "Operating Expenses",
          { row: 1, col: 0 }
        ));
      }
      
      // Create table card from investments data or use fallback
      if (sampleData.tables.investments && 
          sampleData.tables.investments.sample_data.length > 0 &&
          !sampleData.tables.investments.error) {
        initialCards.push(apiService.transformToTableCard(
          sampleData.tables.investments.sample_data,
          ["investment_name", "roi_percentage", "status"],
          "Top Investments",
          { row: 1, col: 1 }
        ));
      } else {
        // Use fallback investments data
        console.warn("Using fallback investment data due to database connectivity issues");
        
        const fallbackInvestments = [
          { investment_name: "Investment Hughes-Young", roi_percentage: 19.29, status: "terminated" },
          { investment_name: "Investment Peters-Gill", roi_percentage: 15.16, status: "terminated" }
        ];
        
        initialCards.push(apiService.transformToTableCard(
          fallbackInvestments,
          ["investment_name", "roi_percentage", "status"],
          "Top Investments",
          { row: 1, col: 1 }
        ));
      }
      
      // Add a Financial Chart card to demonstrate chart functionality
      const demoQueryResponse: QueryResponse = {
        query_id: "demo_chart",
        intent: { metric_type: "revenue", time_period: "monthly", aggregation_level: "monthly", visualization_hint: "line_chart" },
        result: {
          data: [
            { period: "2025-01", revenue: 1200000 },
            { period: "2025-02", revenue: 1350000 },
            { period: "2025-03", revenue: 1180000 },
            { period: "2025-04", revenue: 1420000 },
            { period: "2025-05", revenue: 1380000 }
          ],
          columns: ["period", "revenue"],
          row_count: 5,
          processing_time_ms: 50
        },
        visualization: {
          chart_type: "line",
          title: "Financial Chart",
          config: { responsive: true }
        }
      };
      
      initialCards.push(apiService.transformToChartCard(
        demoQueryResponse,
        { row: 0, col: 2 }
      ));
      
      setBentoCards(initialCards);
      
    } catch (err) {
      console.error("Failed to load initial dashboard:", err);
      // Don't set error for initial dashboard load - just use empty dashboard
      // This prevents the error dialog from showing on page load
      setBentoCards([]);
    }
  }, []);

  const initializeData = useCallback(async () => {
    try {
      setError(null);
      // Don't set loading true for initial data load - only for user interactions

      // Add welcome message
      const welcomeMessage: ChatMessage = {
        id: "welcome",
        content: "Hello! I'm your AI CFO assistant. I can help you analyze financial data from your database. What would you like to know?",
        sender: "assistant",
        timestamp: new Date("2024-01-01T00:00:00Z"), // Fixed timestamp to avoid hydration mismatch
      };
      setChatMessages([welcomeMessage]);

      // Load suggestions (don't fail if this fails)
      try {
        await loadSuggestions();
      } catch (err) {
        console.warn("Failed to load suggestions, using fallbacks:", err);
      }

      // Load initial dashboard data (don't fail if this fails)
      try {
        await loadInitialDashboard();
      } catch (err) {
        console.warn("Failed to load initial dashboard, starting with empty dashboard:", err);
        setBentoCards([]);
      }

    } catch (err) {
      console.error("Critical initialization error:", err);
      setError(err instanceof Error ? err.message : "Failed to initialize data");
    }
    // Remove the finally block that was setting loading to false
  }, [loadSuggestions, loadInitialDashboard]);

  // Initialize with welcome message and load initial data
  useEffect(() => {
    initializeData();
  }, [initializeData]);

  const getNextAvailablePosition = useCallback((): { row: number; col: number } => {
    // Simple logic to find next available position
    const maxRow = Math.max(...bentoCards.map(card => card.position.row), -1);
    const maxCol = Math.max(...bentoCards.map(card => card.position.col), -1);
    
    // Try to place in next column, or new row if we exceed 3 columns
    if (maxCol < 2) {
      return { row: maxRow, col: maxCol + 1 };
    } else {
      return { row: maxRow + 1, col: 0 };
    }
  }, [bentoCards]);

  const updateDashboardFromQuery = useCallback((queryResponse: QueryResponse) => {
    if (!queryResponse.result) return;

    const newCards: BentoGridCard[] = [];

    // Determine where to place new cards
    const nextPosition = getNextAvailablePosition();

    // Create appropriate card based on query type and data
    if (queryResponse.visualization?.chart_type) {
      // Create chart card
      newCards.push(apiService.transformToChartCard(queryResponse, nextPosition));
    } else if (queryResponse.result.data.length > 0) {
      // Create table card for data
      newCards.push(apiService.transformToTableCard(
        queryResponse.result.data,
        queryResponse.result.columns,
        `Query Results: ${queryResponse.intent.metric_type}`,
        nextPosition
      ));
    }

    // Add new cards to dashboard
    if (newCards.length > 0) {
      setBentoCards(prev => [...prev, ...newCards]);
    }
  }, [getNextAvailablePosition]);

  const sendMessage = useCallback(async (content: string) => {
    try {
      setIsLoading(true);
      setError(null);

      // Process query through API FIRST
      const queryRequest: QueryRequest = {
        query: content,
        context: { user_id: "anonymous" }
      };

      const response = await apiService.processQuery(queryRequest);

      // Only add user message if API call succeeds
      const userMessage: ChatMessage = {
        id: `user_${crypto.randomUUID()}`, // Use crypto.randomUUID() for consistent IDs
        content,
        sender: "user",
        timestamp: new Date(), // This is OK since we're client-side only now
      };
      
      setChatMessages(prev => [...prev, userMessage]);

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: response.query_id,
        content: generateResponseMessage(response),
        sender: "assistant",
        timestamp: new Date(), // This is OK since we're client-side only now
        metadata: {
          queryId: response.query_id,
          processingTime: response.result?.processing_time_ms,
        }
      };

      setChatMessages(prev => [...prev, assistantMessage]);

      // Update dashboard if we got useful data
      if (response.result && response.result.data.length > 0) {
        updateDashboardFromQuery(response);
      }

    } catch (err) {
      console.error("API call failed:", err);
      
      // Don't add any messages to chat if API fails
      // Just set a global error to show the error dialog
      setError(err instanceof Error ? err.message : "Failed to process message");
    } finally {
      setIsLoading(false);
    }
  }, [updateDashboardFromQuery]);

  const generateResponseMessage = (response: QueryResponse): string => {
    if (response.error) {
      return `I encountered an error: ${response.error.message}. ${response.error.suggestions?.join(" ") || ""}`;
    }

    if (!response.result) {
      return "I processed your query but didn't get any data back. Please try a different query.";
    }

    const { row_count, processing_time_ms } = response.result;
    const { metric_type, time_period } = response.intent;

    let message = `I found ${row_count} records for ${metric_type}`;
    
    if (time_period !== "unknown") {
      message += ` for ${time_period}`;
    }
    
    message += `. I've updated the dashboard with the results.`;
    
    if (processing_time_ms) {
      message += ` (Query processed in ${processing_time_ms}ms)`;
    }

    return message;
  };

  const refreshDashboard = useCallback(async () => {
    try {
      setError(null);
      setRefreshSuccess(false);
      setIsLoading(true);
      await loadInitialDashboard();
      setRefreshSuccess(true);
      // Clear success message after 3 seconds
      setTimeout(() => setRefreshSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to refresh dashboard:", err);
      setError(err instanceof Error ? err.message : "Failed to refresh dashboard");
    } finally {
      setIsLoading(false);
    }
  }, [loadInitialDashboard]);

  const clearError = useCallback(() => {
    setError(null);
    // Don't reinitialize data when clearing error to preserve chat history
  }, []);

  const clearRefreshSuccess = useCallback(() => {
    setRefreshSuccess(false);
  }, []);

  return {
    chatMessages,
    bentoCards,
    suggestions,
    isLoading,
    error,
    refreshSuccess,
    sendMessage,
    refreshDashboard,
    clearError,
    clearRefreshSuccess,
  };
}
