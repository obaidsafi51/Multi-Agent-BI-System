"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
// Command components will be used for future autocomplete functionality
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Send, ThumbsUp, ThumbsDown, Sparkles } from "lucide-react";
import { ChatMessage, QuerySuggestion, UserFeedback } from "@/types/dashboard";
import { motion, AnimatePresence } from "framer-motion";

interface ChatInterfaceProps {
  messages: ChatMessage[];
  suggestions: QuerySuggestion[];
  onSendMessage: (content: string) => void;
}

export function ChatInterface({ messages, suggestions, onSendMessage }: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [feedbackDialog, setFeedbackDialog] = useState<{ open: boolean; messageId?: string }>({ open: false });
  const [feedbackComment, setFeedbackComment] = useState("");
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
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
      // Handle positive feedback directly
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

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <Card className="rounded-none border-0 border-b">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            AI CFO Assistant
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full p-4" ref={scrollAreaRef}>
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className={`mb-4 ${message.sender === "user" ? "ml-8" : "mr-8"}`}
              >
                <Card className={message.sender === "user" ? "bg-primary text-primary-foreground" : ""}>
                  <CardContent className="p-3">
                    <p className="text-sm">{message.content}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs opacity-70">
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                      {message.sender === "assistant" && (
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => handleFeedback(message.id, "positive")}
                            aria-label="Thumbs up"
                          >
                            <ThumbsUp className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => handleFeedback(message.id, "negative")}
                            aria-label="Thumbs down"
                          >
                            <ThumbsDown className="h-3 w-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </ScrollArea>
      </div>

      {/* Suggestions */}
      {showSuggestions && suggestions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="border-t p-4"
        >
          <h4 className="text-sm font-medium mb-2">Suggested queries:</h4>
          <div className="flex flex-wrap gap-2">
            {suggestions.slice(0, 3).map((suggestion) => (
              <Badge
                key={suggestion.id}
                variant="secondary"
                className="cursor-pointer hover:bg-secondary/80 transition-colors"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion.text}
              </Badge>
            ))}
          </div>
        </motion.div>
      )}

      {/* Input */}
      <Card className="rounded-none border-0 border-t">
        <CardContent className="p-4">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex gap-2">
              <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask about your financial data..."
                className="flex-1"
                onFocus={() => setShowSuggestions(true)}
              />
              <Button type="submit" size="sm" disabled={!inputValue.trim()} aria-label="Send message">
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => setShowSuggestions(!showSuggestions)}
            >
              {showSuggestions ? "Hide" : "Show"} Suggestions
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Feedback Dialog */}
      <Dialog open={feedbackDialog.open} onOpenChange={(open) => setFeedbackDialog({ open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Provide Feedback</DialogTitle>
            <DialogDescription>
              Help us improve by telling us what went wrong with this response.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={feedbackComment}
            onChange={(e) => setFeedbackComment(e.target.value)}
            placeholder="What could be improved?"
            className="min-h-[100px]"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setFeedbackDialog({ open: false })}>
              Cancel
            </Button>
            <Button onClick={submitFeedback}>Submit Feedback</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}