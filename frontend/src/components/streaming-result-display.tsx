/**
 * Streaming Result Display Component
 * Shows real-time streaming results as they arrive from WebSocket
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import {
  ChevronDown,
  ChevronUp,
  Database,
  BarChart3,
  TableIcon,
  Download,
  Maximize2,
  Eye
} from 'lucide-react';
import { QueryResultMessage } from '@/types/websocket';

interface StreamingResultDisplayProps {
  result: QueryResultMessage['result'];
  isComplete?: boolean;
  compact?: boolean;
}

export function StreamingResultDisplay({
  result,
  isComplete = false,
  compact = false
}: StreamingResultDisplayProps) {
  
  const [expandedSection, setExpandedSection] = useState<'response' | 'chart' | 'table' | 'sql' | null>('response');
  const [showFullTable, setShowFullTable] = useState(false);

  // Format execution time
  const formatExecutionTime = (ms: number): string => {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Determine if we have different types of content
  const hasResponse = !!result.response;
  const hasChart = !!result.chart_data;
  const hasTable = !!result.table_data;
  const hasSQL = !!result.sql_query;

  // Get table preview (first 5 rows)
  const getTablePreview = () => {
    if (!result.table_data) return null;
    
    const { headers, rows } = result.table_data;
    const previewRows = showFullTable ? rows : rows.slice(0, 5);
    
    return {
      headers,
      rows: previewRows,
      isPreview: !showFullTable && rows.length > 5,
      totalRows: rows.length
    };
  };

  const tablePreview = getTablePreview();

  // Compact version for inline display
  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full"
      >
        <Card className="border border-green-200 bg-green-50/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-sm font-medium text-green-900">
                  {isComplete ? 'Query Complete' : 'Results Streaming...'}
                </span>
              </div>
              
              {result.execution_time && (
                <Badge variant="secondary" className="text-xs">
                  {formatExecutionTime(result.execution_time)}
                </Badge>
              )}
            </div>

            {hasResponse && (
              <p className="text-sm text-gray-700 line-clamp-3">
                {result.response}
              </p>
            )}

            {(hasChart || hasTable) && (
              <div className="flex items-center gap-2 mt-2">
                {hasChart && (
                  <Badge variant="outline" className="text-xs">
                    <BarChart3 className="w-3 h-3 mr-1" />
                    Chart Available
                  </Badge>
                )}
                {hasTable && (
                  <Badge variant="outline" className="text-xs">
                    <TableIcon className="w-3 h-3 mr-1" />
                    {result.table_data?.rows.length} rows
                  </Badge>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // Full version for detailed display
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full space-y-4"
    >
      {/* Header Card */}
      <Card className="border-green-200 bg-gradient-to-r from-green-50/50 to-emerald-50/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg text-green-900 flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${isComplete ? 'bg-green-500' : 'bg-green-500 animate-pulse'}`} />
              Query Results
              {!isComplete && <span className="text-sm font-normal text-green-700">(Streaming...)</span>}
            </CardTitle>
            
            <div className="flex items-center gap-2">
              {result.execution_time && (
                <Badge variant="secondary">
                  {formatExecutionTime(result.execution_time)}
                </Badge>
              )}
              <Button variant="outline" size="sm">
                <Download className="w-4 h-4 mr-1" />
                Export
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Response Section */}
      {hasResponse && (
        <Card className="border-blue-200">
          <CardHeader 
            className="cursor-pointer hover:bg-blue-50/50 transition-colors"
            onClick={() => setExpandedSection(expandedSection === 'response' ? null : 'response')}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Eye className="w-4 h-4 text-blue-600" />
                Analysis & Insights
              </CardTitle>
              {expandedSection === 'response' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </CardHeader>
          
          <AnimatePresence>
            {expandedSection === 'response' && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <CardContent className="pt-0">
                  <div className="prose prose-sm max-w-none text-gray-700">
                    {result.response.split('\n').map((paragraph, index) => (
                      <p key={index} className="mb-2 last:mb-0">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </CardContent>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      )}

      {/* Chart Section */}
      {hasChart && (
        <Card className="border-purple-200">
          <CardHeader 
            className="cursor-pointer hover:bg-purple-50/50 transition-colors"
            onClick={() => setExpandedSection(expandedSection === 'chart' ? null : 'chart')}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-purple-600" />
                Visualization
                <Badge variant="outline" className="text-xs">
                  {result.chart_type || 'Chart'}
                </Badge>
              </CardTitle>
              {expandedSection === 'chart' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </CardHeader>
          
          <AnimatePresence>
            {expandedSection === 'chart' && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <CardContent className="pt-0">
                  <div className="bg-white rounded-lg border p-4 min-h-[300px] flex items-center justify-center">
                    <div className="text-center text-gray-500">
                      <BarChart3 className="w-12 h-12 mx-auto mb-2 text-purple-400" />
                      <p className="text-sm">Chart visualization would render here</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Data: {JSON.stringify(result.chart_data).substring(0, 100)}...
                      </p>
                    </div>
                  </div>
                </CardContent>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      )}

      {/* Table Section */}
      {hasTable && tablePreview && (
        <Card className="border-indigo-200">
          <CardHeader 
            className="cursor-pointer hover:bg-indigo-50/50 transition-colors"
            onClick={() => setExpandedSection(expandedSection === 'table' ? null : 'table')}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <TableIcon className="w-4 h-4 text-indigo-600" />
                Data Table
                <Badge variant="outline" className="text-xs">
                  {tablePreview.totalRows} rows × {tablePreview.headers.length} columns
                </Badge>
              </CardTitle>
              {expandedSection === 'table' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </CardHeader>
          
          <AnimatePresence>
            {expandedSection === 'table' && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <CardContent className="pt-0">
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-indigo-50/50">
                          {tablePreview.headers.map((header, index) => (
                            <TableHead key={index} className="font-semibold text-indigo-900">
                              {header}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {tablePreview.rows.map((row, rowIndex) => (
                          <TableRow key={rowIndex} className="hover:bg-gray-50">
                            {(row as unknown[]).map((cell, cellIndex) => (
                              <TableCell key={cellIndex} className="text-sm">
                                {String(cell)}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                    
                    {tablePreview.isPreview && (
                      <div className="p-3 bg-gray-50 border-t text-center">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowFullTable(!showFullTable)}
                        >
                          <Maximize2 className="w-4 h-4 mr-1" />
                          Show All {tablePreview.totalRows} Rows
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      )}

      {/* SQL Query Section */}
      {hasSQL && (
        <Card className="border-gray-200">
          <CardHeader 
            className="cursor-pointer hover:bg-gray-50/50 transition-colors"
            onClick={() => setExpandedSection(expandedSection === 'sql' ? null : 'sql')}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="w-4 h-4 text-gray-600" />
                Generated SQL Query
              </CardTitle>
              {expandedSection === 'sql' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </CardHeader>
          
          <AnimatePresence>
            {expandedSection === 'sql' && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <CardContent className="pt-0">
                  <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                    <pre className="text-sm text-gray-100 font-mono whitespace-pre-wrap">
                      {result.sql_query}
                    </pre>
                  </div>
                </CardContent>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      )}
    </motion.div>
  );
}
