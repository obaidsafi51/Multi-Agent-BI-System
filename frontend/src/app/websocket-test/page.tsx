/**
 * WebSocket Test Page
 * Demonstrates real-time WebSocket functionality with the AGENT BI system
 */

"use client";

import { useState } from 'react';
import { ChatInterface } from '@/components/chat/chat-interface';
import { DatabaseContextProvider } from '@/contexts/DatabaseContext';
import { ChatMessage, QuerySuggestion } from '@/types/dashboard';

export default function WebSocketTestPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Mock suggestions for testing
  const suggestions: QuerySuggestion[] = [
    { id: '1', text: 'Show me quarterly revenue trends', category: 'Revenue', confidence: 0.95 },
    { id: '2', text: 'What are our top performing products?', category: 'Products', confidence: 0.90 },
    { id: '3', text: 'Analyze customer acquisition costs', category: 'Customers', confidence: 0.88 },
    { id: '4', text: 'Compare profit margins by region', category: 'Profitability', confidence: 0.92 }
  ];

  // Handle message sending (HTTP fallback)
  const handleSendMessage = async (content: string) => {
    setIsLoading(true);

    // Add user message
    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      content,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      // Simulate HTTP API call (fallback behavior)
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Add mock assistant response
      const assistantMessage: ChatMessage = {
        id: `assistant_${Date.now()}`,
        content: `I received your query: "${content}". Since this is using HTTP fallback, I'll provide a mock response. With WebSocket enabled, you would see real-time progress updates and streaming results.`,
        sender: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDatabaseSetup = () => {
    console.log('Database setup clicked');
  };

  return (
    <DatabaseContextProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-4">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">AI</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">WebSocket Test Environment</h1>
                  <p className="text-sm text-gray-600">Real-time AGENT BI Demo</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                  WebSocket Ready
                </div>
                <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                  Test Mode
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Instructions */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">WebSocket Testing Instructions</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
              <div>
                <h3 className="font-medium text-gray-900 mb-2">✅ What&apos;s Implemented:</h3>
                <ul className="space-y-1">
                  <li>• Real-time WebSocket connection status</li>
                  <li>• Query progress tracking with estimated time</li>
                  <li>• Streaming result display</li>
                  <li>• Connection state management</li>
                  <li>• Automatic reconnection & circuit breaker</li>
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-gray-900 mb-2">🔄 How to Test:</h3>
                <ul className="space-y-1">
                  <li>• Select a database from the header</li>
                  <li>• Ask any financial question</li>
                  <li>• Watch real-time progress updates</li>
                  <li>• See streaming results as they arrive</li>
                  <li>• Monitor connection status indicator</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Interface */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
          <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            <ChatInterface
              messages={messages}
              suggestions={suggestions}
              onSendMessage={handleSendMessage}
              isFullWidth={true}
              isLoading={isLoading}
              onDatabaseSetup={handleDatabaseSetup}
              selectedDatabase="financial_db"
              userId="test_user_123"
              enableWebSocket={true}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 border-t border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <div>
                WebSocket Test Environment - Task AE.1.4 Implementation
              </div>
              <div className="flex items-center gap-4">
                <span>Backend: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</span>
                <span>WebSocket: {process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DatabaseContextProvider>
  );
}
