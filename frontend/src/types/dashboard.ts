export enum CardSize {
  SMALL = "1x1",      // KPI cards
  MEDIUM_H = "2x1",   // Horizontal charts, insights
  MEDIUM_V = "1x2",   // Vertical charts
  LARGE = "2x2",      // Complex charts, tables
  EXTRA_LARGE = "3x2" // Large tables, dashboards
}

export enum CardType {
  KPI = "kpi",
  CHART = "chart",
  TABLE = "table",
  INSIGHT = "insight",
  CUSTOM = "custom"
}

export interface CardContent {
  title: string;
  value?: string;
  label?: string;
  change?: string;
  trend?: "up" | "down";
  chartType?: string;
  description?: string;
  headers?: string[];
  rows?: unknown[][];
  [key: string]: unknown;
}

export interface BentoGridCard {
  id: string;
  cardType: CardType;
  size: CardSize;
  position: { row: number; col: number };
  content: CardContent;
  styling?: Record<string, unknown>;
  isDraggable?: boolean;
  isResizable?: boolean;
}

export interface BentoGridLayout {
  layoutId: string;
  userId: string;
  gridColumns: number;
  cards: BentoGridCard[];
  layoutName: string;
  isDefault: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface DragDropConfig {
  enableDrag: boolean;
  enableResize: boolean;
  snapToGrid: boolean;
  collisionDetection: boolean;
  animationDuration: number;
}

export interface ChatMessage {
  id: string;
  content: string;
  sender: "user" | "assistant";
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

export interface QuerySuggestion {
  id: string;
  text: string;
  category: string;
  confidence: number;
}

export interface UserFeedback {
  messageId: string;
  rating: "positive" | "negative";
  comment?: string;
  timestamp: Date;
}