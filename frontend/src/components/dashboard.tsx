"use client";
import React from "react";

import { useState } from "react";
import { ChatInterface } from "./chat/chat-interface";
import { BentoGrid } from "./bento-grid/bento-grid";
import { Separator } from "@/components/ui/separator";
import { BentoGridCard, ChatMessage, QuerySuggestion } from "@/types/dashboard";
import { mockBentoCards, mockChatMessages, mockSuggestions } from "@/lib/mock-data";

export default function Dashboard() {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(mockChatMessages);
  const [bentoCards, setBentoCards] = useState<BentoGridCard[]>(mockBentoCards);
  const [suggestions] = useState<QuerySuggestion[]>(mockSuggestions);

  const handleSendMessage = (content: string) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      content,
      sender: "user",
      timestamp: new Date(),
    };
    
    setChatMessages(prev => [...prev, newMessage]);
    
    // Simulate assistant response
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: `I understand you're asking about "${content}". Let me analyze that for you and update the dashboard.`,
        sender: "assistant",
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, assistantMessage]);
    }, 1000);
  };

  const handleCardUpdate = (updatedCards: BentoGridCard[]) => {
    setBentoCards(updatedCards);
  };

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