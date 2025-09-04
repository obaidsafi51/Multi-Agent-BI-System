export enum ChartType {
    LINE = "line",
    BAR = "bar",
    PIE = "pie",
    AREA = "area",
    SCATTER = "scatter",
    HEATMAP = "heatmap"
}

export interface ChartDataPoint {
    [key: string]: string | number | Date;
}

export interface ChartData {
    data: ChartDataPoint[];
    xAxisKey: string;
    yAxisKeys: string[];
    categories?: string[];
}

export interface ChartDimensions {
    width?: number;
    height?: number;
    margin?: {
        top?: number;
        right?: number;
        bottom?: number;
        left?: number;
    };
}

export interface ChartInteractivity {
    enableZoom?: boolean;
    enablePan?: boolean;
    enableTooltip?: boolean;
    enableLegend?: boolean;
    enableGrid?: boolean;
    enableAnimation?: boolean;
    onDataPointClick?: (data: ChartDataPoint) => void;
    onChartClick?: (event: React.MouseEvent) => void;
}

export interface ChartStyling {
    colorScheme?: string[];
    theme?: "light" | "dark" | "corporate";
    fontSize?: number;
    fontFamily?: string;
    backgroundColor?: string;
    gridColor?: string;
    axisColor?: string;
}

export interface ChartConfig {
    type: ChartType;
    title?: string;
    subtitle?: string;
    data: ChartData;
    dimensions?: ChartDimensions;
    interactivity?: ChartInteractivity;
    styling?: ChartStyling;
    responsive?: boolean;
    showExportButton?: boolean;
}

export interface ExportOptions {
    format: "png" | "svg" | "pdf";
    filename?: string;
    quality?: number;
    width?: number;
    height?: number;
    includeBranding?: boolean;
}

export interface ChartRendererProps {
    config: ChartConfig;
    loading?: boolean;
    error?: string | null;
    className?: string;
    onExport?: (options: ExportOptions) => void;
    onConfigChange?: (config: Partial<ChartConfig>) => void;
}

// CFO-specific chart configurations
export const CFO_COLOR_SCHEMES = {
    corporate: ["#1f2937", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"],
    financial: ["#059669", "#dc2626", "#2563eb", "#7c3aed", "#ea580c", "#0891b2"],
    performance: ["#22c55e", "#eab308", "#f97316", "#ef4444", "#6366f1", "#ec4899"],
    neutral: ["#6b7280", "#9ca3af", "#d1d5db", "#374151", "#111827", "#f9fafb"]
} as const;

export const CHART_TYPE_SUGGESTIONS = {
    timeSeries: ChartType.LINE,
    categorical: ChartType.BAR,
    proportional: ChartType.PIE,
    correlation: ChartType.SCATTER,
    distribution: ChartType.AREA,
    comparison: ChartType.HEATMAP
} as const;