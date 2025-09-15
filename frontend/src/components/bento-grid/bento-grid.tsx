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
    // Using CSS Grid with proper responsive column spans
    switch (size) {
      case "1x1":
        return "col-span-1 row-span-1";
      case "2x1":
        return "col-span-1 md:col-span-2 row-span-1";
      case "1x2":
        return "col-span-1 row-span-2";
      case "2x2":
        return "col-span-1 md:col-span-2 row-span-2";
      case "3x2":
        return "col-span-1 md:col-span-2 lg:col-span-3 row-span-2";
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
            <div className="text-center max-w-md">
              <div 
                className="w-16 h-16 mx-auto mb-4 rounded-xl flex items-center justify-center"
                style={{ 
                  background: 'linear-gradient(135deg, var(--corporate-blue-500), var(--corporate-indigo-600))',
                  boxShadow: 'var(--shadow-lg)'
                }}
              >
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 
                className="text-xl font-semibold mb-3"
                style={{ color: 'var(--corporate-gray-900)' }}
              >
                Welcome to your AGENT BI Dashboard
              </h3>
              <p 
                className="text-base mb-4 leading-relaxed"
                style={{ color: 'var(--corporate-gray-600)' }}
              >
                Start by asking questions about your financial data in the chat panel. I&apos;ll analyze your data and create interactive charts and insights.
              </p>
              <div 
                className="text-sm space-y-2 p-4 rounded-lg"
                style={{ 
                  color: 'var(--corporate-gray-500)',
                  backgroundColor: 'var(--corporate-blue-50)',
                  border: '1px solid var(--corporate-blue-200)'
                }}
              >
                <p className="font-medium">Try asking:</p>
                <p>&quot;Show me quarterly revenue trends&quot;</p>
                <p>&quot;What&apos;s our profit margin this year?&quot;</p>
                <p>&quot;Compare expenses by department&quot;</p>
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
              <div 
                className="grid gap-4 p-1" 
                style={{
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gridAutoRows: 'minmax(160px, auto)',
                  minHeight: '100%'
                }}
              >
                {cards.map((card, index) => (
                  <motion.div
                    key={card.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: index * 0.1 }}
                    className={`${getGridClass(card.size)} ${
                      isDragging ? "opacity-70" : "opacity-100"
                    }`}
                    style={{
                      minHeight: card.size.includes('2x') ? '280px' : '160px',
                      transition: 'all var(--duration-normal) var(--ease-in-out)'
                    }}
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