"use client";

import React, { useState } from "react";
import { DatabaseSelectorModal } from "./database-selector-modal";

interface DatabaseSetupButtonProps {
  onDatabaseSelected?: (databaseName: string) => void;
  onClick?: () => void; // Add onClick prop for external modal management
  selectedDatabase?: string | null; // Add prop for current database
  className?: string;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
}

export const DatabaseSetupButton: React.FC<DatabaseSetupButtonProps> = ({
  onDatabaseSelected,
  onClick,
  selectedDatabase: propSelectedDatabase,
  className = "",
  variant = "primary",
  size = "md"
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [localSelectedDatabase, setLocalSelectedDatabase] = useState<string | null>(null);
  
  // Use prop selectedDatabase if provided, otherwise use local state
  const selectedDatabase = propSelectedDatabase !== undefined ? propSelectedDatabase : localSelectedDatabase;

  const handleDatabaseSelect = (databaseName: string) => {
    setLocalSelectedDatabase(databaseName);
    onDatabaseSelected?.(databaseName);
  };

  const handleClick = () => {
    if (onClick) {
      onClick(); // Use external modal management
    } else {
      setIsModalOpen(true); // Fallback to internal modal
    }
  };

  const getButtonClasses = () => {
    // Use corporate design system classes for consistency
    let baseClasses = "flex items-center gap-2";
    
    switch (variant) {
      case "primary":
        baseClasses += selectedDatabase
          ? " corporate-button-primary bg-green-600 hover:bg-green-700 border-green-500"
          : " corporate-button-primary";
        break;
      case "secondary":
        baseClasses += selectedDatabase
          ? " corporate-button-secondary bg-green-50 hover:bg-green-100 text-green-800 border-green-300"
          : " corporate-button-secondary";
        break;
      case "ghost":
        baseClasses += selectedDatabase
          ? " text-green-700 hover:bg-green-50 border border-transparent hover:border-green-200 rounded-lg px-3 py-2 transition-all"
          : " text-gray-700 hover:bg-gray-50 border border-transparent hover:border-gray-200 rounded-lg px-3 py-2 transition-all";
        break;
    }

    // Add size-specific classes
    switch (size) {
      case "sm":
        baseClasses += " text-xs px-3 py-2"; // Match refresh button exactly
        break;
      case "md":
        baseClasses += " text-sm px-4 py-2.5";
        break;
      case "lg":
        baseClasses += " text-base px-6 py-3";
        break;
    }

    return `${baseClasses} ${className}`;
  };

  const getIcon = () => {
    // Make icons larger as requested, and consistent with refresh button sizing
    const iconSize = size === "sm" ? "w-4 h-4" : size === "md" ? "w-5 h-5" : "w-6 h-6";
    
    if (selectedDatabase) {
      return (
        <div className="flex items-center">
          <svg className={`${iconSize} mr-1`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <svg className={iconSize} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
        </div>
      );
    }
    
    return (
      <svg className={iconSize} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
      </svg>
    );
  };

  const getButtonText = () => {
    if (selectedDatabase) {
      return `Database: ${selectedDatabase}`;
    }
    return "Setup Database";
  };

  return (
    <>
      <button
        onClick={handleClick}
        className={getButtonClasses()}
        title={selectedDatabase ? `Currently using: ${selectedDatabase}` : "Click to setup database connection"}
      >
        {getIcon()}
        <span>{getButtonText()}</span>
        
        {selectedDatabase && (
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse ml-1"></div>
        )}
      </button>

      {/* Only show modal if not using external modal management */}
      {!onClick && (
        <DatabaseSelectorModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onDatabaseSelect={handleDatabaseSelect}
        />
      )}
    </>
  );
};
