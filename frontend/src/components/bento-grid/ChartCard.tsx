"use client";

import React from "react";
import ChartRenderer from "../charts/ChartRenderer";
import { BentoGridCard } from "@/types/dashboard";
import { ChartConfig, ExportOptions } from "@/types/chart";
import { useChartExport } from "@/lib/chartExport";

interface ChartCardProps {
  card: BentoGridCard;
  onExport?: (options: ExportOptions) => void;
  onConfigChange?: (config: Partial<ChartConfig>) => void;
}

const ChartCard: React.FC<ChartCardProps> = ({
  card,
  onExport,
  onConfigChange,
}) => {
  const { exportChart } = useChartExport();

  const handleExport = async (options: ExportOptions) => {
    try {
      // Find the chart element within this card
      const cardElement = typeof window !== 'undefined' ? document.querySelector(`[data-card-id="${card.id}"]`) : null;

      const chartElement = cardElement?.querySelector('[data-chart-container]') as HTMLElement;
      
      if (chartElement) {
        await exportChart(chartElement, {
          ...options,
          filename: `${card.content.title?.replace(/\s+/g, '-').toLowerCase()}-${crypto.randomUUID().slice(0, 8)}`,

        });
      }
      
      // Call parent export handler if provided
      onExport?.(options);
    } catch (error) {
      console.error("Chart export failed:", error);
    }
  };

  // Only render if this is a chart card with chart configuration
  if (card.cardType !== "chart" || !card.content.chartConfig) {
    return null;
  }

  return (
    <div 
      data-card-id={card.id}
      data-chart-container
      className="h-full w-full flex flex-col"

    >
      <ChartRenderer
        config={card.content.chartConfig}
        cardSize={card.size}
        onExport={handleExport}
        onConfigChange={onConfigChange}
        className="h-full flex-1 border-none shadow-none"

      />
    </div>
  );
};

export default ChartCard;