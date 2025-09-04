import { ChartType, ChartConfig, ChartData, ChartDataPoint, CFO_COLOR_SCHEMES } from "@/types/chart";
import { CardSize } from "@/types/dashboard";

/**
 * Intelligent chart type selection based on data characteristics
 */
export class ChartTypeSelector {
    /**
     * Analyze data and suggest the most appropriate chart type
     */
    static suggestChartType(data: ChartDataPoint[], xAxisKey: string, yAxisKeys: string[]): ChartType {
        if (!data || data.length === 0) return ChartType.BAR;

        const firstItem = data[0];
        const dataKeys = Object.keys(firstItem);

        // Check for time series data
        if (this.isTimeSeriesData(data, xAxisKey)) {
            return ChartType.LINE;
        }

        // Check for proportional data (good for pie charts)
        if (this.isProportionalData(data, yAxisKeys) && data.length <= 8) {
            return ChartType.PIE;
        }

        // Check for correlation analysis (scatter plot)
        if (this.isCorrelationData(data, yAxisKeys)) {
            return ChartType.SCATTER;
        }

        // Check for distribution data (area chart)
        if (this.isDistributionData(data, yAxisKeys)) {
            return ChartType.AREA;
        }

        // Default to bar chart for categorical data
        return ChartType.BAR;
    }

    /**
     * Check if data represents time series
     */
    private static isTimeSeriesData(data: ChartDataPoint[], xAxisKey: string): boolean {
        const timeKeywords = ["date", "time", "period", "month", "year", "quarter", "week"];
        const keyLower = xAxisKey.toLowerCase();

        // Check if key name suggests time data
        if (timeKeywords.some(keyword => keyLower.includes(keyword))) {
            return true;
        }

        // Check if values are dates or can be parsed as dates
        const sampleValues = data.slice(0, 3).map(item => item[xAxisKey]);
        return sampleValues.every(value => {
            if (value instanceof Date) return true;
            if (typeof value === "string") {
                const parsed = new Date(value);
                return !isNaN(parsed.getTime());
            }
            return false;
        });
    }

    /**
     * Check if data represents proportional values (percentages, ratios)
     */
    private static isProportionalData(data: ChartDataPoint[], yAxisKeys: string[]): boolean {
        const proportionalKeywords = ["percentage", "percent", "ratio", "share", "proportion"];

        // Check key names
        const hasProportionalKeys = yAxisKeys.some(key =>
            proportionalKeywords.some(keyword => key.toLowerCase().includes(keyword))
        );

        if (hasProportionalKeys) return true;

        // Check if values sum to approximately 100 (percentages) or 1 (ratios)
        const firstYKey = yAxisKeys[0];
        const sum = data.reduce((acc, item) => {
            const value = item[firstYKey];
            return acc + (typeof value === "number" ? value : 0);
        }, 0);

        return Math.abs(sum - 100) < 5 || Math.abs(sum - 1) < 0.1;
    }

    /**
     * Check if data is suitable for correlation analysis
     */
    private static isCorrelationData(data: ChartDataPoint[], yAxisKeys: string[]): boolean {
        // Need at least 2 numeric variables for correlation
        if (yAxisKeys.length < 2) return false;

        // Check if we have continuous numeric data
        const numericKeys = yAxisKeys.filter(key => {
            return data.every(item => typeof item[key] === "number");
        });

        return numericKeys.length >= 2 && data.length >= 10;
    }

    /**
     * Check if data represents distribution (cumulative, stacked areas)
     */
    private static isDistributionData(data: ChartDataPoint[], yAxisKeys: string[]): boolean {
        const distributionKeywords = ["cumulative", "total", "sum", "distribution"];

        return yAxisKeys.some(key =>
            distributionKeywords.some(keyword => key.toLowerCase().includes(keyword))
        ) && yAxisKeys.length > 1;
    }
}

/**
 * Chart configuration builder with CFO-specific defaults
 */
export class ChartConfigBuilder {
    private config: Partial<ChartConfig> = {};

    constructor(data: ChartData) {
        this.config = {
            data,
            type: ChartTypeSelector.suggestChartType(data.data, data.xAxisKey, data.yAxisKeys),
            responsive: true,
            showExportButton: true,
            interactivity: {
                enableTooltip: true,
                enableLegend: true,
                enableGrid: true,
                enableAnimation: true,
                enableZoom: false,
                enablePan: false,
            },
            styling: {
                theme: "corporate",
                colorScheme: CFO_COLOR_SCHEMES.corporate,
                fontSize: 12,
                fontFamily: "Arial, sans-serif",
            },
        };
    }

    /**
     * Set chart type explicitly
     */
    setType(type: ChartType): ChartConfigBuilder {
        this.config.type = type;
        return this;
    }

    /**
     * Set chart title and subtitle
     */
    setTitle(title: string, subtitle?: string): ChartConfigBuilder {
        this.config.title = title;
        this.config.subtitle = subtitle;
        return this;
    }

    /**
     * Configure dimensions based on card size
     */
    setDimensions(cardSize: CardSize): ChartConfigBuilder {
        const dimensionMap = {
            [CardSize.SMALL]: { width: 300, height: 200 },
            [CardSize.MEDIUM_H]: { width: 600, height: 300 },
            [CardSize.MEDIUM_V]: { width: 300, height: 400 },
            [CardSize.LARGE]: { width: 600, height: 400 },
            [CardSize.EXTRA_LARGE]: { width: 900, height: 500 },
        };

        this.config.dimensions = {
            ...dimensionMap[cardSize],
            margin: { top: 20, right: 30, left: 20, bottom: 5 },
        };

        return this;
    }

