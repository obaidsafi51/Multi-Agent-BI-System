"use client";

import React from "react";
import { motion } from "framer-motion";
import { useDatabaseContext } from "@/contexts/DatabaseContext";

interface DatabaseStatusIndicatorProps {
  showDetails?: boolean;
  className?: string;
}

export const DatabaseStatusIndicator: React.FC<DatabaseStatusIndicatorProps> = ({
  showDetails = false,
  className = ""
}) => {
  const {
    selectedDatabase,
    databaseContext,
    isLoadingDatabases,
    isSelectingDatabase,
    error
  } = useDatabaseContext();

  // Determine status
  const getStatus = () => {
    if (isLoadingDatabases || isSelectingDatabase) {
      return {
        color: "yellow",
        text: "Connecting...",
        icon: "loading"
      };
    }
    
    if (error) {
      return {
        color: "red",
        text: "Connection Error",
        icon: "error"
      };
    }
    
    if (selectedDatabase && databaseContext) {
      return {
        color: "green",
        text: `Connected to ${selectedDatabase.name}`,
        icon: "connected"
      };
    }
    
    return {
      color: "gray",
      text: "No Database Selected",
      icon: "disconnected"
    };
  };

  const status = getStatus();

  // Status indicator colors
  const getColorClasses = (color: string) => {
    switch (color) {
      case "green":
        return {
          dot: "bg-green-500",
          text: "text-green-700",
          bg: "bg-green-50",
          border: "border-green-200"
        };
      case "red":
        return {
          dot: "bg-red-500",
          text: "text-red-700",
          bg: "bg-red-50",
          border: "border-red-200"
        };
      case "yellow":
        return {
          dot: "bg-yellow-500",
          text: "text-yellow-700",
          bg: "bg-yellow-50",
          border: "border-yellow-200"
        };
      default:
        return {
          dot: "bg-gray-400",
          text: "text-gray-600",
          bg: "bg-gray-50",
          border: "border-gray-200"
        };
    }
  };

  const colors = getColorClasses(status.color);

  // Render status icon
  const renderStatusIcon = () => {
    switch (status.icon) {
      case "loading":
        return (
          <div className="w-2 h-2 border border-yellow-500 border-t-transparent rounded-full animate-spin" />
        );
      case "connected":
        return <div className={`w-2 h-2 rounded-full ${colors.dot}`} />;
      case "error":
        return (
          <svg className="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      default:
        return <div className={`w-2 h-2 rounded-full ${colors.dot}`} />;
    }
  };

  if (!showDetails) {
    // Simple indicator
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`flex items-center gap-2 ${className}`}
        title={status.text}
      >
        {renderStatusIcon()}
        <span className={`text-sm font-medium ${colors.text}`}>
          {selectedDatabase ? selectedDatabase.name : "No Database"}
        </span>
      </motion.div>
    );
  }

  // Detailed indicator
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        flex items-center gap-3 px-3 py-2 rounded-lg ${colors.bg} ${colors.border} border
        ${className}
      `}
    >
      <div className="flex items-center gap-2">
        {renderStatusIcon()}
        <span className={`text-sm font-medium ${colors.text}`}>
          {status.text}
        </span>
      </div>
      
      {/* Additional details */}
      {selectedDatabase && databaseContext && !isLoadingDatabases && !error && (
        <div className="flex items-center gap-4 text-xs text-gray-500 border-l border-gray-300 pl-3">
          <span>{databaseContext.total_tables} tables</span>
          <span>Schema ready</span>
        </div>
      )}
      
      {/* Error details */}
      {error && (
        <div className="text-xs text-red-600 border-l border-red-300 pl-3 truncate max-w-48">
          {error}
        </div>
      )}
    </motion.div>
  );
};

export default DatabaseStatusIndicator;
