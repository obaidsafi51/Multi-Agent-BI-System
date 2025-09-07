import { describe, it, expect } from "vitest";
import {
    ChartTypeSelector,
    ChartConfigBuilder,
    ChartDataProcessor,
    useChartConfig,
} from "../chartUtils";
import { ChartType, ChartData } from "@/types/chart";
import { CardSize } from "@/types/dashboard";

describe("ChartTypeSelector", () => {
    describe("suggestChartType", () => {
        it("suggests LINE chart for time series data", () => {
            const data = [
                { date: "2024-01-01", revenue: 100000 },
                { date: "2024-02-01", revenue: 120000 },
                { date: "2024-03-01", revenue: 110000 },
            ];

            const result = ChartTypeSelector.suggestChartType(data, "date", ["revenue"]);
            expect(result).toBe(ChartType.LINE);
        });

        it("suggests PIE chart for proportional data with few items", () => {
            const data = [
                { category: "Product A", percentage: 45 },
                { category: "Product B", percentage: 30 },
                { category: "Product C", percentage: 25 },
            ];

            const result = ChartTypeSelector.suggestChartType(data, "category", ["percentage"]);
            expect(result).toBe(ChartType.PIE);
        });

        it("suggests SCATTER chart for correlation data", () => {
            const data = Array.from({ length: 15 }, (_, i) => ({
                x: i * 10,
                revenue: i * 1000 + Math.random() * 500,
                expenses: i * 800 + Math.random() * 300,
            }));

            const result = ChartTypeSelector.suggestChartType(data, "x", ["revenue", "expenses"]);
            expect(result).toBe(ChartType.SCATTER);
        });

        it("suggests AREA chart for distribution data", () => {
            const data = [
                { month: "Jan", cumulative_revenue: 100000, total_expenses: 80000 },
                { month: "Feb", cumulative_revenue: 220000, total_expenses: 165000 },
                { month: "Mar", cumulative_revenue: 330000, total_expenses: 255000 },
            ];

            const result = ChartTypeSelector.suggestChartType(data, "month", ["cumulative_revenue", "total_expenses"]);
            expect(result).toBe(ChartType.AREA);
        });

        it("defaults to BAR chart for categorical data", () => {
            const data = [
                { department: "Sales", budget: 100000 },
                { department: "Marketing", budget: 80000 },
                { department: "Engineering", budget: 120000 },
            ];

            const result = ChartTypeSelector.suggestChartType(data, "department", ["budget"]);
            expect(result).toBe(ChartType.BAR);
        });

        it("returns BAR chart for empty data", () => {
            const result = ChartTypeSelector.suggestChartType([], "x", ["y"]);
            expect(result).toBe(ChartType.BAR);
        });
    });
});

describe("ChartConfigBuilder", () => {
    const sampleData: ChartData = {
        data: [
            { month: "Jan", revenue: 100000 },
            { month: "Feb", revenue: 120000 },
        ],
        xAxisKey: "month",
        yAxisKeys: ["revenue"],
    };

    it("creates basic configuration with defaults", () => {
        const builder = new ChartConfigBuilder(sampleData);
        const config = builder.build();

        expect(config.data).toBe(sampleData);
        expect(config.type).toBe(ChartType.BAR); // Default for this data
        expect(config.responsive).toBe(true);
        expect(config.showExportButton).toBe(true);
        expect(config.interactivity?.enableTooltip).toBe(true);
        expect(config.styling?.theme).toBe("corporate");
    });

    it("allows setting chart type explicitly", () => {
        const builder = new ChartConfigBuilder(sampleData);
        const config = builder.setType(ChartType.LINE).build();

        expect(config.type).toBe(ChartType.LINE);
    });

    it("allows setting title and subtitle", () => {
        const builder = new ChartConfigBuilder(sampleData);
        const config = builder
            .setTitle("Revenue Chart", "Monthly revenue data")
            .build();

        expect(config.title).toBe("Revenue Chart");
        expect(config.subtitle).toBe("Monthly revenue data");
    });

    it("sets dimensions based on card size", () => {
        const builder = new ChartConfigBuilder(sampleData);
        const config = builder.setDimensions(CardSize.LARGE).build();

        expect(config.dimensions?.width).toBe(600);
        expect(config.dimensions?.height).toBe(400);
        expect(config.dimensions?.margin).toEqual({
            top: 20,
            right: 30,
            left: 20,
            bottom: 5,
        });
    });

    it("allows setting color theme", () => {
        const builder = new ChartConfigBuilder(sampleData);
        const config = builder.setTheme("financial").build();

        expect(config.styling?.theme).toBe("financial");
        expect(config.styling?.colorScheme).toEqual([
            "#059669", "#dc2626", "#2563eb", "#7c3aed", "#ea580c", "#0891b2"
        ]);
    });

    it("allows configuring interactivity", () => {
        const builder = new ChartConfigBuilder(sampleData);
        const config = builder
            .setInteractivity({
                enableZoom: true,
                enablePan: true,
                enableAnimation: false,
            })
            .build();

        expect(config.interactivity?.enableZoom).toBe(true);
        expect(config.interactivity?.enablePan).toBe(true);
        expect(config.interactivity?.enableAnimation).toBe(false);
        expect(config.interactivity?.enableTooltip).toBe(true); // Should preserve defaults
    });

    it("throws error when building without required data", () => {
        const builder = new ChartConfigBuilder(sampleData);
        // @ts-expect-error - Testing error case
        builder.config.type = undefined;

        expect(() => builder.build()).toThrow("Chart type and data are required");
    });
});

