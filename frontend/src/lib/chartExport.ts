// Dynamic imports for browser-only libraries
import { ExportOptions } from "@/types/chart";
import type { jsPDF as JsPDFType } from "jspdf";

export class ChartExportService {
    /**
     * Export chart as PNG using html2canvas
     */
    static async exportAsPNG(
        element: HTMLElement,
        options: ExportOptions
    ): Promise<void> {
        try {
            const html2canvas = (await import("html2canvas")).default;

            const canvas = await html2canvas(element, {
                backgroundColor: "#ffffff",
                scale: options.quality || 2,
                width: options.width,
                height: options.height,
                useCORS: true,
                allowTaint: true,
            });

            // Create download link
            const link = document.createElement("a");
            link.download = `${options.filename || "chart"}.png`;
            link.href = canvas.toDataURL("image/png");

            // Add branding if requested
            if (options.includeBranding) {
                const brandedCanvas = await this.addBranding(canvas);
                link.href = brandedCanvas.toDataURL("image/png");
            }

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error("PNG export failed:", error);
            throw new Error("Failed to export chart as PNG");
        }
    }

    /**
     * Export chart as SVG
     */
    static async exportAsSVG(
        element: HTMLElement,
        options: ExportOptions
    ): Promise<void> {
        try {
            // Find SVG element within the chart container
            const svgElement = element.querySelector("svg");
            if (!svgElement) {
                throw new Error("No SVG element found in chart");
            }

            // Clone and prepare SVG for export
            const clonedSvg = svgElement.cloneNode(true) as SVGElement;
            clonedSvg.setAttribute("width", (options.width || 800).toString());
            clonedSvg.setAttribute("height", (options.height || 600).toString());

            // Add CSS styles inline
            this.inlineSVGStyles(clonedSvg);

            // Add branding if requested
            if (options.includeBranding) {
                this.addSVGBranding(clonedSvg);
            }

            // Create blob and download
            const serializer = new XMLSerializer();
            const svgString = serializer.serializeToString(clonedSvg);
            const blob = new Blob([svgString], { type: "image/svg+xml" });

            const link = document.createElement("a");
            link.download = `${options.filename || "chart"}.svg`;
            link.href = URL.createObjectURL(blob);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
        } catch (error) {
            console.error("SVG export failed:", error);
            throw new Error("Failed to export chart as SVG");
        }
    }

    /**
     * Export chart as PDF using jsPDF
     */
    static async exportAsPDF(
        element: HTMLElement,
        options: ExportOptions
    ): Promise<void> {
        try {
            // Dynamic import of html2canvas for browser
            const html2canvas = (await import("html2canvas")).default;

            const canvas = await html2canvas(element, {
                backgroundColor: "#ffffff",
                scale: options.quality || 2,
                width: options.width,
                height: options.height,
                useCORS: true,
                allowTaint: true,
            });

            const imgData = canvas.toDataURL("image/png");
            // Dynamic import of jsPDF for browser
            const { jsPDF } = await import("jspdf");

            const pdf = new jsPDF({
                orientation: canvas.width > canvas.height ? "landscape" : "portrait",
                unit: "px",
                format: [canvas.width, canvas.height],
            });

            // Add branding header if requested
            if (options.includeBranding) {
                this.addPDFBranding(pdf, canvas.width);
            }

            pdf.addImage(
                imgData,
                "PNG",
                0,
                options.includeBranding ? 40 : 0,
                canvas.width,
                canvas.height
            );

            pdf.save(`${options.filename || "chart"}.pdf`);
        } catch (error) {
            console.error("PDF export failed:", error);
            throw new Error("Failed to export chart as PDF");
        }
    }

    /**
     * Add branding to canvas
     */
    private static async addBranding(canvas: HTMLCanvasElement): Promise<HTMLCanvasElement> {
        const ctx = canvas.getContext("2d");
        if (!ctx) return canvas;

        // Add company branding
        ctx.fillStyle = "#1f2937";
        ctx.font = "14px Arial, sans-serif";
        ctx.fillText("AI CFO BI Agent", 10, canvas.height - 10);

        // Add timestamp
        ctx.fillStyle = "#6b7280";
        ctx.font = "12px Arial, sans-serif";
        const timestamp = new Date().toLocaleString();
        ctx.fillText(`Generated: ${timestamp}`, canvas.width - 200, canvas.height - 10);

        return canvas;
    }

    /**
     * Add branding to SVG
     */
    private static addSVGBranding(svg: SVGElement): void {
        const height = parseInt(svg.getAttribute("height") || "600");
        const width = parseInt(svg.getAttribute("width") || "800");

        // Add branding text
        const brandingGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");

        const brandText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        brandText.setAttribute("x", "10");
        brandText.setAttribute("y", (height - 10).toString());
        brandText.setAttribute("font-family", "Arial, sans-serif");
        brandText.setAttribute("font-size", "14");
        brandText.setAttribute("fill", "#1f2937");
        brandText.textContent = "AI CFO BI Agent";

        const timestampText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        timestampText.setAttribute("x", (width - 200).toString());
        timestampText.setAttribute("y", (height - 10).toString());
        timestampText.setAttribute("font-family", "Arial, sans-serif");
        timestampText.setAttribute("font-size", "12");
        timestampText.setAttribute("fill", "#6b7280");
        timestampText.textContent = `Generated: ${new Date().toLocaleString()}`;

        brandingGroup.appendChild(brandText);
        brandingGroup.appendChild(timestampText);
        svg.appendChild(brandingGroup);
    }

    /**
     * Add branding to PDF
     */
    private static addPDFBranding(pdf: JsPDFType, width: number): void {

        pdf.setFontSize(16);
        pdf.setTextColor(31, 41, 55); // #1f2937
        pdf.text("AI CFO BI Agent", 10, 25);

        pdf.setFontSize(12);
        pdf.setTextColor(107, 114, 128); // #6b7280
        const timestamp = new Date().toLocaleString();
        pdf.text(`Generated: ${timestamp}`, width - 150, 25);
    }

    /**
     * Inline CSS styles for SVG export
     */
    private static inlineSVGStyles(svg: SVGElement): void {
        // Add common chart styles inline
        const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
        style.textContent = `
      .recharts-cartesian-grid-horizontal line,
      .recharts-cartesian-grid-vertical line {
        stroke: #e5e7eb;
        stroke-dasharray: 3 3;
      }
      .recharts-text {
        font-family: Arial, sans-serif;
        font-size: 12px;
        fill: #6b7280;
      }
      .recharts-legend-item-text {
        font-family: Arial, sans-serif;
        font-size: 12px;
        fill: #374151;
      }
    `;
        svg.insertBefore(style, svg.firstChild);
    }
}

/**
 * Hook for chart export functionality
 */
export const useChartExport = () => {
    const exportChart = async (
        element: HTMLElement | null,
        options: ExportOptions
    ): Promise<void> => {
        if (!element) {
            throw new Error("Chart element not found");
        }

        switch (options.format) {
            case "png":
                await ChartExportService.exportAsPNG(element, options);
                break;
            case "svg":
                await ChartExportService.exportAsSVG(element, options);
                break;
            case "pdf":
                await ChartExportService.exportAsPDF(element, options);
                break;
            default:
                throw new Error(`Unsupported export format: ${options.format}`);
        }
    };

    return { exportChart };
};