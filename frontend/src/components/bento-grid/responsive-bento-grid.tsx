"use client";

import { useState, useEffect } from "react";
import { BentoGrid } from "./bento-grid";
import { BentoGridCard, CardSize } from "@/types/dashboard";

interface ResponsiveBentoGridProps {
  cards: BentoGridCard[];
  onCardsUpdate: (cards: BentoGridCard[]) => void;
}

export function ResponsiveBentoGrid({ cards, onCardsUpdate }: ResponsiveBentoGridProps) {
  const [screenSize, setScreenSize] = useState<"mobile" | "tablet" | "desktop">("desktop");

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width < 768) {
        setScreenSize("mobile");
      } else if (width < 1024) {
        setScreenSize("tablet");
      } else {
        setScreenSize("desktop");
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const adaptCardsForScreen = (cards: BentoGridCard[]): BentoGridCard[] => {
    return cards.map(card => {
      let adaptedSize = card.size;
      
      if (screenSize === "mobile") {
        // On mobile, make all cards smaller and stack vertically
        if (card.size === CardSize.LARGE || card.size === CardSize.EXTRA_LARGE) {
          adaptedSize = CardSize.MEDIUM_H;
        }
      } else if (screenSize === "tablet") {
        // On tablet, reduce extra large cards
        if (card.size === CardSize.EXTRA_LARGE) {
          adaptedSize = CardSize.LARGE;
        }
      }

      return {
        ...card,
        size: adaptedSize
      };
    });
  };

  const adaptedCards = adaptCardsForScreen(cards);

  const getGridClass = () => {
    switch (screenSize) {
      case "mobile":
        return "grid-cols-2";
      case "tablet":
        return "grid-cols-4";
      default:
        return "grid-cols-6";
    }
  };

  return (
    <div className="h-full p-6 overflow-auto">
      <div className={`grid ${getGridClass()} gap-4 auto-rows-[200px] h-fit min-h-full`}>
        <BentoGrid cards={adaptedCards} onCardsUpdate={onCardsUpdate} />
      </div>
    </div>
  );
}