    /**
     * Set color theme
     */
    setTheme(theme: keyof typeof CFO_COLOR_SCHEMES): ChartConfigBuilder {
        if (this.config.styling) {
            this.config.styling.theme = theme;
            this.config.styling.colorScheme = CFO_COLOR_SCHEMES[theme];
        }
        return this;
    }

    /**
     * Enable/disable interactivity features
     */
    setInteractivity(options: Partial<ChartConfig["interactivity"]>): ChartConfigBuilder {
        this.config.interactivity = {
            ...this.config.interactivity,
            ...options,
        };
        return this;
    }

    /**
     * Build the final configuration
     */
    build(): ChartConfig {
        if (!this.config.type || !this.config.data) {
            throw new Error("Chart type and data are required");
        }

        return this.config as ChartConfig;
    }
}

/**
 * Utility functions for chart data processing
 */
export class ChartDataProcessor {
    /**
     * Format financial values for display
     */
    static formatFinancialValue(value: number, currency = "USD"): string {
        const absValue = Math.abs(value);

        if (absValue >= 1000000000) {
            return `${currency === "USD" ? "$" : ""}${(value / 1000000000).toFixed(1)}B`;
        } else if (absValue >= 1000000) {
            return `${currency === "USD" ? "$" : ""}${(value / 1000000).toFixed(1)}M`;
        } else if (absValue >= 1000) {
            return `${currency === "USD" ? "$" : ""}${(value / 1000).toFixed(1)}K`;
        }

        return `${currency === "USD" ? "$" : ""}${value.toLocaleString()}`;
    }

    /**
     * Format percentage values
     */
    static formatPercentage(value: number, decimals = 1): string {
        return `${value.toFixed(decimals)}%`;
    }

    /**
     * Process time series data for better chart display
     */
    static processTimeSeriesData(data: ChartDataPoint[], xAxisKey: string): ChartDataPoint[] {
        return data.map(item => ({
            ...item,
            [xAxisKey]: this.formatDateForChart(item[xAxisKey]),
        }));
    }

    /**
     * Format dates for chart display
     */
    private static formatDateForChart(value: any): string {
        if (value instanceof Date) {
            return value.toLocaleDateString();
        }

        if (typeof value === "string") {
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
                return date.toLocaleDateString();
            }
        }

        return String(value);
    }

    /**
     * Calculate trend indicators for financial data
     */
    static calculateTrend(data: ChartDataPoint[], yAxisKey: string): "up" | "down" | "stable" {
        if (data.length < 2) return "stable";

        const values = data
            .map(item => item[yAxisKey])
            .filter(value => typeof value === "number") as number[];

        if (values.length < 2) return "stable";

        const firstValue = values[0];
        const lastValue = values[values.length - 1];
        const changePercent = ((lastValue - firstValue) / firstValue) * 100;

        if (changePercent > 5) return "up";
        if (changePercent < -5) return "down";
        return "stable";
    }

    /**
     * Aggregate data by time period
     */
    static aggregateByPeriod(
        data: ChartDataPoint[],
        xAxisKey: string,
        yAxisKey: string,
        period: "daily" | "weekly" | "monthly" | "quarterly"
    ): ChartDataPoint[] {
        const grouped = new Map<string, number[]>();

        data.forEach(item => {
            const date = new Date(item[xAxisKey] as string);
            const key = this.getPeriodKey(date, period);
            const value = item[yAxisKey] as number;

            if (!grouped.has(key)) {
                grouped.set(key, []);
            }
            grouped.get(key)!.push(value);
        });

        return Array.from(grouped.entries()).map(([key, values]) => ({
            [xAxisKey]: key,
            [yAxisKey]: values.reduce((sum, val) => sum + val, 0),
        }));
    }

    /**
     * Get period key for aggregation
     */
    private static getPeriodKey(date: Date, period: string): string {
        switch (period) {
            case "daily":
                return date.toISOString().split("T")[0];
            case "weekly":
                const weekStart = new Date(date);
                weekStart.setDate(date.getDate() - date.getDay());
                return weekStart.toISOString().split("T")[0];
            case "monthly":
                return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
            case "quarterly":
                const quarter = Math.floor(date.getMonth() / 3) + 1;
                return `${date.getFullYear()}-Q${quarter}`;
            default:
                return date.toISOString().split("T")[0];
        }
    }
}

/**
 * Hook for chart configuration management
 */
export const useChartConfig = (initialData: ChartData, cardSize: CardSize = CardSize.LARGE) => {
    const createConfig = (overrides?: Partial<ChartConfig>): ChartConfig => {
        const builder = new ChartConfigBuilder(initialData)
            .setDimensions(cardSize)
            .setTheme("corporate");

        const baseConfig = builder.build();

        return {
            ...baseConfig,
            ...overrides,
        };
    };

    const suggestChartType = (): ChartType => {
        return ChartTypeSelector.suggestChartType(
            initialData.data,
            initialData.xAxisKey,
            initialData.yAxisKeys
        );
    };

    return {
        createConfig,
        suggestChartType,
        ChartConfigBuilder,
    };
};