describe("ChartDataProcessor", () => {
    describe("formatFinancialValue", () => {
        it("formats billions correctly", () => {
            expect(ChartDataProcessor.formatFinancialValue(1500000000)).toBe("$1.5B");
            expect(ChartDataProcessor.formatFinancialValue(-2300000000)).toBe("$-2.3B");
        });

        it("formats millions correctly", () => {
            expect(ChartDataProcessor.formatFinancialValue(1500000)).toBe("$1.5M");
            expect(ChartDataProcessor.formatFinancialValue(999999)).toBe("$1.0M");
        });

        it("formats thousands correctly", () => {
            expect(ChartDataProcessor.formatFinancialValue(1500)).toBe("$1.5K");
            expect(ChartDataProcessor.formatFinancialValue(999)).toBe("$999");
        });

        it("formats small numbers correctly", () => {
            expect(ChartDataProcessor.formatFinancialValue(500)).toBe("$500");
            expect(ChartDataProcessor.formatFinancialValue(0)).toBe("$0");
        });

        it("supports different currencies", () => {
            expect(ChartDataProcessor.formatFinancialValue(1500000, "EUR")).toBe("1.5M");
        });
    });

    describe("formatPercentage", () => {
        it("formats percentages with default decimals", () => {
            expect(ChartDataProcessor.formatPercentage(45.678)).toBe("45.7%");
        });

        it("formats percentages with custom decimals", () => {
            expect(ChartDataProcessor.formatPercentage(45.678, 2)).toBe("45.68%");
            expect(ChartDataProcessor.formatPercentage(45.678, 0)).toBe("46%");
        });
    });

    describe("processTimeSeriesData", () => {
        it("formats date strings for chart display", () => {
            const data = [
                { date: "2024-01-01", value: 100 },
                { date: "2024-02-01", value: 200 },
            ];

            const processed = ChartDataProcessor.processTimeSeriesData(data, "date");

            expect(processed[0].date).toBe("1/1/2024");
            expect(processed[1].date).toBe("2/1/2024");
        });

        it("handles Date objects", () => {
            const data = [
                { date: new Date("2024-01-01"), value: 100 },
                { date: new Date("2024-02-01"), value: 200 },
            ];

            const processed = ChartDataProcessor.processTimeSeriesData(data, "date");

            expect(processed[0].date).toBe("1/1/2024");
            expect(processed[1].date).toBe("2/1/2024");
        });

        it("preserves non-date values", () => {
            const data = [
                { category: "A", value: 100 },
                { category: "B", value: 200 },
            ];

            const processed = ChartDataProcessor.processTimeSeriesData(data, "category");

            expect(processed[0].category).toBe("A");
            expect(processed[1].category).toBe("B");
        });
    });

    describe("calculateTrend", () => {
        it("calculates upward trend", () => {
            const data = [
                { month: "Jan", value: 100 },
                { month: "Feb", value: 120 },
                { month: "Mar", value: 130 },
            ];

            const trend = ChartDataProcessor.calculateTrend(data, "value");
            expect(trend).toBe("up");
        });

        it("calculates downward trend", () => {
            const data = [
                { month: "Jan", value: 130 },
                { month: "Feb", value: 120 },
                { month: "Mar", value: 100 },
            ];

            const trend = ChartDataProcessor.calculateTrend(data, "value");
            expect(trend).toBe("down");
        });

        it("calculates stable trend", () => {
            const data = [
                { month: "Jan", value: 100 },
                { month: "Feb", value: 102 },
                { month: "Mar", value: 101 },
            ];

            const trend = ChartDataProcessor.calculateTrend(data, "value");
            expect(trend).toBe("stable");
        });

        it("handles insufficient data", () => {
            const data = [{ month: "Jan", value: 100 }];
            const trend = ChartDataProcessor.calculateTrend(data, "value");
            expect(trend).toBe("stable");
        });

        it("handles non-numeric data", () => {
            const data = [
                { month: "Jan", value: "high" },
                { month: "Feb", value: "low" },
            ];

            const trend = ChartDataProcessor.calculateTrend(data, "value");
            expect(trend).toBe("stable");
        });
    });

    describe("aggregateByPeriod", () => {
        const sampleData = [
            { date: "2024-01-01", value: 100 },
            { date: "2024-01-02", value: 150 },
            { date: "2024-01-15", value: 200 },
            { date: "2024-02-01", value: 120 },
            { date: "2024-02-15", value: 180 },
        ];

        it("aggregates by monthly period", () => {
            const aggregated = ChartDataProcessor.aggregateByPeriod(
                sampleData,
                "date",
                "value",
                "monthly"
            );

            expect(aggregated).toHaveLength(2);
            expect(aggregated[0]).toEqual({ date: "2024-01", value: 450 });
            expect(aggregated[1]).toEqual({ date: "2024-02", value: 300 });
        });

        it("aggregates by daily period", () => {
            const aggregated = ChartDataProcessor.aggregateByPeriod(
                sampleData,
                "date",
                "value",
                "daily"
            );

            expect(aggregated).toHaveLength(5); // Each day is separate
        });

        it("aggregates by quarterly period", () => {
            const quarterlyData = [
                { date: "2024-01-01", value: 100 },
                { date: "2024-03-01", value: 200 },
                { date: "2024-04-01", value: 150 },
                { date: "2024-06-01", value: 250 },
            ];

            const aggregated = ChartDataProcessor.aggregateByPeriod(
                quarterlyData,
                "date",
                "value",
                "quarterly"
            );

            expect(aggregated).toHaveLength(2);
            expect(aggregated[0]).toEqual({ date: "2024-Q1", value: 300 });
            expect(aggregated[1]).toEqual({ date: "2024-Q2", value: 400 });
        });
    });
});

