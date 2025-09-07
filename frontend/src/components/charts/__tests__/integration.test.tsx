/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ChartRendererExample from "../ChartRendererExample";

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

// Mock export libraries
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

describe("ChartRenderer Integration", () => {
  it("renders the example component without crashing", () => {
    render(<ChartRendererExample />);
    
    expect(screen.getByText("ChartRenderer Component Demo")).toBeInTheDocument();
    expect(screen.getByText("Revenue, Expenses & Profit Trends")).toBeInTheDocument();
  });

  it("displays chart configuration controls", () => {
    render(<ChartRendererExample />);
    
    expect(screen.getByText("Dataset")).toBeInTheDocument();
    expect(screen.getByText("Chart Type")).toBeInTheDocument();
    expect(screen.getByText("Card Size")).toBeInTheDocument();
    expect(screen.getByText("Auto-Suggest Type")).toBeInTheDocument();
  });

  it("renders the chart component", () => {
    render(<ChartRendererExample />);
    
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("displays feature checklist", () => {
    render(<ChartRendererExample />);
    
    expect(screen.getByText("Features Demonstrated")).toBeInTheDocument();
    expect(screen.getByText(/Multiple chart types/)).toBeInTheDocument();
    expect(screen.getByText(/CFO-specific financial data formatting/)).toBeInTheDocument();
    expect(screen.getByText(/Export functionality/)).toBeInTheDocument();
  });
});