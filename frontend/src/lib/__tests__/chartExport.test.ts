import { describe, it, expect, vi, beforeEach } from "vitest";
import { ChartExportService, useChartExport } from "../chartExport";
import { ExportOptions } from "@/types/chart";

// Mock html2canvas
const mockCanvas = {
    toDataURL: vi.fn(() => "data:image/png;base64,mockdata"),
    width: 800,
    height: 600,
};

vi.mock("html2canvas", () => ({
    default: vi.fn(() => Promise.resolve(mockCanvas)),
}));

// Mock jsPDF
const mockPDF = {
    addImage: vi.fn(),
    save: vi.fn(),
    setFontSize: vi.fn(),
    setTextColor: vi.fn(),
    text: vi.fn(),
};

vi.mock("jspdf", () => ({
    default: vi.fn(() => mockPDF),
}));

// Mock DOM methods
Object.defineProperty(document, "createElement", {
    value: vi.fn((tagName: string) => {
        if (tagName === "a") {
            return {
                download: "",
                href: "",
                click: vi.fn(),
                style: {},
            };
        }
        return {};
    }),
});

Object.defineProperty(document.body, "appendChild", {
    value: vi.fn(),
});

Object.defineProperty(document.body, "removeChild", {
    value: vi.fn(),
});

Object.defineProperty(URL, "createObjectURL", {
    value: vi.fn(() => "blob:mock-url"),
});

Object.defineProperty(URL, "revokeObjectURL", {
    value: vi.fn(),
});

describe("ChartExportService", () => {
    let mockElement: HTMLElement;
    let mockSVGElement: SVGElement;

    beforeEach(() => {
        vi.clearAllMocks();

        // Create mock HTML element
        mockElement = document.createElement("div");

        // Create mock SVG element
        mockSVGElement = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        mockSVGElement.setAttribute("width", "800");
        mockSVGElement.setAttribute("height", "600");

        // Mock querySelector to return SVG element
        mockElement.querySelector = vi.fn(() => mockSVGElement);

        // Mock SVG cloneNode
        mockSVGElement.cloneNode = vi.fn(() => {
            const cloned = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            cloned.setAttribute = vi.fn();
            cloned.insertBefore = vi.fn();
            return cloned;
        });
    });

    describe("exportAsPNG", () => {
        it("exports chart as PNG successfully", async () => {
            const options: ExportOptions = {
                format: "png",
                filename: "test-chart",
                quality: 2,
                width: 800,
                height: 600,
                includeBranding: false,
            };

            await expect(
                ChartExportService.exportAsPNG(mockElement, options)
            ).resolves.not.toThrow();

            expect(document.createElement).toHaveBeenCalledWith("a");
        });

        it("includes branding when requested", async () => {
            const options: ExportOptions = {
                format: "png",
                filename: "test-chart",
                includeBranding: true,
            };

            await expect(
                ChartExportService.exportAsPNG(mockElement, options)
            ).resolves.not.toThrow();
        });

        it("handles export errors gracefully", async () => {
            const html2canvas = await import("html2canvas");
            vi.mocked(html2canvas.default).mockRejectedValueOnce(new Error("Canvas error"));

            const options: ExportOptions = {
                format: "png",
                filename: "test-chart",
            };

            await expect(
                ChartExportService.exportAsPNG(mockElement, options)
            ).rejects.toThrow("Failed to export chart as PNG");
        });
    });

    describe("exportAsSVG", () => {
        it("exports chart as SVG successfully", async () => {
            const options: ExportOptions = {
                format: "svg",
                filename: "test-chart",
                width: 800,
                height: 600,
                includeBranding: false,
            };

            // Mock XMLSerializer
            global.XMLSerializer = vi.fn(() => ({
                serializeToString: vi.fn(() => "<svg></svg>"),
            })) as any;

            // Mock Blob
            global.Blob = vi.fn(() => ({})) as any;

            await expect(
                ChartExportService.exportAsSVG(mockElement, options)
            ).resolves.not.toThrow();
        });

        it("includes branding in SVG when requested", async () => {
            const options: ExportOptions = {
                format: "svg",
                filename: "test-chart",
                includeBranding: true,
            };

            global.XMLSerializer = vi.fn(() => ({
                serializeToString: vi.fn(() => "<svg></svg>"),
            })) as any;

            global.Blob = vi.fn(() => ({})) as any;

            await expect(
                ChartExportService.exportAsSVG(mockElement, options)
            ).resolves.not.toThrow();
        });

        it("throws error when no SVG element found", async () => {
            mockElement.querySelector = vi.fn(() => null);

            const options: ExportOptions = {
                format: "svg",
                filename: "test-chart",
            };

            await expect(
                ChartExportService.exportAsSVG(mockElement, options)
            ).rejects.toThrow("Failed to export chart as SVG");
        });
    });

    describe("exportAsPDF", () => {
        it("exports chart as PDF successfully", async () => {
            const options: ExportOptions = {
                format: "pdf",
                filename: "test-chart",
                quality: 1,
                includeBranding: false,
            };

            await expect(
                ChartExportService.exportAsPDF(mockElement, options)
            ).resolves.not.toThrow();

            expect(mockPDF.addImage).toHaveBeenCalled();
            expect(mockPDF.save).toHaveBeenCalledWith("test-chart.pdf");
        });

        it("includes branding in PDF when requested", async () => {
            const options: ExportOptions = {
                format: "pdf",
                filename: "test-chart",
                includeBranding: true,
            };

            await expect(
                ChartExportService.exportAsPDF(mockElement, options)
            ).resolves.not.toThrow();

            expect(mockPDF.setFontSize).toHaveBeenCalled();
            expect(mockPDF.text).toHaveBeenCalled();
        });

        it("handles PDF export errors gracefully", async () => {
            const html2canvas = await import("html2canvas");
            vi.mocked(html2canvas.default).mockRejectedValueOnce(new Error("Canvas error"));

            const options: ExportOptions = {
                format: "pdf",
                filename: "test-chart",
            };

            await expect(
                ChartExportService.exportAsPDF(mockElement, options)
            ).rejects.toThrow("Failed to export chart as PDF");
        });
    });
});

