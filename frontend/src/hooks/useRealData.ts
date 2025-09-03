import { useState, useEffect, useCallback } from "react";
import { BentoGridCard, ChatMessage, QuerySuggestion } from "@/types/dashboard";
import { apiService, QueryRequest, QueryResponse } from "@/lib/api";

interface UseRealDataReturn {
  // State
  chatMessages: ChatMessage[];
  bentoCards: BentoGridCard[];
  suggestions: QuerySuggestion[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  sendMessage: (content: string) => Promise<void>;
  refreshDashboard: () => Promise<void>;
  clearError: () => void;
}

export function useRealData(): UseRealDataReturn {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [bentoCards, setBentoCards] = useState<BentoGridCard[]>([]);
  const [suggestions, setSuggestions] = useState<QuerySuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize with welcome message and load initial data
  useEffect(() => {
    initializeData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const initializeData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Add welcome message
      const welcomeMessage: ChatMessage = {
        id: "welcome",
        content: "Hello! I'm your AI CFO assistant. I can help you analyze financial data from your database. What would you like to know?",
        sender: "assistant",
        timestamp: new Date(),
      };
      setChatMessages([welcomeMessage]);

      // Load suggestions
      await loadSuggestions();

      // Load initial dashboard data
      await loadInitialDashboard();

    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to initialize data");
    } finally {
      setIsLoading(false);
    }
  };

  const loadSuggestions = async () => {
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
  };

  const loadInitialDashboard = async () => {
    try {
      // Get sample data to create initial cards
      const sampleData = await apiService.getDatabaseSampleData();
      
      const initialCards: BentoGridCard[] = [];
      
      // Create KPI cards from financial overview
      if (sampleData.tables.financial_overview && sampleData.tables.financial_overview.sample_data.length > 0) {
        const finData = sampleData.tables.financial_overview.sample_data[0];
        
        if (finData.revenue) {
          initialCards.push(apiService.transformToKpiCard(
            { value: finData.revenue, change_percent: 12.5 },
            "Revenue",
            { row: 0, col: 0 }
          ));
        }
        
        if (finData.net_profit) {
          initialCards.push(apiService.transformToKpiCard(
            { value: finData.net_profit, change_percent: -3.2 },
            "Net Profit",
            { row: 0, col: 1 }
          ));
        }
        
        if (finData.operating_expenses) {
          initialCards.push(apiService.transformToKpiCard(
            { value: finData.operating_expenses, change_percent: 5.8 },
            "Operating Expenses",
            { row: 1, col: 0 }
          ));
        }
      }
      
      // Create table card from investments data
      if (sampleData.tables.investments && sampleData.tables.investments.sample_data.length > 0) {
        initialCards.push(apiService.transformToTableCard(
          sampleData.tables.investments.sample_data,
          ["investment_name", "roi_percentage", "status"],
          "Top Investments",
          { row: 1, col: 1 }
        ));
      }
      
      setBentoCards(initialCards);
      
    } catch (err) {
      console.error("Failed to load initial dashboard:", err);
      // Create a single error card
      setBentoCards([
        apiService.transformToInsightCard(
          "Unable to connect to database. Please check your connection and try again.",
          "Connection Error",
          { row: 0, col: 0 }
        )
      ]);
    }
  };

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

      // Add user message immediately
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        content,
        sender: "user",
        timestamp: new Date(),
      };
      
      setChatMessages(prev => [...prev, userMessage]);

      // Process query through API
      const queryRequest: QueryRequest = {
        query: content,
        context: { user_id: "anonymous" }
      };

      const response = await apiService.processQuery(queryRequest);

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
      setError(err instanceof Error ? err.message : "Failed to process message");
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        content: "I'm sorry, I encountered an error processing your request. Please try again.",
        sender: "assistant",
        timestamp: new Date(),
      };
      
      setChatMessages(prev => [...prev, errorMessage]);
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
    await loadInitialDashboard();
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    chatMessages,
    bentoCards,
    suggestions,
    isLoading,
    error,
    sendMessage,
    refreshDashboard,
    clearError,
  };
}
