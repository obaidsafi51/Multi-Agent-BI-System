/**
 * Query Progress Display Component
 * Shows real-time progress updates for WebSocket queries
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import {
  QueryProgressDisplayProps,
  QueryProgressStatus,
  QUERY_PROGRESS_STEPS
} from '@/types/websocket';

export function QueryProgressDisplay({
  queryState,
  showEstimatedTime = true,
  showDetailedSteps = true,
  compact = false
}: QueryProgressDisplayProps) {
  
  // Get current step information
  const currentStepInfo = queryState.current_step 
    ? QUERY_PROGRESS_STEPS[queryState.current_step]
    : null;
  
  // Format time remaining
  const formatTimeRemaining = (seconds: number): string => {
    if (seconds < 60) {
      return `${Math.ceil(seconds)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${Math.ceil(remainingSeconds)}s`;
  };

  // Get status color and icon
  const getStatusDisplay = (status: QueryProgressStatus) => {
    switch (status) {
      case QueryProgressStatus.QUEUED:
        return {
          color: 'text-gray-600',
          bgColor: 'bg-gray-100',
          icon: <Clock className="h-4 w-4" />,
          label: 'Queued'
        };
      case QueryProgressStatus.PROCESSING:
      case QueryProgressStatus.ANALYZING:
      case QueryProgressStatus.GENERATING_SQL:
      case QueryProgressStatus.EXECUTING_QUERY:
      case QueryProgressStatus.GENERATING_VISUALIZATION:
        return {
          color: 'text-blue-600',
          bgColor: 'bg-blue-100',
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          label: 'Processing'
        };
      case QueryProgressStatus.COMPLETED:
        return {
          color: 'text-green-600',
          bgColor: 'bg-green-100',
          icon: <CheckCircle className="h-4 w-4" />,
          label: 'Completed'
        };
      case QueryProgressStatus.ERROR:
        return {
          color: 'text-red-600',
          bgColor: 'bg-red-100',
          icon: <XCircle className="h-4 w-4" />,
          label: 'Error'
        };
      default:
        return {
          color: 'text-gray-600',
          bgColor: 'bg-gray-100',
          icon: <AlertCircle className="h-4 w-4" />,
          label: 'Unknown'
        };
    }
  };

  const statusDisplay = getStatusDisplay(queryState.status);

  // Compact version for inline display
  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex items-center gap-3 p-3 rounded-lg bg-white/80 backdrop-blur-sm border border-gray-200 shadow-sm"
      >
        <div className={`p-1.5 rounded-full ${statusDisplay.bgColor}`}>
          {statusDisplay.icon}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900">
              {currentStepInfo?.label || statusDisplay.label}
            </span>
            {showEstimatedTime && queryState.estimated_time_remaining && (
              <Badge variant="secondary" className="text-xs">
                ~{formatTimeRemaining(queryState.estimated_time_remaining)}
              </Badge>
            )}
          </div>
          
          <Progress 
            value={queryState.progress} 
            className="h-2 w-full"
          />
          
          {currentStepInfo?.description && (
            <p className="text-xs text-gray-500 mt-1 truncate">
              {currentStepInfo.description}
            </p>
          )}
        </div>
      </motion.div>
    );
  }

  // Full version for detailed display
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full"
    >
      <Card className="border-0 shadow-lg bg-gradient-to-br from-blue-50/50 to-indigo-50/50 backdrop-blur-sm">
        <CardContent className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${statusDisplay.bgColor}`}>
                {statusDisplay.icon}
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">
                  Query Processing
                </h3>
                <p className="text-sm text-gray-600">
                  {queryState.query_text.length > 50 
                    ? `${queryState.query_text.substring(0, 50)}...`
                    : queryState.query_text
                  }
                </p>
              </div>
            </div>
            
            <Badge 
              variant={queryState.status === QueryProgressStatus.ERROR ? "destructive" : "default"}
              className="font-medium"
            >
              {statusDisplay.label}
            </Badge>
          </div>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Progress: {queryState.progress}%
              </span>
              
              {showEstimatedTime && queryState.estimated_time_remaining && (
                <span className="text-sm text-gray-500 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatTimeRemaining(queryState.estimated_time_remaining)} remaining
                </span>
              )}
            </div>
            
            <Progress 
              value={queryState.progress} 
              className="h-3 w-full"
            />
          </div>

          {/* Current Step */}
          {currentStepInfo && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-4 p-4 rounded-lg bg-white/60 border border-blue-200/50"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{currentStepInfo.icon}</span>
                <span className="font-medium text-gray-900">
                  {currentStepInfo.label}
                </span>
              </div>
              <p className="text-sm text-gray-600">
                {currentStepInfo.description}
              </p>
            </motion.div>
          )}

          {/* Detailed Steps Progress */}
          {showDetailedSteps && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                Processing Steps
              </h4>
              
              {Object.values(QUERY_PROGRESS_STEPS).map((step, index) => {
                const isCurrentStep = queryState.current_step === step.step;
                const isCompletedStep = queryState.progress > (index * 100 / Object.keys(QUERY_PROGRESS_STEPS).length);
                
                return (
                  <motion.div
                    key={step.step}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`flex items-center gap-3 p-2 rounded-md transition-all duration-300 ${
                      isCurrentStep 
                        ? 'bg-blue-100 border border-blue-200' 
                        : isCompletedStep 
                        ? 'bg-green-50 border border-green-200'
                        : 'bg-gray-50 border border-gray-200'
                    }`}
                  >
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                      isCurrentStep
                        ? 'bg-blue-500 text-white'
                        : isCompletedStep
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-300 text-gray-600'
                    }`}>
                      {isCurrentStep ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : isCompletedStep ? (
                        <CheckCircle className="h-3 w-3" />
                      ) : (
                        index + 1
                      )}
                    </div>
                    
                    <div className="flex-1">
                      <span className={`text-sm font-medium ${
                        isCurrentStep ? 'text-blue-900' : isCompletedStep ? 'text-green-900' : 'text-gray-500'
                      }`}>
                        {step.label}
                      </span>
                      <p className={`text-xs ${
                        isCurrentStep ? 'text-blue-700' : isCompletedStep ? 'text-green-700' : 'text-gray-400'
                      }`}>
                        {step.description}
                      </p>
                    </div>
                    
                    {isCurrentStep && (
                      <motion.div
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 1, repeat: Infinity }}
                        className="w-2 h-2 bg-blue-500 rounded-full"
                      />
                    )}
                  </motion.div>
                );
              })}
            </div>
          )}

          {/* Error Display */}
          {queryState.error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 p-4 rounded-lg bg-red-50 border border-red-200"
            >
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="h-4 w-4 text-red-600" />
                <span className="font-medium text-red-900">Error Occurred</span>
              </div>
              <p className="text-sm text-red-700">
                {queryState.error}
              </p>
            </motion.div>
          )}

          {/* Processing Time */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>
                Started: {new Date(queryState.start_time).toLocaleTimeString()}
              </span>
              <span>
                Elapsed: {Math.floor((Date.now() - queryState.start_time) / 1000)}s
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
