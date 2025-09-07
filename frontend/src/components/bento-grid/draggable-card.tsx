"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { BentoGridCard, CardType } from "@/types/dashboard";
import { GripVertical, TrendingUp, BarChart3, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import ChartCard from "./ChartCard";

interface DraggableCardProps {
  card: BentoGridCard;
}

export function DraggableCard({ card }: DraggableCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const renderCardContent = () => {
    switch (card.cardType) {
      case CardType.KPI:
        return (
          <div className="flex items-center justify-between h-full">
            <div className="flex-1">
              <p className="text-2xl font-bold mb-1" style={{ color: 'var(--corporate-gray-900)' }}>
                {card.content.value}
              </p>
              <p className="text-sm" style={{ color: 'var(--corporate-gray-600)' }}>
                {card.content.label}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <Badge variant={card.content.trend === "up" ? "default" : "destructive"} className="text-xs">
                {card.content.change}
              </Badge>
              {card.content.trend === "up" ? (
                <TrendingUp className="h-4 w-4 text-green-500" />
              ) : (
                <TrendingUp className="h-4 w-4 text-red-500 rotate-180" />
              )}
            </div>
          </div>
        );

      case CardType.CHART:
        // If we have a chart configuration, render the actual chart
        if (card.content.chartConfig) {
          return <ChartCard card={card} />;
        }
        // Otherwise, render placeholder
        return (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 mx-auto mb-3 text-gray-400" />
              <p className="text-sm font-medium mb-1" style={{ color: 'var(--corporate-gray-700)' }}>
                {card.content.chartType}
              </p>
              <p className="text-xs" style={{ color: 'var(--corporate-gray-500)' }}>
                {card.content.description}
              </p>
            </div>
          </div>
        );

      case CardType.TABLE:
        return (
          <div className="h-full flex flex-col overflow-hidden">
            <div className="flex-1 overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow className="h-8">
                    {card.content.headers?.map((header: string, index: number) => (
                      <TableHead key={index} className="text-xs py-2 font-semibold">
                        {header}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {card.content.rows?.slice(0, 5).map((row: unknown[], index: number) => (
                    <TableRow key={index} className="h-8">
                      {row.map((cell, cellIndex) => (
                        <TableCell key={cellIndex} className="text-xs py-2">
                          {String(cell)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {card.content.rows && card.content.rows.length > 5 && (
              <div className="flex-shrink-0 pt-2 border-t border-gray-200">
                <p className="text-xs text-center" style={{ color: 'var(--corporate-gray-500)' }}>
                  +{card.content.rows.length - 5} more rows
                </p>
              </div>
            )}
          </div>
        );

      case CardType.INSIGHT:
        return (
          <div className="h-full">
            <Alert className="h-full border-none shadow-none p-0">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <AlertTitle className="text-sm font-semibold mb-2">
                {card.content.title}
              </AlertTitle>
              <AlertDescription className="text-sm leading-relaxed">
                {card.content.description}
              </AlertDescription>
            </Alert>
          </div>
        );

      default:
        return (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <p className="text-sm" style={{ color: 'var(--corporate-gray-600)' }}>
                Custom content
              </p>
            </div>
          </div>
        );
    }
  };

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className={`h-full ${isDragging ? "z-50" : ""}`}
      whileHover={{ scale: 1.01 }}
      transition={{ duration: 0.2 }}
    >
      <div 
        className={`h-full corporate-card flex flex-col ${isDragging ? "ring-2 ring-blue-500 ring-opacity-50" : ""}`}
        style={{
          boxShadow: isDragging ? 'var(--shadow-xl)' : 'var(--shadow-sm)',
          transition: 'all var(--duration-normal) var(--ease-in-out)',
          minHeight: '200px'
        }}
      >
        {/* Card Header */}
        <div 
          className="flex-shrink-0 px-4 py-3 flex flex-row items-center justify-between"
          style={{
            borderBottom: '1px solid var(--corporate-gray-200)',
          }}
        >
          <h3 
            className="text-sm font-semibold truncate"
            style={{ color: 'var(--corporate-gray-900)' }}
          >
            {card.content.title}
          </h3>
          {card.isDraggable !== false && (
            <div
              {...listeners}
              className="cursor-grab active:cursor-grabbing p-1 rounded-md hover:bg-gray-100 transition-colors flex-shrink-0"
              data-testid="grip-handle"
            >
              <GripVertical 
                className="h-4 w-4"
                style={{ color: 'var(--corporate-gray-400)' }}
              />
            </div>
          )}
        </div>
        
        {/* Card Content */}
        <div className="flex-1 p-4 overflow-hidden flex flex-col">
          {renderCardContent()}
        </div>
      </div>
    </motion.div>
  );
}