describe("useChartExport", () => {
    let mockElement: HTMLElement;

    beforeEach(() => {
        mockElement = document.createElement("div");

        // Mock SVG element for SVG export tests
        const mockSVGElement = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        mockSVGElement.setAttribute("width", "800");
        mockSVGElement.setAttribute("height", "600");
        mockSVGElement.cloneNode = vi.fn(() => {
            const cloned = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            cloned.setAttribute = vi.fn();
            cloned.insertBefore = vi.fn();
            return cloned;
        });

        mockElement.querySelector = vi.fn(() => mockSVGElement);
    });

    it("exports PNG format correctly", async () => {
        const { exportChart } = useChartExport();

        const options: ExportOptions = {
            format: "png",
            filename: "test-chart",
        };

        await expect(exportChart(mockElement, options)).resolves.not.toThrow();
    });

    it("exports SVG format correctly", async () => {
        const { exportChart } = useChartExport();

        global.XMLSerializer = vi.fn(() => ({
            serializeToString: vi.fn(() => "<svg></svg>"),
        })) as any;

        global.Blob = vi.fn(() => ({})) as any;

        const options: ExportOptions = {
            format: "svg",
            filename: "test-chart",
        };

        await expect(exportChart(mockElement, options)).resolves.not.toThrow();
    });

    it("exports PDF format correctly", async () => {
        const { exportChart } = useChartExport();

        const options: ExportOptions = {
            format: "pdf",
            filename: "test-chart",
        };

        await expect(exportChart(mockElement, options)).resolves.not.toThrow();
    });

    it("throws error for unsupported format", async () => {
        const { exportChart } = useChartExport();

        const options: ExportOptions = {
            format: "unsupported" as any,
            filename: "test-chart",
        };

        await expect(exportChart(mockElement, options)).rejects.toThrow(
            "Unsupported export format: unsupported"
        );
    });

    it("throws error when element is null", async () => {
        const { exportChart } = useChartExport();

        const options: ExportOptions = {
            format: "png",
            filename: "test-chart",
        };

        await expect(exportChart(null, options)).rejects.toThrow(
            "Chart element not found"
        );
    });

    it("handles export service errors", async () => {
        const { exportChart } = useChartExport();

        // Mock html2canvas to throw error
        const html2canvas = await import("html2canvas");
        vi.mocked(html2canvas.default).mockRejectedValueOnce(new Error("Export failed"));

        const options: ExportOptions = {
            format: "png",
            filename: "test-chart",
        };

        await expect(exportChart(mockElement, options)).rejects.toThrow();
    });
});