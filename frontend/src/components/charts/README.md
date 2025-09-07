# ChartRenderer Component

A comprehensive, reusable chart rendering component built with Recharts for the AI CFO BI Agent frontend. This component provides intelligent chart type selection, CFO-specific styling, and advanced export capabilities.

## Features

### ✅ Chart Types Supported

- **Line Charts**: Time series data, trends, and continuous metrics
- **Bar Charts**: Categorical comparisons, department budgets
- **Pie Charts**: Market share, proportional data distribution
- **Area Charts**: Cumulative data, stacked metrics
- **Scatter Plots**: Correlation analysis, performance metrics
- **Heatmaps**: (Future enhancement)

### ✅ CFO-Specific Features

- **Financial Formatting**: Automatic currency formatting ($1.2M, $500K)
- **Corporate Color Schemes**: Professional color palettes
- **Business Metrics**: Revenue, expenses, profit margins, ROI
- **Time Period Intelligence**: Quarterly, monthly, yearly aggregations

### ✅ Responsive Design

- **Bento Grid Integration**: Adapts to card sizes (1x1, 2x1, 1x2, 2x2, 3x2)
- **Mobile Responsive**: Works across different screen sizes
- **Dynamic Sizing**: Automatic chart sizing based on container

### ✅ Interactive Features

- **Zoom & Pan**: For detailed data exploration
- **Custom Tooltips**: Financial data formatting in tooltips
- **Legend Control**: Show/hide data series
- **Grid Toggle**: Customizable grid display
- **Animations**: Smooth transitions and loading states

### ✅ Export Capabilities

- **PNG Export**: High-resolution image export
- **SVG Export**: Vector graphics for presentations
- **PDF Export**: Professional reports with branding
- **Branding**: Automatic company branding on exports

### ✅ Error Handling

- **Loading States**: Skeleton loading with progress indicators
- **Error Boundaries**: Graceful error handling and recovery
- **Fallback Charts**: Default chart types when data is invalid

## Usage

### Basic Usage

```tsx
import ChartRenderer from "@/components/charts/ChartRenderer";
import { ChartType, ChartConfig } from "@/types/chart";
import { CardSize } from "@/types/dashboard";

const chartConfig: ChartConfig = {
  type: ChartType.LINE,
  title: "Revenue Trends",
  subtitle: "Monthly performance overview",
  data: {
    data: [
      { month: "Jan", revenue: 100000, expenses: 80000 },
      { month: "Feb", revenue: 120000, expenses: 85000 },
      { month: "Mar", revenue: 110000, expenses: 90000 },
    ],
    xAxisKey: "month",
    yAxisKeys: ["revenue", "expenses"],
  },
  responsive: true,
  showExportButton: true,
};

function MyComponent() {
  const handleExport = async (options: ExportOptions) => {
    // Handle export logic
  };

  return (
    <ChartRenderer
      config={chartConfig}
      cardSize={CardSize.LARGE}
      onExport={handleExport}
    />
  );
}
```

### Advanced Configuration

```tsx
import { useChartConfig } from "@/lib/chartUtils";

function AdvancedChart() {
  const data = {
    data: financialData,
    xAxisKey: "period",
    yAxisKeys: ["revenue", "profit"],
  };

  const { createConfig, suggestChartType } = useChartConfig(
    data,
    CardSize.LARGE
  );

  const config = createConfig({
    type: suggestChartType(), // Intelligent type selection
    title: "Financial Performance",
    interactivity: {
      enableZoom: true,
      enablePan: true,
      enableTooltip: true,
    },
    styling: {
      theme: "corporate",
      colorScheme: ["#1f2937", "#3b82f6", "#10b981"],
    },
  });

  return <ChartRenderer config={config} />;
}
```

### Bento Grid Integration

```tsx
import ChartCard from "@/components/bento-grid/ChartCard";

const bentoCard: BentoGridCard = {
  id: "revenue-chart",
  cardType: CardType.CHART,
  size: CardSize.LARGE,
  position: { row: 0, col: 0 },
  content: {
    title: "Revenue Analysis",
    chartConfig: chartConfig,
  },
};

function Dashboard() {
  return <ChartCard card={bentoCard} />;
}
```

## Configuration Options

### ChartConfig Interface

```typescript
interface ChartConfig {
  type: ChartType; // Chart type (line, bar, pie, etc.)
  title?: string; // Chart title
  subtitle?: string; // Chart subtitle
  data: ChartData; // Chart data configuration
  dimensions?: ChartDimensions; // Width, height, margins
  interactivity?: ChartInteractivity; // Interactive features
  styling?: ChartStyling; // Colors, fonts, themes
  responsive?: boolean; // Responsive behavior
  showExportButton?: boolean; // Export functionality
}
```

