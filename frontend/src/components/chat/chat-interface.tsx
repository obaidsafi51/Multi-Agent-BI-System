"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Send, ThumbsUp, ThumbsDown, Sparkles, BarChart3, TrendingUp, PieChart, Activity } from "lucide-react";
import { ChatMessage, QuerySuggestion, UserFeedback } from "@/types/dashboard";
import { motion, AnimatePresence } from "framer-motion";
import { DatabaseSetupButton } from "../database-setup-button";

interface ChatInterfaceProps {
  messages: ChatMessage[];
  suggestions: QuerySuggestion[];
  onSendMessage: (content: string) => void;
  isFullWidth?: boolean; // New prop to handle full-width styling
  isLoading?: boolean; // Add loading state prop
  onDatabaseSetup?: () => void; // Add database setup callback
  selectedDatabase?: string | null; // Add selected database prop
}

export function ChatInterface({ messages, suggestions, onSendMessage, isFullWidth = false, isLoading = false, onDatabaseSetup, selectedDatabase }: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [feedbackDialog, setFeedbackDialog] = useState<{ open: boolean; messageId?: string }>({ open: false });
  const [feedbackComment, setFeedbackComment] = useState("");
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      console.log("ChatInterface: Sending message:", inputValue.trim());
      console.log("ChatInterface: Current messages count:", messages.length);
      onSendMessage(inputValue.trim());
      setInputValue("");
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion: QuerySuggestion) => {
    setInputValue(suggestion.text);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleFeedback = (messageId: string, rating: "positive" | "negative") => {
    if (rating === "negative") {
      setFeedbackDialog({ open: true, messageId });
    } else {
      console.log("Positive feedback for message:", messageId);
    }
  };

  const submitFeedback = () => {
    if (feedbackDialog.messageId) {
      const feedback: UserFeedback = {
        messageId: feedbackDialog.messageId,
        rating: "negative",
        comment: feedbackComment,
        timestamp: new Date(),
      };
      console.log("Feedback submitted:", feedback);
    }
    setFeedbackDialog({ open: false });
    setFeedbackComment("");
  };

  const suggestionsData = [
    { icon: BarChart3, text: "Show revenue trends", category: "Analytics" },
    { icon: TrendingUp, text: "Quarterly growth analysis", category: "Growth" },
    { icon: PieChart, text: "Expense breakdown", category: "Expenses" },
    { icon: Activity, text: "Performance metrics", category: "KPIs" },
  ];

  return (
    <div 
      className="h-full flex flex-col"
      style={{ 
        background: isFullWidth 
          ? 'linear-gradient(135deg, var(--corporate-gray-50), var(--corporate-blue-50))' 
          : 'transparent'
      }}
    >
      {/* Professional Header */}
      <div 
        className={`corporate-glass ${isFullWidth ? 'py-6 px-8' : 'py-4 px-6'}`}
        style={{
          borderBottom: '1px solid var(--corporate-gray-200)',
          boxShadow: 'var(--shadow-sm)'
        }}
      >
        <div className={`flex items-center ${isFullWidth ? 'justify-between' : 'justify-start'}`}>
          <div className="flex items-center gap-4">
            <div className="relative">
              <div 
                className="absolute inset-0 rounded-2xl blur-lg opacity-30"
                style={{ background: 'linear-gradient(135deg, var(--corporate-blue-600), var(--corporate-indigo-600))' }}
              ></div>
              <div 
                className="relative p-3 rounded-2xl"
                style={{ background: 'linear-gradient(135deg, var(--corporate-blue-600), var(--corporate-indigo-600))' }}
              >
                <Sparkles className={`${isFullWidth ? 'h-7 w-7' : 'h-5 w-5'} text-white`} />
              </div>
            </div>
            <div>
              <h1 
                className={`font-bold tracking-tight ${isFullWidth ? 'text-3xl' : 'text-xl'}`}
                style={{ color: 'var(--corporate-gray-900)' }}
              >
                AI CFO Assistant
              </h1>
              {isFullWidth && (
                <p 
                  className="mt-1 font-medium"
                  style={{ 
                    color: 'var(--corporate-gray-600)',
                    fontSize: 'var(--text-base)'
                  }}
                >
                  Your intelligent financial analytics platform
                </p>
              )}
            </div>
          </div>
          
          {/* Database Setup Button - Only show in full width mode */}
          {isFullWidth && (
            <div className="flex items-center">
              <DatabaseSetupButton 
                variant="secondary"
                size="sm"
                selectedDatabase={selectedDatabase}
                onClick={() => onDatabaseSetup?.()}
                onDatabaseSelected={(dbName) => {
                  console.log("Database selected from header:", dbName);
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className={`h-full ${isFullWidth ? 'p-8' : 'p-6'}`} ref={scrollAreaRef}>
          {isFullWidth && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full">
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="max-w-4xl mx-auto text-center space-y-12"
              >
                {/* Hero Section */}
                <div className="space-y-6">
                  <div className="relative inline-block">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-600/30 to-indigo-600/30 rounded-full blur-3xl scale-150"></div>
                    <div className="relative bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 p-8 rounded-3xl border border-blue-200/50 dark:border-blue-800/50 shadow-xl">
                      <div className="text-6xl mb-2">📊</div>
                      <div className="absolute top-4 right-4 w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <h2 className="text-4xl font-bold text-slate-900 dark:text-white tracking-tight">
                      Welcome to your 
                      <span className="block bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                        AI-Powered CFO Dashboard
                      </span>
                    </h2>
                    <p className="text-xl text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl mx-auto">
                      Transform complex financial data into actionable insights. Generate comprehensive reports, 
                      analyze trends, and make data-driven decisions with confidence.
                    </p>
                  </div>
                </div>

                {/* Corporate Features */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mt-16">
                  {suggestionsData.map((item, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.6, delay: 0.2 + index * 0.1 }}
                      onClick={() => handleSuggestionClick({ id: index.toString(), text: item.text, category: item.category, confidence: 0.9 })}
                      className="group cursor-pointer relative"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-300 opacity-0 group-hover:opacity-100"></div>
                      <div className="relative p-6 rounded-2xl border border-slate-200/60 dark:border-slate-700/60 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm hover:bg-white dark:hover:bg-slate-800 hover:shadow-2xl hover:shadow-blue-500/10 transition-all duration-300 hover:-translate-y-1">
                        <div className="flex flex-col items-center gap-4 text-center">
                          <div className="p-3 rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 group-hover:from-blue-100 dark:group-hover:from-blue-800/50 transition-all duration-300">
                            <item.icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                          </div>
                          <div>
                            <div className="font-semibold text-slate-900 dark:text-white text-sm mb-1">
                              {item.text}
                            </div>
                            <div className="text-xs text-blue-600 dark:text-blue-400 font-medium uppercase tracking-wider">
                              {item.category}
                            </div>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>

                {/* Getting Started */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.8 }}
                  className="mt-16 p-6 rounded-2xl bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200/50 dark:border-blue-800/50"
                >
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                    Getting Started
                  </h3>
                  <p className="text-slate-600 dark:text-slate-300 text-sm">
                    Try asking: <span className="font-medium text-blue-600 dark:text-blue-400">&ldquo;Show me quarterly revenue trends&rdquo;</span> or{' '}
                    <span className="font-medium text-blue-600 dark:text-blue-400">&ldquo;What&apos;s our profit margin analysis?&rdquo;</span>
                  </p>
                </motion.div>
              </motion.div>
            </div>
          )}

          <AnimatePresence>
            {messages.map((message) => {
              console.log("Rendering message:", message.id, message.sender, message.content.substring(0, 50));
              return (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -20, scale: 0.95 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className={`mb-8 ${message.sender === "user" ? "flex justify-end" : "flex justify-start"}`}
                >
                  <div className={`max-w-[85%] ${message.sender === "user" ? "order-2" : "order-1"}`}>
                    {/* Message Bubble */}
                    <div className="relative">
                      {message.sender === "user" ? (
                        <div className="relative">
                          <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur-sm opacity-30"></div>
                          <div className="relative p-4 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
                            <p className="text-sm leading-relaxed font-medium">{message.content}</p>
                          </div>
                        </div>
                      ) : (
                        <div className="relative">
                          <div className="p-4 rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                            <p className="text-sm leading-relaxed text-slate-900 dark:text-white">{message.content}</p>
                          </div>
                          {/* Assistant indicator */}
                          <div className="absolute -left-2 top-4 w-3 h-3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full border-2 border-white dark:border-slate-800"></div>
                        </div>
                      )}
                    </div>

                    {/* Message Footer */}
                    <div className={`flex items-center mt-3 gap-3 ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
                      <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                      {message.sender === "assistant" && (
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 hover:bg-green-100 dark:hover:bg-green-900/30 rounded-full transition-all duration-200"
                            onClick={() => handleFeedback(message.id, "positive")}
                            aria-label="Thumbs up"
                          >
                            <ThumbsUp className="h-3 w-3 text-slate-400 hover:text-green-600 dark:hover:text-green-400" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-full transition-all duration-200"
                            onClick={() => handleFeedback(message.id, "negative")}
                            aria-label="Thumbs down"
                          >
                            <ThumbsDown className="h-3 w-3 text-slate-400 hover:text-red-600 dark:hover:text-red-400" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </ScrollArea>
      </div>

      {/* Enhanced Suggestions Bar */}
      <AnimatePresence>
        {showSuggestions && suggestions.length > 0 && !isFullWidth && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-slate-200 dark:border-slate-700 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 dark:from-blue-900/10 dark:to-indigo-900/10"
          >
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Quick Analytics</h4>
              </div>
              <div className="flex flex-wrap gap-3">
                {suggestions.slice(0, 3).map((suggestion) => (
                  <motion.div
                    key={suggestion.id}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Badge
                      variant="secondary"
                      className="cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/30 hover:text-blue-700 dark:hover:text-blue-300 transition-all duration-300 border border-slate-200 dark:border-slate-600 px-4 py-2 rounded-xl font-medium shadow-sm hover:shadow-md"
                      onClick={() => handleSuggestionClick(suggestion)}
                    >
                      {suggestion.text}
                    </Badge>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Professional Input Area */}
      <div 
        className={`corporate-glass ${isFullWidth ? 'p-8' : 'p-6'}`}
        style={{
          borderTop: '1px solid var(--corporate-gray-200)'
        }}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className={`relative ${isFullWidth ? 'max-w-4xl mx-auto' : 'w-full'}`}>
            <div className="relative w-full">
              <div className="flex-1 relative group w-full">
                <div 
                  className="absolute inset-0 rounded-2xl blur-lg opacity-0 group-focus-within:opacity-100 transition-opacity duration-300"
                  style={{ background: 'linear-gradient(135deg, var(--corporate-blue-500), var(--corporate-indigo-500))' }}
                ></div>
                <Textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={isLoading ? "Processing your query..." : "Ask about your financial data, request analytics, or generate reports..."}
                  disabled={isLoading}
                  className={`
                    relative w-full rounded-2xl resize-none
                    bg-white shadow-lg focus:shadow-xl
                    transition-all duration-300 placeholder:text-slate-400
                    focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500
                    ${isFullWidth ? 'text-lg pl-6 pr-15' : 'pl-5 pr-15'}
                    ${isLoading ? 'opacity-60 cursor-not-allowed bg-gray-50' : ''}
                  `}
                  style={{
                    border: '1px solid var(--corporate-gray-300)',
                    minHeight: isFullWidth ? '64px' : '56px',
                    maxHeight: isFullWidth ? '128px' : '96px',
                    paddingTop: isFullWidth ? '20px' : '16px',
                    paddingBottom: isFullWidth ? '20px' : '16px',
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                />
                
                {/* Send Button at Bottom Right */}
                <Button
                  type="submit"
                  disabled={!inputValue.trim() || isLoading}
                  className={`
                    absolute right-2 bottom-2
                    rounded-full cursor-pointer text-white shadow-lg
                    disabled:opacity-50 disabled:cursor-not-allowed 
                    transition-all duration-500 ease-in-out
                    ${isFullWidth ? 'h-12 w-12' : 'h-10 w-10'}
                  `}
                  style={{
                    background: 'linear-gradient(135deg, var(--corporate-blue-600), var(--corporate-indigo-600))',
                    backgroundImage: inputValue.trim() 
                      ? 'linear-gradient(135deg, var(--corporate-blue-700), var(--corporate-indigo-700))'
                      : 'linear-gradient(135deg, var(--corporate-blue-600), var(--corporate-indigo-600))'
                  }}
                  onMouseEnter={(e) => {
                    if (!e.currentTarget.disabled) {
                      e.currentTarget.style.background = 'linear-gradient(135deg, var(--corporate-blue-700), var(--corporate-indigo-700))';
                      e.currentTarget.style.transform = 'scale(1.05)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!e.currentTarget.disabled) {
                      e.currentTarget.style.background = 'linear-gradient(135deg, var(--corporate-blue-600), var(--corporate-indigo-600))';
                      e.currentTarget.style.transform = 'scale(1)';
                    }
                  }}
                  aria-label={isLoading ? "Processing..." : "Send message"}
                >
                  {isLoading ? (
                    <div className={`animate-spin rounded-full border-2 border-white border-t-transparent ${isFullWidth ? 'h-5 w-5' : 'h-4 w-4'}`}></div>
                  ) : (
                    <Send className={`${isFullWidth ? 'h-5 w-5' : 'h-4 w-4'}`} />
                  )}
                </Button>
              </div>
            </div>
          </div>

          {!isFullWidth && (
            <div className="flex justify-center">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl px-4 py-2 transition-all duration-200"
                onClick={() => setShowSuggestions(!showSuggestions)}
              >
                {showSuggestions ? "Hide" : "Show"} quick suggestions
              </Button>
            </div>
          )}
        </form>
      </div>

      {/* Enhanced Feedback Dialog */}
      <Dialog open={feedbackDialog.open} onOpenChange={(open) => setFeedbackDialog({ open })}>
        <DialogContent className="rounded-2xl border-slate-200 dark:border-slate-700 shadow-2xl max-w-md">
          <DialogHeader className="text-left">
            <DialogTitle className="text-slate-900 dark:text-white text-xl font-semibold flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                💬
              </div>
              Feedback
            </DialogTitle>
            <DialogDescription className="text-slate-600 dark:text-slate-400 mt-2">
              Help us improve our AI responses. Your feedback helps us provide better financial insights.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <Textarea
              value={feedbackComment}
              onChange={(e) => setFeedbackComment(e.target.value)}
              placeholder="What could be improved? Be specific about accuracy, relevance, or clarity..."
              className="min-h-[120px] rounded-xl border-slate-200 dark:border-slate-700 focus:border-blue-500 dark:focus:border-blue-400 resize-none"
            />
          </div>
          <DialogFooter className="gap-3 pt-6">
            <Button
              variant="outline"
              onClick={() => setFeedbackDialog({ open: false })}
              className="rounded-xl border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              Cancel
            </Button>
            <Button
              onClick={submitFeedback}
              className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg"
            >
              Submit Feedback
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}