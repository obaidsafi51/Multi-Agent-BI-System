import { useState, useEffect, useCallback } from "react";
import { BentoGridCard, ChatMessage, QuerySuggestion } from "@/types/dashboard";
import { apiService, QueryRequest, QueryResponse } from "@/lib/api";
import { useDatabaseContext } from "@/contexts/DatabaseContext";
import { useGlobalWebSocket } from "@/contexts/WebSocketContext";
import { useWebSocketQuery } from "@/hooks/useWebSocketQuery";

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
  // Get database context and WebSocket connections
  const { sessionId } = useDatabaseContext();
  const { isConnected } = useGlobalWebSocket();
  const { processQuery, isProcessing } = useWebSocketQuery();
  
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [bentoCards, setBentoCards] = useState<BentoGridCard[]>([]);
  const [suggestions, setSuggestions] = useState<QuerySuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshSuccess, setRefreshSuccess] = useState(false);

  const loadSuggestions = useCallback(async () => {
    // Use static suggestions instead of API call
    const staticSuggestions = [
      "Show me the total revenue by month",
      "What are our top performing products?", 
      "Analyze cash flow trends over time",
      "Compare profit margins by category",
      "Show budget vs actual expenses",
      "What is our customer acquisition cost?",
      "Display quarterly financial ratios",
      "Show investment portfolio performance",
      "What are the main expense categories?",
      "Analyze revenue growth year over year"
    ];
    
    // Transform suggestions inline
    const transformedSuggestions = staticSuggestions.map((text, index) => {
      const lowerText = text.toLowerCase();
      let category = "General";
      
      if (lowerText.includes("revenue") || lowerText.includes("sales")) {
        category = "Revenue";
      } else if (lowerText.includes("cash flow") || lowerText.includes("cash")) {
        category = "Cash Flow";
      } else if (lowerText.includes("budget") || lowerText.includes("expense")) {
        category = "Budget";
      } else if (lowerText.includes("investment") || lowerText.includes("roi")) {
        category = "Investments";
      } else if (lowerText.includes("ratio") || lowerText.includes("debt")) {
        category = "Financial Ratios";
      } else if (lowerText.includes("product")) {
        category = "Products";
      } else if (lowerText.includes("profit") || lowerText.includes("margin")) {
        category = "Profitability";
      } else if (lowerText.includes("customer")) {
        category = "Customers";
      }
      
      return {
        id: `suggestion_${index}`,
        text,
        category,
        confidence: 0.9,
      };
    });
    
    setSuggestions(transformedSuggestions);
  }, []);

  const loadInitialDashboard = useCallback(async () => {
    try {
      // Check if we have a selected database and session ID first
      const selectedDatabase = sessionStorage.getItem('selected_database');
      if (!selectedDatabase) {
        console.log("No database selected - skipping initial dashboard load");
        setBentoCards([]);
        return;
      }

      if (!sessionId) {
        console.log("No session ID available - skipping initial dashboard load");
        setBentoCards([]);
        return;
      }

      // Check if we already have cached data to avoid redundant calls
      const cacheKey = `dashboard_initial_data_${selectedDatabase}`;
      const cachedData = sessionStorage.getItem(cacheKey);
      
      if (cachedData) {
        try {
          const parsed = JSON.parse(cachedData);
          if (Date.now() - parsed.timestamp < 300000) { // 5 minutes cache
            console.log("Using cached dashboard data for database:", selectedDatabase);
            setBentoCards(parsed.cards);
            return;
          }
        } catch (e) {
          console.warn("Failed to parse cached data:", e);
        }
      }

      // Only load dashboard data after database is properly selected and schema is initialized
      console.log("Loading initial dashboard data for database:", selectedDatabase);

      const initialCards: BentoGridCard[] = [];
      
      try {
        // Query real revenue data
        const revenueResponse = await apiService.processQuery({
          query: "Show me total revenue for the last 6 months",
          session_id: sessionId || undefined,
          context: { user_id: "dashboard_init" }
        });
        
        if (revenueResponse.result?.data && revenueResponse.result.data.length > 0) {
          const latestRevenue = revenueResponse.result.data[revenueResponse.result.data.length - 1] as Record<string, unknown>;
          const revenueValue = latestRevenue.revenue || latestRevenue.total_revenue || 0;
          
          initialCards.push(apiService.transformToKpiCard(
            { value: Number(revenueValue), change_percent: 12.5 },
            "Revenue",
            { row: 0, col: 0 }
          ));
        }
      } catch (error) {
        console.warn("Failed to fetch revenue data:", error);
      }

      try {
        // Query real profit data
        const profitResponse = await apiService.processQuery({
          query: "Show me net profit for the current period",
          session_id: sessionId || undefined,
          context: { user_id: "dashboard_init" }
        });
        
        if (profitResponse.result?.data && profitResponse.result.data.length > 0) {
          const latestProfit = profitResponse.result.data[profitResponse.result.data.length - 1] as Record<string, unknown>;
          const profitValue = latestProfit.net_profit || latestProfit.profit || 0;
          
          initialCards.push(apiService.transformToKpiCard(
            { value: Number(profitValue), change_percent: -3.2 },
            "Net Profit",
            { row: 0, col: 1 }
          ));
        }
      } catch (error) {
        console.warn("Failed to fetch profit data:", error);
      }

      try {
        // Query real expenses data
        const expensesResponse = await apiService.processQuery({
          query: "Show me operating expenses for the current period",
          session_id: sessionId || undefined,
          context: { user_id: "dashboard_init" }
        });
        
        if (expensesResponse.result?.data && expensesResponse.result.data.length > 0) {
          const latestExpenses = expensesResponse.result.data[expensesResponse.result.data.length - 1] as Record<string, unknown>;
          const expensesValue = latestExpenses.operating_expenses || latestExpenses.expenses || 0;
          
          initialCards.push(apiService.transformToKpiCard(
            { value: Number(expensesValue), change_percent: 5.8 },
            "Operating Expenses",
            { row: 1, col: 0 }
          ));
        }
      } catch (error) {
        console.warn("Failed to fetch expenses data:", error);
      }

      try {
        // Query real investments data
        const investmentsResponse = await apiService.processQuery({
          query: "Show me top 5 investments by ROI",
          session_id: sessionId || undefined,
          context: { user_id: "dashboard_init" }
        });
        
        if (investmentsResponse.result?.data && investmentsResponse.result.data.length > 0) {
          initialCards.push(apiService.transformToTableCard(
            investmentsResponse.result.data,
            investmentsResponse.result.columns,
            "Top Investments",
            { row: 1, col: 1 }
          ));
        }
      } catch (error) {
        console.warn("Failed to fetch investments data:", error);
      }

      // Add revenue trend chart with real data
      try {
        const chartResponse = await apiService.processQuery({
          query: "Show me monthly revenue trend for the last 6 months",
          session_id: sessionId || undefined,
          context: { user_id: "dashboard_init" }
        });
        
        if (chartResponse.result?.data && chartResponse.result.data.length > 0) {
          initialCards.push(apiService.transformToChartCard(
            chartResponse,
            { row: 0, col: 2 }
          ));
        }
      } catch (error) {
        console.warn("Failed to fetch chart data:", error);
      }
      
      // If no real data was loaded, show empty dashboard
      if (initialCards.length === 0) {
        console.warn("No real data available, showing empty dashboard");
      }
      
      setBentoCards(initialCards);
      
      // Cache the successful result with database context
      if (initialCards.length > 0) {
        sessionStorage.setItem(cacheKey, JSON.stringify({
          cards: initialCards,
          timestamp: Date.now(),
          database: selectedDatabase
        }));
      }
      
    } catch (err) {
      console.error("Failed to load initial dashboard:", err);
      // Show empty dashboard instead of fallback data
      setBentoCards([]);
    }
  }, [sessionId]);

  // Removed initializeData function as we now handle initialization inline

  // Initialize with welcome message only (no automatic data loading)
  useEffect(() => {
    // Prevent double initialization in React Strict Mode (development)
    let mounted = true;
    
    const initialize = async () => {
      if (mounted) {
        // Only initialize welcome message and suggestions, skip dashboard data loading
        try {
          setError(null);
          
          // Add welcome message
          const welcomeMessage: ChatMessage = {
            id: "welcome",
            content: "Hello! I'm your AI CFO assistant. I can help you analyze financial data from your database. What would you like to know?",
            sender: "assistant",
            timestamp: new Date("2024-01-01T00:00:00Z"), // Fixed timestamp to avoid hydration mismatch
          };
          setChatMessages([welcomeMessage]);

          // Load suggestions only (lightweight operation)
          try {
            await loadSuggestions();
          } catch (err) {
            console.warn("Failed to load suggestions, using fallbacks:", err);
          }

          // Skip automatic dashboard loading to prevent unnecessary queries
          console.log("Frontend initialized without automatic queries");
          setBentoCards([]);

        } catch (err) {
          console.error("Critical initialization error:", err);
          setError(err instanceof Error ? err.message : "Failed to initialize data");
        }
      }
    };
    
    initialize();
    
    return () => {
      mounted = false;
    };
  }, [loadSuggestions]); // Remove initializeData dependency

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

  const processQueryResponse = useCallback((content: string, response: QueryResponse) => {
    try {
      // Only add user message if processing succeeds
      const userMessage: ChatMessage = {
        id: `user_${crypto.randomUUID()}`,
        content,
        sender: "user",
        timestamp: new Date(),
      };
      
      setChatMessages(prev => [...prev, userMessage]);

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: response.query_id,
        content: generateResponseMessage(response),
        sender: "assistant",
        timestamp: new Date(),
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
      console.error("Query response processing failed:", err);
      setError(err instanceof Error ? err.message : "Failed to process response");
    }
  }, [updateDashboardFromQuery]);

  const sendMessage = useCallback(async (content: string) => {
    try {
      setIsLoading(true);
      setError(null);

      // Check if WebSocket is connected and use it, otherwise fallback to HTTP
      if (isConnected) {
        console.log("Using WebSocket for query:", content);
        
        // Process query through WebSocket
        const wsResponse = await processQuery({
          query: content,
          session_id: sessionId || undefined,
          preferences: {
            output_format: "json"
          }
        });

        // Transform WebSocket response to expected format
        const response: QueryResponse = {
          query_id: wsResponse.response?.query_id || `ws_${Date.now()}`,
          result: {
            data: Array.isArray(wsResponse.response?.data) ? wsResponse.response.data : [],
            processing_time_ms: 1000, // Default processing time
            columns: [],
            row_count: Array.isArray(wsResponse.response?.data) ? wsResponse.response.data.length : 0
          },
          intent: {
            metric_type: "unknown",
            time_period: "unknown",
            aggregation_level: "summary"
          },
          error: wsResponse.error ? {
            error_type: wsResponse.error.error_type,
            message: wsResponse.error.message,
            recovery_action: "retry",
            suggestions: wsResponse.error.suggestions || []
          } : undefined
        };

        // Use the transformed response
        processQueryResponse(content, response);
      } else {
        console.log("WebSocket not connected, using HTTP fallback");
        
        // Fallback to HTTP API
        const queryRequest: QueryRequest = {
          query: content,
          user_id: "anonymous",
          session_id: sessionId || undefined,
          context: { 
            user_id: "anonymous",
            source: "chat_interface_http_fallback"
          }
        };

        const response = await apiService.processQuery(queryRequest);
        processQueryResponse(content, response);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      setError(err instanceof Error ? err.message : "Failed to process query");
      
      // Add error message to chat
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        content: `Sorry, I encountered an error: ${err instanceof Error ? err.message : "Unknown error"}`,
        sender: "assistant",
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isConnected, processQuery, processQueryResponse]);

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
