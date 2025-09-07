"use client";

import React, { useState } from "react";
import ChartRenderer from "./ChartRenderer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ChartType, ChartConfig, ExportOptions } from "@/types/chart";
import { CardSize } from "@/types/dashboard";
import { useChartExport } from "@/lib/chartExport";
import { useChartConfig } from "@/lib/chartUtils";

// Sample financial data for demonstration
const SAMPLE_FINANCIAL_DATA = {
  revenue: [
    { month: "Jan 2024", revenue: 2500000, expenses: 1800000, profit: 700000 },
    { month: "Feb 2024", revenue: 2800000, expenses: 1900000, profit: 900000 },
    { month: "Mar 2024", revenue: 3200000, expenses: 2100000, profit: 1100000 },
    { month: "Apr 2024", revenue: 2900000, expenses: 2000000, profit: 900000 },
    { month: "May 2024", revenue: 3500000, expenses: 2200000, profit: 1300000 },
    { month: "Jun 2024", revenue: 3800000, expenses: 2300000, profit: 1500000 },
  ],
  departments: [
    { department: "Sales", budget: 1200000, actual: 1150000, variance: -50000 },
    { department: "Marketing", budget: 800000, actual: 850000, variance: 50000 },
    { department: "Engineering", budget: 2000000, actual: 1950000, variance: -50000 },
    { department: "Operations", budget: 600000, actual: 620000, variance: 20000 },
    { department: "HR", budget: 400000, actual: 380000, variance: -20000 },
  ],
  marketShare: [
    { segment: "Enterprise", share: 45.2 },
    { segment: "SMB", share: 32.8 },
    { segment: "Startup", share: 22.0 },
  ],
  cashFlow: [
    { quarter: "Q1 2024", operating: 4200000, investing: -800000, financing: -500000 },
    { quarter: "Q2 2024", operating: 4800000, investing: -1200000, financing: -300000 },
    { quarter: "Q3 2024", operating: 5100000, investing: -600000, financing: -800000 },
    { quarter: "Q4 2024", operating: 5500000, investing: -1000000, financing: -200000 },
  ],
};

