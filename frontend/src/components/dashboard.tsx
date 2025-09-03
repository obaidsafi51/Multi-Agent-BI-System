"use client";
import React from "react";

import { ChatInterface } from "./chat/chat-interface";
import { BentoGrid } from "./bento-grid/bento-grid";
import { Separator } from "@/components/ui/separator";
import { BentoGridCard } from "@/types/dashboard";
import { useRealData } from "@/hooks/useRealData";

export default function Dashboard() {
  const {
    chatMessages,
    bentoCards,
    suggestions,
    error,
    sendMessage,
    refreshDashboard,
    clearError,
  } = useRealData();

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  const handleCardUpdate = (updatedCards: BentoGridCard[]) => {
    // For now, we don't need to handle card updates from drag/drop
    // This would be where we'd sync card positions back to the server
    console.log("Cards updated:", updatedCards);
  };

  // Show error message if there's an error
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="space-x-2">
            <button
              onClick={clearError}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Dismiss
            </button>
            <button
              onClick={refreshDashboard}
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex bg-background">
      {/* Chat Interface - 30% */}
      <div className="w-[30%] min-w-[320px] border-r border-border">
        <ChatInterface
          messages={chatMessages}
          suggestions={suggestions}
          onSendMessage={handleSendMessage}
        />
      </div>

      <Separator orientation="vertical" />

      {/* Dashboard - 70% */}
      <div className="flex-1 overflow-hidden">
        <BentoGrid
          cards={bentoCards}
          onCardsUpdate={handleCardUpdate}
        />
      </div>
    </div>
  );
}