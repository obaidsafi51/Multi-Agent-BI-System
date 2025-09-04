"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
            <div>
              <p className="text-lg font-bold">{card.content.value}</p>
              <p className="text-xs text-muted-foreground">{card.content.label}</p>
            </div>
            <div className="flex items-center gap-1">
              <Badge variant={card.content.trend === "up" ? "default" : "destructive"} className="text-xs">
                {card.content.change}
              </Badge>
              {card.content.trend === "up" ? (
                <TrendingUp className="h-3 w-3 text-green-500" />
              ) : (
                <TrendingUp className="h-3 w-3 text-red-500 rotate-180" />
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
              <BarChart3 className="h-8 w-8 mx-auto mb-1 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Chart: {card.content.chartType}</p>
              <p className="text-[10px] text-muted-foreground mt-1">{card.content.description}</p>
            </div>
          </div>
        );

      case CardType.TABLE:
        return (
          <div className="h-full overflow-auto">
            <Table>
              <TableHeader>
                <TableRow className="h-6">
                  {card.content.headers?.map((header: string, index: number) => (
                    <TableHead key={index} className="text-xs py-1">{header}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {card.content.rows?.slice(0, 3).map((row: unknown[], index: number) => (
                  <TableRow key={index} className="h-6">
                    {row.map((cell, cellIndex) => (
                      <TableCell key={cellIndex} className="text-xs py-1">{String(cell)}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {card.content.rows && card.content.rows.length > 3 && (
              <p className="text-[10px] text-muted-foreground text-center mt-1">
                +{card.content.rows.length - 3} more rows
              </p>
            )}
          </div>
        );

      case CardType.INSIGHT:
        return (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>{card.content.title}</AlertTitle>
            <AlertDescription className="mt-2">
              {card.content.description}
            </AlertDescription>
          </Alert>
        );

      default:
        return (
          <div className="h-full flex items-center justify-center">
            <p className="text-muted-foreground">Custom content</p>
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
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      <Card className={`h-full ${isDragging ? "shadow-lg" : ""} transition-shadow duration-200`}>
        <CardHeader className="pb-1 px-3 py-2 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-xs font-medium">{card.content.title}</CardTitle>
          {card.isDraggable !== false && (
            <div
              {...listeners}
              className="cursor-grab active:cursor-grabbing p-0.5 hover:bg-muted rounded"
              data-testid="grip-handle"
            >
              <GripVertical className="h-3 w-3 text-muted-foreground" />
            </div>
          )}
        </CardHeader>
        <CardContent className="pt-0 px-3 pb-2 h-[calc(100%-2.5rem)] overflow-hidden">
          {renderCardContent()}
        </CardContent>
      </Card>
    </motion.div>
  );
}