const ChartRendererExample: React.FC = () => {
  const [selectedDataset, setSelectedDataset] = useState<keyof typeof SAMPLE_FINANCIAL_DATA>("revenue");
  const [selectedChartType, setSelectedChartType] = useState<ChartType>(ChartType.LINE);
  const [selectedCardSize, setSelectedCardSize] = useState<CardSize>(CardSize.LARGE);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { exportChart } = useChartExport();

  // Get current dataset configuration
  const getCurrentDataConfig = () => {
    const dataset = SAMPLE_FINANCIAL_DATA[selectedDataset];
    
    switch (selectedDataset) {
      case "revenue":
        return {
          data: dataset,
          xAxisKey: "month",
          yAxisKeys: ["revenue", "expenses", "profit"],
        };
      case "departments":
        return {
          data: dataset,
          xAxisKey: "department",
          yAxisKeys: ["budget", "actual"],
        };
      case "marketShare":
        return {
          data: dataset,
          xAxisKey: "segment",
          yAxisKeys: ["share"],
        };
      case "cashFlow":
        return {
          data: dataset,
          xAxisKey: "quarter",
          yAxisKeys: ["operating", "investing", "financing"],
        };
      default:
        return {
          data: [],
          xAxisKey: "",
          yAxisKeys: [],
        };
    }
  };

  const dataConfig = getCurrentDataConfig();
  const { createConfig, suggestChartType } = useChartConfig(dataConfig, selectedCardSize);

  // Create chart configuration
  const chartConfig: ChartConfig = createConfig({
    type: selectedChartType,
    title: getChartTitle(),
    subtitle: getChartSubtitle(),
    interactivity: {
      enableTooltip: true,
      enableLegend: true,
      enableGrid: true,
      enableAnimation: true,
      enableZoom: selectedCardSize === CardSize.LARGE || selectedCardSize === CardSize.EXTRA_LARGE,
      enablePan: false,
    },
  });

  function getChartTitle(): string {
    switch (selectedDataset) {
      case "revenue":
        return "Revenue, Expenses & Profit Trends";
      case "departments":
        return "Budget vs Actual by Department";
      case "marketShare":
        return "Market Share Distribution";
      case "cashFlow":
        return "Quarterly Cash Flow Analysis";
      default:
        return "Financial Chart";
    }
  }

  function getChartSubtitle(): string {
    switch (selectedDataset) {
      case "revenue":
        return "Monthly financial performance overview";
      case "departments":
        return "Budget variance analysis by department";
      case "marketShare":
        return "Current market segment breakdown";
      case "cashFlow":
        return "Operating, investing, and financing cash flows";
      default:
        return "";
    }
  }

  const handleExport = async (options: ExportOptions) => {
    setIsLoading(true);
    try {
      const chartElement = typeof window !== 'undefined' ? document.querySelector('[data-chart-container]') as HTMLElement : null;

      if (chartElement) {
        await exportChart(chartElement, options);
      }
    } catch (err) {
      setError("Export failed. Please try again.");
      console.error("Export error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestChartType = () => {
    const suggested = suggestChartType();
    setSelectedChartType(suggested);
  };

  const simulateLoading = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 2000);
  };

  const simulateError = () => {
    setError("Simulated error: Unable to load chart data");
    setTimeout(() => setError(null), 3000);
  };

  return (
    <div className="space-y-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>ChartRenderer Component Demo</CardTitle>
          <p className="text-sm text-gray-600">
            Interactive demonstration of the ChartRenderer component with CFO-specific financial data
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {/* Dataset Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Dataset</label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="w-full justify-between">
                    {selectedDataset}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setSelectedDataset("revenue")}>
                    Revenue Data
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedDataset("departments")}>
                    Department Budgets
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedDataset("marketShare")}>
                    Market Share
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedDataset("cashFlow")}>
                    Cash Flow
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Chart Type Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Chart Type</label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="w-full justify-between">
                    {selectedChartType}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setSelectedChartType(ChartType.LINE)}>
                    Line Chart
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedChartType(ChartType.BAR)}>
                    Bar Chart
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedChartType(ChartType.PIE)}>
                    Pie Chart
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedChartType(ChartType.AREA)}>
                    Area Chart
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedChartType(ChartType.SCATTER)}>
                    Scatter Plot
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Card Size Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Card Size</label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="w-full justify-between">
                    {selectedCardSize}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setSelectedCardSize(CardSize.SMALL)}>
                    Small (1x1)
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedCardSize(CardSize.MEDIUM_H)}>
                    Medium H (2x1)
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedCardSize(CardSize.MEDIUM_V)}>
                    Medium V (1x2)
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedCardSize(CardSize.LARGE)}>
                    Large (2x2)
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSelectedCardSize(CardSize.EXTRA_LARGE)}>
                    Extra Large (3x2)
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Actions */}
            <div>
              <label className="block text-sm font-medium mb-2">Actions</label>
              <div className="space-y-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSuggestChartType}
                  className="w-full"
                >
                  Auto-Suggest Type
                </Button>
              </div>
            </div>
          </div>

          {/* Demo Controls */}
          <div className="flex gap-2 mb-6">
            <Button variant="outline" onClick={simulateLoading}>
              Simulate Loading
            </Button>
            <Button variant="outline" onClick={simulateError}>
              Simulate Error
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Chart Display */}
      <div data-chart-container>
        <ChartRenderer
          config={chartConfig}
          loading={isLoading}
          error={error}
          cardSize={selectedCardSize}
          onExport={handleExport}
          className="w-full"
        />
      </div>

      {/* Chart Information */}
      <Card>
        <CardHeader>
          <CardTitle>Chart Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-medium mb-2">Current Configuration</h4>
              <ul className="space-y-1 text-gray-600">
                <li>Dataset: {selectedDataset}</li>
                <li>Chart Type: {selectedChartType}</li>
                <li>Card Size: {selectedCardSize}</li>
                <li>Dimensions: {chartConfig.dimensions?.width}x{chartConfig.dimensions?.height}</li>
                <li>Responsive: {chartConfig.responsive ? "Yes" : "No"}</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Features Demonstrated</h4>
              <ul className="space-y-1 text-gray-600">
                <li>✅ Multiple chart types (Line, Bar, Pie, Area, Scatter)</li>
                <li>✅ CFO-specific financial data formatting</li>
                <li>✅ Responsive sizing for Bento grid cards</li>
                <li>✅ Interactive features (zoom, tooltips, legends)</li>
                <li>✅ Export functionality (PNG, SVG, PDF)</li>
                <li>✅ Loading and error states</li>
                <li>✅ Intelligent chart type suggestions</li>
                <li>✅ Corporate color schemes and styling</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ChartRendererExample;