### Chart Data Structure

```typescript
interface ChartData {
  data: ChartDataPoint[]; // Array of data points
  xAxisKey: string; // Key for X-axis values
  yAxisKeys: string[]; // Keys for Y-axis values
  categories?: string[]; // Category labels (for pie charts)
}

interface ChartDataPoint {
  [key: string]: string | number | Date;
}
```

### Styling Options

```typescript
interface ChartStyling {
  colorScheme?: string[]; // Custom color palette
  theme?: "light" | "dark" | "corporate"; // Predefined themes
  fontSize?: number; // Font size for labels
  fontFamily?: string; // Font family
  backgroundColor?: string; // Chart background
  gridColor?: string; // Grid line color
  axisColor?: string; // Axis color
}
```

## Intelligent Chart Type Selection

The component includes intelligent chart type selection based on data characteristics:

```typescript
import { ChartTypeSelector } from "@/lib/chartUtils";

// Automatic type selection
const suggestedType = ChartTypeSelector.suggestChartType(
  data,
  xAxisKey,
  yAxisKeys
);

// Selection logic:
// - Time series data → Line Chart
// - Proportional data (≤8 items) → Pie Chart
// - Correlation data (≥2 numeric variables) → Scatter Plot
// - Distribution data → Area Chart
// - Categorical data → Bar Chart (default)
```

## Export Functionality

### Export Options

```typescript
interface ExportOptions {
  format: "png" | "svg" | "pdf";
  filename?: string;
  quality?: number; // For PNG (1-3)
  width?: number; // Custom dimensions
  height?: number;
  includeBranding?: boolean; // Company branding
}
```

### Export Usage

```typescript
import { useChartExport } from "@/lib/chartExport";

function ExportExample() {
  const { exportChart } = useChartExport();

  const handleExport = async () => {
    const chartElement = document.querySelector("[data-chart-container]");

    await exportChart(chartElement, {
      format: "png",
      filename: "revenue-analysis",
      quality: 2,
      includeBranding: true,
    });
  };

  return <button onClick={handleExport}>Export Chart</button>;
}
```

## Performance Considerations

### Large Datasets

- Automatic data sampling for datasets >1000 points
- Virtualization for improved rendering performance
- Lazy loading of chart components

### Memory Management

- Memoized calculations for expensive operations
- Cleanup of event listeners and timers
- Efficient re-rendering with React.memo

### Responsive Performance

- CSS-based responsive design
- Debounced resize handlers
- Optimized animation performance

## Testing

The component includes comprehensive test coverage:

```bash
# Run all chart tests
npm run test src/components/charts/

# Run specific test suites
npm run test ChartRenderer.test.tsx
npm run test chartUtils.test.ts
npm run test chartExport.test.ts
```

### Test Coverage

- ✅ Chart rendering for all types
- ✅ Responsive behavior
- ✅ Interactive features (zoom, pan, tooltips)
- ✅ Export functionality
- ✅ Error handling and loading states
- ✅ Accessibility compliance
- ✅ Performance with large datasets

## Accessibility

### ARIA Support

- Proper ARIA labels for chart elements
- Keyboard navigation for interactive controls
- Screen reader compatible descriptions

### Color Accessibility

- High contrast color schemes
- Colorblind-friendly palettes
- Alternative text for visual elements

## Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Dependencies

- **recharts**: Chart rendering library
- **html2canvas**: PNG export functionality
- **jspdf**: PDF export functionality
- **framer-motion**: Animations and transitions
- **@dnd-kit/core**: Drag and drop support

## Future Enhancements

### Planned Features

- [ ] Heatmap chart type implementation
- [ ] Real-time data streaming
- [ ] Advanced drill-down capabilities
- [ ] Custom chart annotations
- [ ] Multi-axis chart support
- [ ] 3D chart rendering options

### Performance Improvements

- [ ] WebGL rendering for large datasets
- [ ] Web Workers for data processing
- [ ] Progressive loading for complex charts

## Contributing

When contributing to the ChartRenderer component:

1. **Follow TypeScript best practices**
2. **Add comprehensive tests for new features**
3. **Update documentation for API changes**
4. **Ensure accessibility compliance**
5. **Test across different screen sizes**
6. **Validate export functionality**

## Examples

See `ChartRendererExample.tsx` for a comprehensive demonstration of all features and capabilities.