describe("useChartConfig", () => {
    const sampleData: ChartData = {
        data: [
            { month: "Jan", revenue: 100000 },
            { month: "Feb", revenue: 120000 },
        ],
        xAxisKey: "month",
        yAxisKeys: ["revenue"],
    };

    it("creates configuration with defaults", () => {
        const { createConfig } = useChartConfig(sampleData);
        const config = createConfig();

        expect(config.data).toBe(sampleData);
        expect(config.responsive).toBe(true);
        expect(config.styling?.theme).toBe("corporate");
    });

    it("applies overrides to configuration", () => {
        const { createConfig } = useChartConfig(sampleData);
        const config = createConfig({
            type: ChartType.LINE,
            title: "Custom Title",
        });

        expect(config.type).toBe(ChartType.LINE);
        expect(config.title).toBe("Custom Title");
    });

    it("suggests appropriate chart type", () => {
        const { suggestChartType } = useChartConfig(sampleData);
        const suggestion = suggestChartType();

        expect(suggestion).toBe(ChartType.BAR); // For categorical data
    });

    it("adapts to different card sizes", () => {
        const { createConfig } = useChartConfig(sampleData, CardSize.SMALL);
        const config = createConfig();

        expect(config.dimensions?.width).toBe(300);
        expect(config.dimensions?.height).toBe(200);
    });
});