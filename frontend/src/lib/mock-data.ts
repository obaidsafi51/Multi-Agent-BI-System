import { BentoGridCard, CardType, CardSize, ChatMessage, QuerySuggestion } from "@/types/dashboard";

export const mockBentoCards: BentoGridCard[] = [
  {
    id: "1",
    cardType: CardType.KPI,
    size: CardSize.SMALL,
    position: { row: 0, col: 0 },
    content: {
      title: "Revenue",
      value: "$2.4M",
      label: "This Quarter",
      change: "+12.5%",
      trend: "up"
    }
  },
  {
    id: "2",
    cardType: CardType.KPI,
    size: CardSize.SMALL,
    position: { row: 0, col: 1 },
    content: {
      title: "Net Profit",
      value: "$480K",
      label: "This Quarter",
      change: "-3.2%",
      trend: "down"
    }
  },
  {
    id: "3",
    cardType: CardType.CHART,
    size: CardSize.MEDIUM_H,
    position: { row: 0, col: 2 },
    content: {
      title: "Cash Flow Trend",
      chartType: "Line Chart",
      description: "Monthly cash flow over the last 12 months"
    }
  },
  {
    id: "4",
    cardType: CardType.KPI,
    size: CardSize.SMALL,
    position: { row: 1, col: 0 },
    content: {
      title: "Operating Expenses",
      value: "$1.2M",
      label: "This Quarter",
      change: "+5.8%",
      trend: "up"
    }
  },
  {
    id: "5",
    cardType: CardType.INSIGHT,
    size: CardSize.MEDIUM_V,
    position: { row: 1, col: 1 },
    content: {
      title: "Budget Alert",
      description: "Marketing department is 15% over budget this quarter. Consider reviewing campaign spending."
    }
  },
  {
    id: "6",
    cardType: CardType.TABLE,
    size: CardSize.LARGE,
    position: { row: 1, col: 2 },
    content: {
      title: "Top Investments",
      headers: ["Investment", "ROI", "Status"],
      rows: [
        ["Tech Upgrade", "18.5%", "Active"],
        ["Market Expansion", "12.3%", "Active"],
        ["R&D Initiative", "8.7%", "Completed"],
        ["Infrastructure", "15.2%", "Active"],
        ["Training Program", "6.4%", "Active"]
      ]
    }
  },
  {
    id: "7",
    cardType: CardType.KPI,
    size: CardSize.SMALL,
    position: { row: 2, col: 0 },
    content: {
      title: "Debt-to-Equity",
      value: "0.45",
      label: "Current Ratio",
      change: "-0.05",
      trend: "down"
    }
  },
  {
    id: "8",
    cardType: CardType.CHART,
    size: CardSize.MEDIUM_H,
    position: { row: 2, col: 1 },
    content: {
      title: "Budget vs Actual",
      chartType: "Bar Chart",
      description: "Departmental budget performance comparison"
    }
  }
];

export const mockChatMessages: ChatMessage[] = [
  {
    id: "1",
    content: "Hello! I'm your AI CFO assistant. I can help you analyze financial data, create reports, and answer questions about your business performance.",
    sender: "assistant",
    timestamp: new Date(Date.now() - 300000) // 5 minutes ago
  },
  {
    id: "2",
    content: "Show me the quarterly revenue breakdown",
    sender: "user",
    timestamp: new Date(Date.now() - 240000) // 4 minutes ago
  },
  {
    id: "3",
    content: "Here's your quarterly revenue breakdown. I've updated the dashboard with the latest data showing $2.4M in revenue with a 12.5% increase from last quarter.",
    sender: "assistant",
    timestamp: new Date(Date.now() - 180000) // 3 minutes ago
  }
];

export const mockSuggestions: QuerySuggestion[] = [
  {
    id: "1",
    text: "Show me cash flow trends",
    category: "Cash Flow",
    confidence: 0.95
  },
  {
    id: "2",
    text: "Compare this year vs last year revenue",
    category: "Revenue",
    confidence: 0.88
  },
  {
    id: "3",
    text: "What's our current debt-to-equity ratio?",
    category: "Financial Ratios",
    confidence: 0.92
  },
  {
    id: "4",
    text: "Show budget variance by department",
    category: "Budget",
    confidence: 0.85
  },
  {
    id: "5",
    text: "Investment performance summary",
    category: "Investments",
    confidence: 0.90
  }
];