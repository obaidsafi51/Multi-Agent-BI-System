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
              <p className="text-2xl font-bold">{card.content.value}</p>
              <p className="text-sm text-muted-foreground">{card.content.label}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={card.content.trend === "up" ? "default" : "destructive"}>
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
        return (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Chart: {card.content.chartType}</p>
              <p className="text-xs text-muted-foreground mt-1">{card.content.description}</p>
            </div>
          </div>
        );

      case CardType.TABLE:
        return (
          <div className="h-full overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {card.content.headers?.map((header: string, index: number) => (
                    <TableHead key={index}>{header}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {card.content.rows?.slice(0, 3).map((row: unknown[], index: number) => (
                  <TableRow key={index}>
                    {row.map((cell, cellIndex) => (
                      <TableCell key={cellIndex}>{String(cell)}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {card.content.rows && card.content.rows.length > 3 && (
              <p className="text-xs text-muted-foreground text-center mt-2">
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
        <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm font-medium">{card.content.title}</CardTitle>
          {card.isDraggable !== false && (
            <div
              {...listeners}
              className="cursor-grab active:cursor-grabbing p-1 hover:bg-muted rounded"
              data-testid="grip-handle"
            >
              <GripVertical className="h-4 w-4 text-muted-foreground" />
            </div>
          )}
        </CardHeader>
        <CardContent className="pt-0 h-[calc(100%-4rem)] overflow-hidden">
          {renderCardContent()}
        </CardContent>
      </Card>
    </motion.div>
  );
}