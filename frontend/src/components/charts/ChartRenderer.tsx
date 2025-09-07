"use client";

import React, { useState, useRef, useCallback, useMemo } from "react";
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    AreaChart,
    Area,
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Download, ZoomIn, ZoomOut } from "lucide-react";
import {
    ChartType,
    ChartRendererProps,
    ExportOptions,
    CFO_COLOR_SCHEMES,
} from "@/types/chart";
import { CardSize } from "@/types/dashboard";

// Chart size mappings for Bento grid
const CHART_SIZE_DIMENSIONS = {
    [CardSize.SMALL]: { width: 300, height: 200 },
    [CardSize.MEDIUM_H]: { width: 600, height: 300 },
    [CardSize.MEDIUM_V]: { width: 300, height: 400 },
    [CardSize.LARGE]: { width: 600, height: 400 },
    [CardSize.EXTRA_LARGE]: { width: 900, height: 500 },
} as const;

interface ChartRendererInternalProps extends ChartRendererProps {
    cardSize?: CardSize;
}

const ChartRenderer: React.FC<ChartRendererInternalProps> = ({
    config,
    loading = false,
    error = null,
    className = "",
    cardSize = CardSize.LARGE,
    onExport,
    // onConfigChange is not used in this component
}) => {
    const chartRef = useRef<HTMLDivElement>(null);
    const [zoomLevel, setZoomLevel] = useState(1);
    const [isExporting, setIsExporting] = useState(false);

    // Get dimensions based on card size or config
    const dimensions = useMemo(() => {
        const sizeConfig = CHART_SIZE_DIMENSIONS[cardSize];
        return {
            width: config.dimensions?.width || sizeConfig.width,
            height: config.dimensions?.height || sizeConfig.height,
            margin: config.dimensions?.margin || { top: 20, right: 30, left: 20, bottom: 5 },
        };
    }, [config.dimensions, cardSize]);

    // Get color scheme
    const colorScheme = useMemo(() => {
        const theme = config.styling?.theme || "corporate";
        return config.styling?.colorScheme || CFO_COLOR_SCHEMES[theme as keyof typeof CFO_COLOR_SCHEMES] || CFO_COLOR_SCHEMES.corporate;
    }, [config.styling]);

    // Format financial values
    const formatFinancialValue = useCallback((value: number) => {
        if (Math.abs(value) >= 1000000) {
            return `$${(value / 1000000).toFixed(1)}M`;
        } else if (Math.abs(value) >= 1000) {
            return `$${(value / 1000).toFixed(1)}K`;
        }
        return `$${value.toLocaleString()}`;
    }, []);

    // Custom tooltip for financial data
    interface TooltipProps {
        active?: boolean;
        payload?: Array<{
            name: string;
            value: number;
            color: string;
        }>;
        label?: string;
    }

    const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
                    <p className="font-medium">{label}</p>
                    {payload.map((entry, index: number) => (
                        <p key={index} style={{ color: entry.color }}>
                            {entry.name}: {formatFinancialValue(entry.value)}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };    // Export functionality
    const handleExport = useCallback(async (format: ExportOptions["format"]) => {
        if (!chartRef.current || !onExport) return;

        setIsExporting(true);
        try {
            const exportOptions: ExportOptions = {
                format,
                filename: `chart-${crypto.randomUUID().slice(0, 8)}`,
                quality: 1,
                width: dimensions.width,
                height: dimensions.height,
                includeBranding: true,
            };

            await onExport(exportOptions);
        } catch (error) {
            console.error("Export failed:", error);
        } finally {
            setIsExporting(false);
        }
    }, [onExport, dimensions]);

    // Zoom handlers
    const handleZoomIn = () => setZoomLevel(prev => Math.min(prev * 1.2, 3));
    const handleZoomOut = () => setZoomLevel(prev => Math.max(prev / 1.2, 0.5));

    // Render different chart types
    const renderChart = () => {
        const { data, xAxisKey, yAxisKeys } = config.data;
        const chartProps = {
            data,
            margin: dimensions.margin,
        };

        switch (config.type) {
            case ChartType.LINE:
                return (
                    <LineChart {...chartProps}>
                        <CartesianGrid strokeDasharray="3 3" stroke={config.styling?.gridColor || "#e5e7eb"} />
                        <XAxis
                            dataKey={xAxisKey}
                            stroke={config.styling?.axisColor || "#6b7280"}
                            fontSize={config.styling?.fontSize || 12}
                        />
                        <YAxis
                            stroke={config.styling?.axisColor || "#6b7280"}
                            fontSize={config.styling?.fontSize || 12}
                            tickFormatter={formatFinancialValue}
                        />
                        {config.interactivity?.enableTooltip !== false && <Tooltip content={<CustomTooltip />} />}
                        {config.interactivity?.enableLegend !== false && <Legend />}
                        {yAxisKeys.map((key, index) => (
                            <Line
                                key={key}
                                type="monotone"
                                dataKey={key}
                                stroke={colorScheme[index % colorScheme.length]}
                                strokeWidth={2}
                                dot={{ fill: colorScheme[index % colorScheme.length], strokeWidth: 2, r: 4 }}
                                activeDot={{ r: 6 }}
                                animationDuration={config.interactivity?.enableAnimation !== false ? 1000 : 0}
                            />
                        ))}
                    </LineChart>
                );

            case ChartType.BAR:
                return (
                    <BarChart {...chartProps}>
                        <CartesianGrid strokeDasharray="3 3" stroke={config.styling?.gridColor || "#e5e7eb"} />
                        <XAxis
                            dataKey={xAxisKey}
                            stroke={config.styling?.axisColor || "#6b7280"}
                            fontSize={config.styling?.fontSize || 12}
                        />
                        <YAxis
                            stroke={config.styling?.axisColor || "#6b7280"}
                            fontSize={config.styling?.fontSize || 12}
                            tickFormatter={formatFinancialValue}
                        />
                        {config.interactivity?.enableTooltip !== false && <Tooltip content={<CustomTooltip />} />}
                        {config.interactivity?.enableLegend !== false && <Legend />}
                        {yAxisKeys.map((key, index) => (
                            <Bar
                                key={key}
                                dataKey={key}
                                fill={colorScheme[index % colorScheme.length]}
                                animationDuration={config.interactivity?.enableAnimation !== false ? 1000 : 0}
                            />
                        ))}
                    </BarChart>
                );

            case ChartType.PIE:
                return (
                    <PieChart {...chartProps}>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                            outerRadius={Math.min(dimensions.width, dimensions.height) * 0.3}
                            fill="#8884d8"
                            dataKey={yAxisKeys[0]}
                            animationDuration={config.interactivity?.enableAnimation !== false ? 1000 : 0}
                        >
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={colorScheme[index % colorScheme.length]} />
                            ))}
                        </Pie>
                        {config.interactivity?.enableTooltip !== false && <Tooltip content={<CustomTooltip />} />}
                        {config.interactivity?.enableLegend !== false && <Legend />}
                    </PieChart>
                );

            case ChartType.AREA:
                return (
                    <AreaChart {...chartProps}>
                        <CartesianGrid strokeDasharray="3 3" stroke={config.styling?.gridColor || "#e5e7eb"} />
                        <XAxis
                            dataKey={xAxisKey}
                            stroke={config.styling?.axisColor || "#6b7280"}
                            fontSize={config.styling?.fontSize || 12}
                        />
                        <YAxis
                            stroke={config.styling?.axisColor || "#6b7280"}
                            fontSize={config.styling?.fontSize || 12}
                            tickFormatter={formatFinancialValue}
                        />
                        {config.interactivity?.enableTooltip !== false && <Tooltip content={<CustomTooltip />} />}
                        {config.interactivity?.enableLegend !== false && <Legend />}
                        {yAxisKeys.map((key, index) => (
                            <Area
                                key={key}
                                type="monotone"
                                dataKey={key}
                                stackId="1"
                                stroke={colorScheme[index % colorScheme.length]}
                                fill={colorScheme[index % colorScheme.length]}
                                fillOpacity={0.6}
                                animationDuration={config.interactivity?.enableAnimation !== false ? 1000 : 0}
                            />
                        ))}
                    </AreaChart>
                );

            case ChartType.SCATTER:
                return (
                    <ScatterChart {...chartProps}>
                        <CartesianGrid strokeDasharray="3 3" stroke={config.styling?.gridColor || "#e5e7eb"} />
                        <XAxis
                            dataKey={xAxisKey}
                            stroke={config.styling?.axisColor || "#6b7280"}
                            fontSize={config.styling?.fontSize || 12}
                            type="number"
                        />
                        <YAxis
                            stroke={config.styling?.axisColor || "#6b7280"}
                            fontSize={config.styling?.fontSize || 12}
                            tickFormatter={formatFinancialValue}
                            type="number"
                        />
                        {config.interactivity?.enableTooltip !== false && <Tooltip content={<CustomTooltip />} />}
                        {config.interactivity?.enableLegend !== false && <Legend />}
                        {yAxisKeys.map((key, index) => (
                            <Scatter
                                key={key}
                                dataKey={key}
                                fill={colorScheme[index % colorScheme.length]}
                                animationDuration={config.interactivity?.enableAnimation !== false ? 1000 : 0}
                            />
                        ))}
                    </ScatterChart>
                );

            default:
                return (
                    <div className="flex items-center justify-center h-full text-gray-500">
                        Unsupported chart type: {config.type}
                    </div>
                );
        }
    };

    if (loading) {
        return (
            <Card className={className}>
                <CardContent className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span className="ml-2 text-gray-600">Loading chart...</span>
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card className={className}>
                <CardContent className="flex items-center justify-center h-64">
                    <div className="text-center">
                        <div className="text-red-500 mb-2">⚠️ Chart Error</div>
                        <p className="text-gray-600 text-sm">{error}</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className={className}>
            {(config.title || config.showExportButton) && (
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <div>
                        {config.title && <CardTitle className="text-lg font-semibold">{config.title}</CardTitle>}
                        {config.subtitle && <p className="text-sm text-gray-600">{config.subtitle}</p>}
                    </div>

                    {config.showExportButton && (
                        <div className="flex items-center space-x-2">
                            {config.interactivity?.enableZoom && (
                                <div className="flex items-center space-x-1">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleZoomOut}
                                        disabled={zoomLevel <= 0.5}
                                    >
                                        <ZoomOut className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleZoomIn}
                                        disabled={zoomLevel >= 3}
                                    >
                                        <ZoomIn className="h-4 w-4" />
                                    </Button>
                                </div>
                            )}

                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="outline" size="sm" disabled={isExporting}>
                                        <Download className="h-4 w-4 mr-1" />
                                        Export
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent>
                                    <DropdownMenuItem onClick={() => handleExport("png")}>
                                        Export as PNG
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => handleExport("svg")}>
                                        Export as SVG
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => handleExport("pdf")}>
                                        Export as PDF
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    )}
                </CardHeader>
            )}

            <CardContent>
                <div
                    ref={chartRef}
                    style={{
                        transform: `scale(${zoomLevel})`,
                        transformOrigin: "top left",
                        transition: "transform 0.2s ease-in-out"
                    }}
                >
                    <ResponsiveContainer width="100%" height={dimensions.height}>
                        {renderChart()}
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
};

export default ChartRenderer;