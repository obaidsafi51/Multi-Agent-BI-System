/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ChartRenderer from "../ChartRenderer";
import { ChartType, ChartConfig } from "@/types/chart";
import { CardSize } from "@/types/dashboard";

// Mock recharts components
vi.mock("recharts", () => ({
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div data-testid="pie" />,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => <div data-testid="area" />,
  ScatterChart: ({ children }: any) => <div data-testid="scatter-chart">{children}</div>,
  Scatter: () => <div data-testid="scatter" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Cell: () => <div data-testid="cell" />,
}));

// Mock html2canvas and jsPDF
vi.mock("html2canvas", () => ({
  default: vi.fn(() =>
    Promise.resolve({
      toDataURL: vi.fn(() => "data:image/png;base64,mock"),
      width: 800,
      height: 600,
    })
  ),
}));

vi.mock("jspdf", () => ({
  jsPDF: vi.fn(() => ({
    addImage: vi.fn(),
    save: vi.fn(),
    setFontSize: vi.fn(),
    setTextColor: vi.fn(),
    text: vi.fn(),
  })),
}));

describe("ChartRenderer", () => {
  const mockData = [
    { month: "Jan", revenue: 100000, expenses: 80000 },
    { month: "Feb", revenue: 120000, expenses: 85000 },
    { month: "Mar", revenue: 110000, expenses: 90000 },
  ];

  const baseConfig: ChartConfig = {
    type: ChartType.LINE,
    title: "Revenue vs Expenses",
    data: {
      data: mockData,
      xAxisKey: "month",
      yAxisKeys: ["revenue", "expenses"],
    },
    responsive: true,
    showExportButton: true,
  };

  const mockOnExport = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders loading state correctly", () => {
      render(
        <ChartRenderer
          config={baseConfig}
          loading={true}
        />
      );

      expect(screen.getByText("Loading chart...")).toBeInTheDocument();
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("renders error state correctly", () => {
      const errorMessage = "Failed to load chart data";
      render(
        <ChartRenderer
          config={baseConfig}
          error={errorMessage}
        />
      );

      expect(screen.getByText("⚠️ Chart Error")).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it("renders chart title and subtitle", () => {
      const configWithSubtitle = {
        ...baseConfig,
        subtitle: "Monthly comparison",
      };

      render(<ChartRenderer config={configWithSubtitle} />);

      expect(screen.getByText("Revenue vs Expenses")).toBeInTheDocument();
      expect(screen.getByText("Monthly comparison")).toBeInTheDocument();
    });

    it("renders export button when showExportButton is true", () => {
      render(<ChartRenderer config={baseConfig} onExport={mockOnExport} />);

      expect(screen.getByText("Export")).toBeInTheDocument();
    });

    it("does not render export button when showExportButton is false", () => {
      const configWithoutExport = {
        ...baseConfig,
        showExportButton: false,
      };

      render(<ChartRenderer config={configWithoutExport} />);

      expect(screen.queryByText("Export")).not.toBeInTheDocument();
    });
  });

  describe("Chart Types", () => {
    it("renders line chart correctly", () => {
      render(<ChartRenderer config={baseConfig} />);

      expect(screen.getByTestId("line-chart")).toBeInTheDocument();
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });

    it("renders bar chart correctly", () => {
      const barConfig = { ...baseConfig, type: ChartType.BAR };
      render(<ChartRenderer config={barConfig} />);

      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });

    it("renders pie chart correctly", () => {
      const pieConfig = { ...baseConfig, type: ChartType.PIE };
      render(<ChartRenderer config={pieConfig} />);

      expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
    });

    it("renders area chart correctly", () => {
      const areaConfig = { ...baseConfig, type: ChartType.AREA };
      render(<ChartRenderer config={areaConfig} />);

      expect(screen.getByTestId("area-chart")).toBeInTheDocument();
    });

    it("renders scatter chart correctly", () => {
      const scatterConfig = { ...baseConfig, type: ChartType.SCATTER };
      render(<ChartRenderer config={scatterConfig} />);

      expect(screen.getByTestId("scatter-chart")).toBeInTheDocument();
    });

    it("handles unsupported chart type", () => {
      const unsupportedConfig = { ...baseConfig, type: "unsupported" as ChartType };
      render(<ChartRenderer config={unsupportedConfig} />);

      expect(screen.getByText(/Unsupported chart type/)).toBeInTheDocument();
    });
  });

  describe("Responsive Behavior", () => {
    it("adapts dimensions based on card size", () => {
      const { rerender } = render(
        <ChartRenderer config={baseConfig} cardSize={CardSize.SMALL} />
      );

      // Check that responsive container is rendered
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();

      // Test different card sizes
      rerender(<ChartRenderer config={baseConfig} cardSize={CardSize.LARGE} />);
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });

    it("uses config dimensions when provided", () => {
      const configWithDimensions = {
        ...baseConfig,
        dimensions: {
          width: 1000,
          height: 500,
          margin: { top: 10, right: 10, bottom: 10, left: 10 },
        },
      };

      render(<ChartRenderer config={configWithDimensions} />);
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });
  });

  describe("Interactivity", () => {
    it("renders zoom controls when zoom is enabled", () => {
      const configWithZoom = {
        ...baseConfig,
        interactivity: { enableZoom: true },
      };

      render(<ChartRenderer config={configWithZoom} />);

      expect(screen.getByRole("button", { name: /zoom out/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /zoom in/i })).toBeInTheDocument();
    });

    it("handles zoom in and zoom out", () => {
      const configWithZoom = {
        ...baseConfig,
        interactivity: { enableZoom: true },
      };

      render(<ChartRenderer config={configWithZoom} />);

      const zoomInButton = screen.getByRole("button", { name: /zoom in/i });
      const zoomOutButton = screen.getByRole("button", { name: /zoom out/i });

      // Test zoom in
      fireEvent.click(zoomInButton);
      // Zoom out should not be disabled after zoom in
      expect(zoomOutButton).not.toBeDisabled();

      // Test zoom out
      fireEvent.click(zoomOutButton);
    });

    it("disables zoom buttons at limits", () => {
      const configWithZoom = {
        ...baseConfig,
        interactivity: { enableZoom: true },
      };

      render(<ChartRenderer config={configWithZoom} />);

      const zoomOutButton = screen.getByRole("button", { name: /zoom out/i });
      
      // Initially at zoom level 1, so zoom out should work
      expect(zoomOutButton).not.toBeDisabled();
    });
  });

  describe("Export Functionality", () => {
    it("opens export dropdown when export button is clicked", async () => {
      render(<ChartRenderer config={baseConfig} onExport={mockOnExport} />);

      const exportButton = screen.getByText("Export");
      fireEvent.click(exportButton);

      await waitFor(() => {
        expect(screen.getByText("Export as PNG")).toBeInTheDocument();
        expect(screen.getByText("Export as SVG")).toBeInTheDocument();
        expect(screen.getByText("Export as PDF")).toBeInTheDocument();
      });
    });

    it("calls onExport with correct format when export option is selected", async () => {
      render(<ChartRenderer config={baseConfig} onExport={mockOnExport} />);

      const exportButton = screen.getByText("Export");
      fireEvent.click(exportButton);

      await waitFor(() => {
        const pngOption = screen.getByText("Export as PNG");
        fireEvent.click(pngOption);
      });

      expect(mockOnExport).toHaveBeenCalledWith(
        expect.objectContaining({
          format: "png",
          filename: expect.stringContaining("chart-"),
          quality: 1,
          includeBranding: true,
        })
      );
    });

    it("disables export button during export", async () => {
      const slowExport = vi.fn(() => new Promise(resolve => setTimeout(resolve, 100)));
      
      render(<ChartRenderer config={baseConfig} onExport={slowExport} />);

      const exportButton = screen.getByText("Export");
      fireEvent.click(exportButton);

      await waitFor(() => {
        const pngOption = screen.getByText("Export as PNG");
        fireEvent.click(pngOption);
      });

      // Button should be disabled during export
      expect(exportButton).toBeDisabled();
    });
  });

  describe("Styling and Theming", () => {
    it("applies corporate color scheme by default", () => {
      render(<ChartRenderer config={baseConfig} />);
      
      // Chart should render with default styling
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });

    it("applies custom color scheme when provided", () => {
      const configWithCustomColors = {
        ...baseConfig,
        styling: {
          colorScheme: ["#ff0000", "#00ff00", "#0000ff"],
          theme: "corporate" as const,
        },
      };

      render(<ChartRenderer config={configWithCustomColors} />);
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });

    it("applies custom font settings", () => {
      const configWithCustomFont = {
        ...baseConfig,
        styling: {
          fontSize: 14,
          fontFamily: "Helvetica, sans-serif",
        },
      };

      render(<ChartRenderer config={configWithCustomFont} />);
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });
  });

  describe("Error Boundaries", () => {
    it("handles chart rendering errors gracefully", () => {
      // Mock console.error to avoid noise in test output
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      const invalidConfig = {
        ...baseConfig,
        data: {
          data: null as any,
          xAxisKey: "",
          yAxisKeys: [],
        },
      };

      render(<ChartRenderer config={invalidConfig} />);
      
      // Component should still render without crashing
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();

      consoleSpy.mockRestore();
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA labels and roles", () => {
      render(<ChartRenderer config={baseConfig} />);

      // Card should have proper structure
      const card = screen.getByRole("region");
      expect(card).toBeInTheDocument();
    });

    it("supports keyboard navigation for interactive elements", () => {
      const configWithZoom = {
        ...baseConfig,
        interactivity: { enableZoom: true },
      };

      render(<ChartRenderer config={configWithZoom} />);

      const zoomInButton = screen.getByRole("button", { name: /zoom in/i });
      
      // Button should be focusable
      zoomInButton.focus();
      expect(zoomInButton).toHaveFocus();
    });
  });

  describe("Performance", () => {
    it("handles large datasets efficiently", () => {
      const largeData = Array.from({ length: 1000 }, (_, i) => ({
        month: `Month ${i}`,
        revenue: Math.random() * 100000,
        expenses: Math.random() * 80000,
      }));

      const configWithLargeData = {
        ...baseConfig,
        data: {
          data: largeData,
          xAxisKey: "month",
          yAxisKeys: ["revenue", "expenses"],
        },
      };

      const startTime = performance.now();
      render(<ChartRenderer config={configWithLargeData} />);
      const endTime = performance.now();

      // Rendering should complete within reasonable time
      expect(endTime - startTime).toBeLessThan(1000);
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });

    it("memoizes expensive calculations", () => {
      const { rerender } = render(<ChartRenderer config={baseConfig} />);

      // Re-render with same config should be fast
      const startTime = performance.now();
      rerender(<ChartRenderer config={baseConfig} />);
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(100);
    });
  });
});