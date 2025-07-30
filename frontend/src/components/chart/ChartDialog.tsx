import React, { useEffect, useState, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useTranslations } from "next-intl";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { AlertCircle, ExternalLink, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import embed from "vega-embed";
import { useTheme } from "@/contexts/ThemeContext";

interface ChartDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  chartData: any;
  chartContainerRef?: React.RefObject<HTMLDivElement>;
}

export const ChartDialog = ({
  isOpen,
  onOpenChange,
  chartData,
}: ChartDialogProps) => {
  const t = useTranslations("chatPage.analyticsPal.chartsArtifact");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [vegaSpec, setVegaSpec] = useState<string | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const vegaViewRef = useRef<any>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const prevZoomLevel = useRef(1);
  const { theme } = useTheme();
  const [currentTheme, setCurrentTheme] = useState<"dark" | "light">(
    theme === "dark" ? "dark" : "light"
  );

  // Update current theme when theme changes
  useEffect(() => {
    const isDarkMode = document.documentElement.classList.contains("dark");
    setCurrentTheme(isDarkMode ? "dark" : "light");
  }, [theme]);

  // Process chart data when dialog opens
  useEffect(() => {
    if (!isOpen || !chartData) return;

    setIsLoading(true);
    setError(null);
    setZoomLevel(1); // Reset zoom level when dialog opens
    prevZoomLevel.current = 1; // Reset previous zoom level reference

    try {
      // Create a deep copy of the schema
      const schema = JSON.parse(JSON.stringify(chartData.chart_schema || {}));

      // IMPORTANT: Check if schema already has aggregated data
      const hasPreAggregatedData =
        schema.data &&
        schema.data.values &&
        Array.isArray(schema.data.values) &&
        schema.data.values.length > 0;

      // If schema already has data values, use those instead of chart_data
      if (hasPreAggregatedData) {
        // Process any string numbers in the pre-aggregated data
        schema.data.values = schema.data.values.map((item: any) => {
          const newItem: Record<string, any> = {};

          // Convert string numeric values to actual numbers
          Object.entries(item).forEach(([key, value]) => {
            if (typeof value === "string" && !isNaN(Number(value))) {
              newItem[key] = Number(value);
            } else {
              newItem[key] = value;
            }
          });

          return newItem;
        });
      } else {
        // If no pre-aggregated data, use chart_data (this is the original behavior)

        // Process data to ensure numeric values are numbers, not strings
        const processedData = (chartData.chart_data || []).map((item: any) => {
          const newItem: Record<string, any> = {};

          // Convert string numeric values to actual numbers
          Object.entries(item).forEach(([key, value]) => {
            if (typeof value === "string" && !isNaN(Number(value))) {
              newItem[key] = Number(value);
            } else {
              newItem[key] = value;
            }
          });

          return newItem;
        });

        // Set the data values with properly formatted data
        schema.data = {
          values: processedData,
        };
      }

      // Ensure proper width and height
      schema.width = "container";
      schema.height = 500;
      schema.autosize = {
        type: "fit",
        contains: "padding",
      };

      // Apply theme based on the current theme
      const isDarkMode = currentTheme === "dark";

      // Add theme configuration
      schema.config = {
        ...schema.config,
        // Apply dark theme colors if in dark mode
        background: isDarkMode ? "transparent" : "white",
        axis: {
          ...schema.config?.axis,
          labelColor: isDarkMode ? "#e5e7eb" : "#374151",
          titleColor: isDarkMode ? "#e5e7eb" : "#374151",
          domainColor: isDarkMode ? "#4b5563" : "#9ca3af",
          tickColor: isDarkMode ? "#4b5563" : "#9ca3af",
          gridColor: isDarkMode
            ? "rgba(75, 85, 99, 0.2)"
            : "rgba(156, 163, 175, 0.2)",
        },
        title: {
          ...schema.config?.title,
          color: isDarkMode ? "#e5e7eb" : "#374151",
        },
        legend: {
          ...schema.config?.legend,
          labelColor: isDarkMode ? "#e5e7eb" : "#374151",
          titleColor: isDarkMode ? "#e5e7eb" : "#374151",
        },
        view: {
          ...schema.config?.view,
          stroke: isDarkMode ? "#4b5563" : "#e5e7eb",
        },
        // Ensure tooltip is styled correctly
        tooltip: {
          ...schema.config?.tooltip,
          fill: isDarkMode ? "#1f2937" : "#ffffff",
          stroke: isDarkMode ? "#374151" : "#e5e7eb",
          titleColor: isDarkMode ? "#e5e7eb" : "#111827",
          labelColor: isDarkMode ? "#d1d5db" : "#374151",
        },
      };

      // Detect if this is a pie chart
      const isPieChart =
        (typeof schema.mark === "object" && schema.mark.type === "arc") ||
        (typeof schema.mark === "string" && schema.mark === "arc") ||
        (schema.encoding && schema.encoding.theta);

      // Apply special handling for pie chart tooltips
      if (isPieChart) {
        // Ensure mark is an object
        if (typeof schema.mark === "string") {
          schema.mark = { type: schema.mark };
        }

        // Add tooltip configuration to avoid flicker
        schema.mark = {
          ...schema.mark,
          tooltip: true,
          // Add these properties to stabilize tooltip
          strokeWidth: 2,
          stroke: "#fff",
          // Reduce sensitivity to mouse movement
          cornerRadius: 0,
        };

        // Add proper data transformation to aggregate by category
        // Only if we don't already have pre-aggregated data
        if (!hasPreAggregatedData) {
          // Find the category field (usually in color encoding)
          let categoryField = "";
          let valueField = "";

          if (schema.encoding.color?.field) {
            categoryField = schema.encoding.color.field;
          }

          if (schema.encoding.theta?.field) {
            valueField = schema.encoding.theta.field;
          }

          // Add an aggregation transform if we have category and value fields
          if (categoryField && valueField) {
            // Add a transform to aggregate the data
            schema.transform = schema.transform || [];

            // Check if aggregation transform already exists
            const hasAggregationTransform = schema.transform.some(
              (t: any) =>
                t.aggregate && t.groupby && t.groupby.includes(categoryField)
            );

            if (!hasAggregationTransform) {
              schema.transform.push({
                aggregate: [
                  {
                    op: "sum",
                    field: valueField,
                    as: valueField,
                  },
                ],
                groupby: [categoryField],
              });
            }

            // Update the encoding to use the aggregated data
            if (schema.encoding.theta) {
              schema.encoding.theta = {
                ...schema.encoding.theta,
                aggregate: undefined, // Remove any existing aggregate
                field: valueField,
              };
            }
          }
        }

        // Configure tooltip channel if it exists
        if (!schema.encoding.tooltip) {
          // Auto-generate tooltips based on existing encoding
          const tooltipFields: Array<{
            field: string;
            type: string;
            title: string;
            format?: string;
          }> = [];

          // First add category field (usually in "color" encoding)
          if (schema.encoding.color?.field) {
            tooltipFields.push({
              field: schema.encoding.color.field,
              type: schema.encoding.color.type || "nominal",
              title: schema.encoding.color.title || schema.encoding.color.field,
            });
          }

          // Then add value field (usually in "theta" encoding)
          if (schema.encoding.theta?.field) {
            tooltipFields.push({
              field: schema.encoding.theta.field,
              type: schema.encoding.theta.type || "quantitative",
              title: schema.encoding.theta.title || schema.encoding.theta.field,
              format: ",.1f",
            });
          }

          if (tooltipFields.length > 0) {
            schema.encoding.tooltip = tooltipFields;
          }
        }
      }

      // Stringify the spec for embedding
      const specString = JSON.stringify(schema);
      setVegaSpec(specString);

      // Use setTimeout to ensure the DOM is ready
      setTimeout(() => {
        if (chartRef.current) {
          chartRef.current.innerHTML = ""; // Clear any previous content

          // Create a wrapper div for better control
          const wrapper = document.createElement("div");
          wrapper.id = "chart-wrapper";
          wrapper.style.width = "100%";
          wrapper.style.height = "100%";
          wrapper.style.display = "flex";
          wrapper.style.justifyContent = "center";
          wrapper.style.alignItems = "center";

          chartRef.current.appendChild(wrapper);

          embed(wrapper, schema, {
            renderer: "svg", // Use SVG for better tooltip stability
            actions: false,
            tooltip: {
              // Customize tooltip behavior to reduce flickering
              debounce: 50, // Debounce tooltip updates
              offsetX: 5, // Offset to avoid tooltip jumping
              offsetY: 5,
            },
            padding: { left: 50, right: 50, top: 50, bottom: 50 },
          })
            .then((result: any) => {
              vegaViewRef.current = result.view;

              // Apply initial sizing
              const svg = wrapper.querySelector("svg");
              if (svg) {
                svg.style.maxWidth = "100%";
                svg.style.maxHeight = "100%";

                // For pie charts, add event listener to stabilize tooltip
                if (isPieChart) {
                  // Add custom CSS for smoother tooltips
                  const style = document.createElement("style");
                  style.textContent = `
                    .vg-tooltip {
                      transition: transform 0.05s ease-out, opacity 0.1s ease-out !important;
                      pointer-events: none !important;
                    }
                  `;
                  wrapper.appendChild(style);
                }
              }

              setIsLoading(false);
            })
            .catch((err: Error) => {
              console.error("Vega embed error:", err);
              setError(`Failed to render chart: ${err.message}`);
              setIsLoading(false);
            });
        } else {
          console.error("Chart container ref is null");
          setError("Chart container not available");
          setIsLoading(false);
        }
      }, 300);
    } catch (error: any) {
      console.error("Error processing chart data:", error);
      setError(error.message || "Failed to process chart data");
      setIsLoading(false);
    }
  }, [isOpen, chartData, currentTheme]);

  // Handle zoom in
  const handleZoomIn = () => {
    const newZoomLevel = Math.min(zoomLevel + 0.25, 3); // Max zoom 3x
    setZoomLevel(newZoomLevel);
    applyZoom(newZoomLevel);
  };

  // Handle zoom out
  const handleZoomOut = () => {
    const newZoomLevel = Math.max(zoomLevel - 0.25, 0.5); // Min zoom 0.5x
    setZoomLevel(newZoomLevel);
    applyZoom(newZoomLevel);
  };

  // Improved zoom function to maintain center point
  const applyZoom = (newZoomLevel: number) => {
    if (!chartRef.current) return;

    const container = chartRef.current;
    const wrapper = container.querySelector("#chart-wrapper") as HTMLDivElement;
    if (!wrapper) return;

    const svg = wrapper.querySelector("svg");
    if (!svg) return;

    // Get the container's dimensions
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    // Calculate the current visible center point
    const viewportCenterX = container.scrollLeft + containerWidth / 2;
    const viewportCenterY = container.scrollTop + containerHeight / 2;

    // Calculate the center point as a percentage of the content's total size
    // This is important to maintain the same relative position when zooming
    const scrollableWidth = container.scrollWidth;
    const scrollableHeight = container.scrollHeight;

    // If scrollable dimensions are 0, use container dimensions as fallback
    const totalWidth = scrollableWidth || containerWidth;
    const totalHeight = scrollableHeight || containerHeight;

    // Calculate the relative center position (0-1)
    const relCenterX = viewportCenterX / totalWidth;
    const relCenterY = viewportCenterY / totalHeight;

    // Adjust wrapper dimensions BEFORE applying transform to avoid flickering
    wrapper.style.width = `${newZoomLevel * 100}%`;
    wrapper.style.height = `${newZoomLevel * 100}%`;
    wrapper.style.minWidth = `${newZoomLevel * 100}%`;
    wrapper.style.minHeight = `${newZoomLevel * 100}%`;

    // Apply the zoom transformation
    svg.style.transform = `scale(${newZoomLevel})`;
    svg.style.transformOrigin = "center center";

    // Remove transition to eliminate flickering effect
    svg.style.transition = "none";

    // Enable scrolling if zoomed in
    container.style.overflow = newZoomLevel > 1 ? "auto" : "hidden";

    // Immediately adjust scroll position without waiting
    if (container.scrollWidth > 0 && container.scrollHeight > 0) {
      const newScrollableWidth = container.scrollWidth;
      const newScrollableHeight = container.scrollHeight;

      // Calculate new scroll position to maintain the same relative center
      const newScrollLeft =
        relCenterX * newScrollableWidth - containerWidth / 2;
      const newScrollTop =
        relCenterY * newScrollableHeight - containerHeight / 2;

      // Apply new scroll position
      container.scrollLeft = newScrollLeft;
      container.scrollTop = newScrollTop;
    } else {
      // If dimensions aren't available yet, use a minimal timeout
      requestAnimationFrame(() => {
        if (!chartRef.current) return;

        const newScrollableWidth = chartRef.current.scrollWidth;
        const newScrollableHeight = chartRef.current.scrollHeight;

        // Calculate new scroll position to maintain the same relative center
        const newScrollLeft =
          relCenterX * newScrollableWidth - containerWidth / 2;
        const newScrollTop =
          relCenterY * newScrollableHeight - containerHeight / 2;

        // Apply new scroll position
        chartRef.current.scrollLeft = newScrollLeft;
        chartRef.current.scrollTop = newScrollTop;
      });
    }

    // Store current zoom level for next zoom operation
    prevZoomLevel.current = newZoomLevel;
  };

  // Function to open the chart in Vega Editor
  const openInVegaEditor = () => {
    if (vegaSpec) {
      const url = `https://vega.github.io/editor/#/custom/vega-lite?spec=${encodeURIComponent(vegaSpec)}`;
      window.open(url, "_blank");
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-[90vw] max-h-[90vh] overflow-auto"
        useBackButton={true}
      >
        <DialogHeader className="flex flex-row justify-between items-center">
          <DialogTitle useBackButton={true}>{t("expandView")}</DialogTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={handleZoomOut}
              disabled={zoomLevel <= 0.5 || isLoading}
              className="w-8 h-8"
              title="Zoom Out"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-xs font-mono">
              {Math.round(zoomLevel * 100)}%
            </span>
            <Button
              variant="outline"
              size="icon"
              onClick={handleZoomIn}
              disabled={zoomLevel >= 3 || isLoading}
              className="w-8 h-8"
              title="Zoom In"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div
          className="relative flex flex-col items-center w-full"
          style={{ minHeight: "600px" }}
        >
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
              <LoadingSpinner size={32} />
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="bg-destructive/10 text-destructive p-4 rounded-md flex items-center gap-2 max-w-[80%]">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            </div>
          )}

          <div
            className="w-full border border-border/20 rounded-md"
            style={{
              height: "600px",
              overflow: "hidden",
              position: "relative",
            }}
          >
            <div
              id="vega-chart-container"
              ref={chartRef}
              className="w-full h-full"
              style={{
                overflow: "auto",
                padding: "10px",
              }}
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
