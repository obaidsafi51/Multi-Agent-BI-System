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
    <div className="h-full p-6 overflow-auto">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="h-full"
      >
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={cards.map(card => card.id)} strategy={rectSortingStrategy}>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 auto-rows-[200px] h-fit min-h-full">
              {cards.map((card) => (
                <div
                  key={card.id}
                  className={`${getGridClass(card.size)} transition-all duration-300 ${
                    isDragging ? "opacity-50" : "opacity-100"
                  }`}
                >
                  <DraggableCard card={card} />
                </div>
              ))}
            </div>
          </SortableContext>
        </DndContext>
      </motion.div>
    </div>
  );
}