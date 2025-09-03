"use client";

import { useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from "@dnd-kit/sortable";
import { BentoGridCard } from "@/types/dashboard";
import { DraggableCard } from "./draggable-card";
import { motion } from "framer-motion";

interface BentoGridProps {
  cards: BentoGridCard[];
  onCardsUpdate: (cards: BentoGridCard[]) => void;
}

export function BentoGrid({ cards, onCardsUpdate }: BentoGridProps) {
  const [isDragging, setIsDragging] = useState(false);
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragStart = () => {
    setIsDragging(true);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setIsDragging(false);
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = cards.findIndex((card) => card.id === active.id);
      const newIndex = cards.findIndex((card) => card.id === over?.id);
      
      const newCards = arrayMove(cards, oldIndex, newIndex);
      onCardsUpdate(newCards);
    }
  };

  const getGridClass = (size: string) => {
    switch (size) {
      case "1x1":
        return "col-span-1 row-span-1";
      case "2x1":
        return "col-span-2 row-span-1";
      case "1x2":
        return "col-span-1 row-span-2";
      case "2x2":
        return "col-span-2 row-span-2";
      case "3x2":
        return "col-span-3 row-span-2";
      default:
        return "col-span-1 row-span-1";
    }
  };

  return (
    <div className="h-full overflow-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="h-full"
      >
        {cards.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 mx-auto mb-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2">
                Welcome to your AI CFO Dashboard
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                Start by asking questions about your financial data in the chat panel
              </p>
              <div className="text-xs text-slate-500 dark:text-slate-500">
                Try: &quot;Show me quarterly revenue trends&quot; or &quot;What&apos;s our profit margin?&quot;
              </div>
            </div>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={cards.map(card => card.id)} strategy={rectSortingStrategy}>
              <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 auto-rows-[140px] h-fit min-h-full">
                {cards.map((card, index) => (
                  <motion.div
                    key={card.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: index * 0.1 }}
                    className={`${getGridClass(card.size)} transition-all duration-300 ${
                      isDragging ? "opacity-50" : "opacity-100"
                    }`}
                  >
                    <DraggableCard card={card} />
                  </motion.div>
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </motion.div>
    </div>
  );
}