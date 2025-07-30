import React, { useEffect, useState, useRef } from "react";
import { useTheme } from "@/contexts/ThemeContext";
import embed from "vega-embed";

interface DashboardChartProps {
  content: string;
  height: number;
  width: number;
  forceRender?: number;
  chartData?: any; // Add optional chartData prop
}

export function DashboardChart({
  content,
  height,
  width,
  forceRender,
  chartData, // Accept chartData prop
}: DashboardChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ height, width });
  const { theme } = useTheme();
  const [currentTheme, setCurrentTheme] = useState<"dark" | "light">(
    theme === "dark" ? "dark" : "light"
  );
  const [isResizing, setIsResizing] = useState(false);
  const resizeTimeoutRef = useRef<NodeJS.Timeout>();
  const vegaViewRef = useRef<any>(null);
  const chartSpecRef = useRef<any>(null);
  // Add a mount state ref to prevent updates after unmount
  const isMounted = useRef(true);

  // Cleanup function for unmounting
  useEffect(() => {
    return () => {
      isMounted.current = false;
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current);
      }
      // Clean up Vega view if it exists
      if (vegaViewRef.current) {
        try {
          vegaViewRef.current.finalize();
        } catch (e) {
          console.error("Error finalizing Vega view:", e);
        }
      }
    };
  }, []);

  // Watch for theme changes using MutationObserver
  useEffect(() => {
    // Set up observer to watch for class changes on html element
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (
          mutation.attributeName === "class" &&
          mutation.target === document.documentElement
        ) {
          const newIsDarkMode =
            document.documentElement.classList.contains("dark");
          const newTheme = newIsDarkMode ? "dark" : "light";

          if (newTheme !== currentTheme) {
            setCurrentTheme(newTheme);
          }
        }
      });
    });

    // Start observing
    observer.observe(document.documentElement, { attributes: true });

    // Cleanup
    return () => observer.disconnect();
  }, [currentTheme]);

  // Update dimensions when container size changes or forceRender changes
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current && isMounted.current) {
        const container = containerRef.current;
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;

        // Skip if container has no size yet
        if (containerWidth <= 0 || containerHeight <= 0) return;

        // Calculate the available space with a small buffer
        const adjustedWidth = Math.max(containerWidth - 16, 100); // Minimum width of 100px
        const adjustedHeight = Math.max(containerHeight - 16, 100); // Minimum height of 100px

        setDimensions((prevDimensions) => {
          // Only update if the change is significant (more than 5px to reduce unnecessary updates)
          if (
            Math.abs(prevDimensions.width - adjustedWidth) > 5 ||
            Math.abs(prevDimensions.height - adjustedHeight) > 5
          ) {
            return { width: adjustedWidth, height: adjustedHeight };
          }
          return prevDimensions;
        });
      }
    };

    // Initial update
    updateDimensions();

    // Add resize observer with minimal debouncing
    const resizeObserver = new ResizeObserver((entries) => {
      // Clear any existing timeout
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current);
      }

      // Set resizing state to true when resize starts
      if (isMounted.current) {
        setIsResizing(true);
      }

      // Update dimensions immediately for smoother experience
      updateDimensions();

      // Set resizing state to false after resize is complete
      resizeTimeoutRef.current = setTimeout(() => {
        if (isMounted.current) {
          setIsResizing(false);

          // Resize the chart if a view exists
          if (vegaViewRef.current) {
            try {
              vegaViewRef.current.resize().run();
            } catch (e) {
              console.error("Error resizing chart:", e);
            }
          }
        }
      }, 50); // Reduced to 50ms for more responsive feel
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current);
      }
      resizeObserver.disconnect();
    };
  }, [forceRender]); // Only depend on forceRender to avoid circular dependencies

  // Process chart content and prepare spec
  useEffect(() => {
    if (!isMounted.current) return;

    try {
      // Parse content if it's a string
      let parsedContent;
      if (typeof content === "string") {
        try {
          parsedContent = JSON.parse(content);
        } catch (e) {
          console.error(
            "Failed to parse content as JSON, content might already be an object:",
            e
          );
          parsedContent = content; // Use as is if it's not valid JSON
        }
      } else {
        parsedContent = content; // Use as is if it's not a string
      }

      // Create a clean copy of the spec to work with
      const parsedSpec = JSON.parse(JSON.stringify(parsedContent));

      if (!parsedSpec.$schema) {
        parsedSpec.$schema = "https://vega.github.io/schema/vega-lite/v5.json";
      }

      // Process chartData if provided
      let processedChartData;
      if (chartData) {
        if (typeof chartData === "string") {
          try {
            processedChartData = JSON.parse(chartData);
          } catch (e) {
            console.error("Failed to parse chartData:", e);
          }
        } else {
          processedChartData = chartData;
        }

        // Convert string numbers to actual numbers in the data
        if (Array.isArray(processedChartData)) {
          processedChartData = processedChartData.map((item) => {
            const newItem: Record<string, any> = {};

            // Process each field in the item
            for (const [key, value] of Object.entries(item)) {
              // Handle string numbers by converting them to actual numbers
              if (
                typeof value === "string" &&
                !isNaN(Number(value)) &&
                value.trim() !== ""
              ) {
                newItem[key] = Number(value);
              } else if (
                typeof value === "string" &&
                /^\d{4}-\d{2}-\d{2}/.test(value) &&
                !isNaN(Date.parse(value))
              ) {
                // Properly handle date strings
                newItem[key] = new Date(value);
              } else {
                newItem[key] = value;
              }
            }
            return newItem;
          });
        }
      }

      // Handle data in the spec
      if (processedChartData) {
        // If explicit chartData is provided, use it
        if (!parsedSpec.data) {
          parsedSpec.data = {};
        }
        parsedSpec.data.values = processedChartData;
      } else if (parsedSpec.chart_data) {
        // If the spec has chart_data, use it
        let specChartData;
        if (typeof parsedSpec.chart_data === "string") {
          try {
            specChartData = JSON.parse(parsedSpec.chart_data);
          } catch (e) {
            console.error("Failed to parse chart_data:", e);
            specChartData = [];
          }
        } else {
          specChartData = parsedSpec.chart_data;
        }

        // Process data to ensure numeric values are numbers
        if (Array.isArray(specChartData)) {
          specChartData = specChartData.map((item) => {
            const newItem: Record<string, any> = {};

            // Process each field in the item
            for (const [key, value] of Object.entries(item)) {
              // Handle string numbers by converting them to actual numbers
              if (
                typeof value === "string" &&
                !isNaN(Number(value)) &&
                value.trim() !== ""
              ) {
                newItem[key] = Number(value);
              } else if (
                typeof value === "string" &&
                /^\d{4}-\d{2}-\d{2}/.test(value) &&
                !isNaN(Date.parse(value))
              ) {
                // Properly handle date strings
                newItem[key] = new Date(value);
              } else {
                newItem[key] = value;
              }
            }
            return newItem;
          });
        }

        // Set up the data object
        if (!parsedSpec.data) {
          parsedSpec.data = {};
        }
        parsedSpec.data.values = specChartData;
      }

      // Make sure all data values are properly processed
      if (parsedSpec.data?.values) {
        // Filter out invalid values
        parsedSpec.data.values = parsedSpec.data.values.filter((item: any) => {
          // Basic validation - skip null or undefined items
          return item !== null && item !== undefined;
        });
      }

      // Ensure proper sizing
      parsedSpec.width = "container";
      parsedSpec.height = "container";
      parsedSpec.autosize = {
        type: "fit",
        contains: "padding",
        resize: true,
      };

      // Identify chart type for special handling
      const chartType =
        typeof parsedSpec.mark === "object"
          ? parsedSpec.mark.type
          : parsedSpec.mark;

      // Add tooltip support by default
      if (typeof parsedSpec.mark === "string") {
        parsedSpec.mark = {
          type: parsedSpec.mark,
          tooltip: true,
        };
      } else if (
        typeof parsedSpec.mark === "object" &&
        parsedSpec.mark.tooltip !== false
      ) {
        parsedSpec.mark.tooltip = true;
      }

      // Store the processed spec in the ref
      chartSpecRef.current = parsedSpec;

      // Render the chart with current theme
      renderChart();
    } catch (error) {
      console.error("Error processing chart specification:", error);
    }
  }, [content, forceRender, chartData, dimensions]);

  // Render chart function to apply theme and render
  const renderChart = () => {
    if (!containerRef.current || !chartSpecRef.current || !isMounted.current) {
      return;
    }

    // Clean up previous view if it exists
    if (vegaViewRef.current) {
      try {
        vegaViewRef.current.finalize();
        vegaViewRef.current = null;
      } catch (e) {
        console.error("Error cleaning up previous view:", e);
      }
    }

    // Clear the container
    if (containerRef.current) {
      containerRef.current.innerHTML = "";
    }

    const parsedSpec = JSON.parse(JSON.stringify(chartSpecRef.current));
    const isDarkMode = currentTheme === "dark";

    // Apply theme based on the current theme
    parsedSpec.config = {
      ...parsedSpec.config,
      // Apply dark theme colors if in dark mode
      background: isDarkMode ? "transparent" : "white",
      axis: {
        ...parsedSpec.config?.axis,
        labelColor: isDarkMode ? "#e5e7eb" : "#374151",
        titleColor: isDarkMode ? "#e5e7eb" : "#374151",
        domainColor: isDarkMode ? "#4b5563" : "#9ca3af",
        tickColor: isDarkMode ? "#4b5563" : "#9ca3af",
        gridColor: isDarkMode
          ? "rgba(75, 85, 99, 0.2)"
          : "rgba(156, 163, 175, 0.2)",
      },
      title: {
        ...parsedSpec.config?.title,
        color: isDarkMode ? "#e5e7eb" : "#374151",
      },
      legend: {
        ...parsedSpec.config?.legend,
        labelColor: isDarkMode ? "#e5e7eb" : "#374151",
        titleColor: isDarkMode ? "#e5e7eb" : "#374151",
      },
      view: {
        ...parsedSpec.config?.view,
        stroke: isDarkMode ? "#4b5563" : "#e5e7eb",
      },
      // Ensure tooltip is styled correctly
      tooltip: {
        ...parsedSpec.config?.tooltip,
        fill: isDarkMode ? "#1f2937" : "#ffffff",
        stroke: isDarkMode ? "#374151" : "#e5e7eb",
        titleColor: isDarkMode ? "#e5e7eb" : "#111827",
        labelColor: isDarkMode ? "#d1d5db" : "#374151",
      },
    };

    // Render the chart using vega-embed
    embed(containerRef.current, parsedSpec, {
      renderer: "svg", // Use SVG for better quality
      actions: false,
      theme: isDarkMode ? "dark" : "light",
      padding: { left: 20, right: 20, top: 20, bottom: 20 },
      tooltip: {
        // Customize tooltip behavior for better display
        debounce: 50,
        offsetX: 5,
        offsetY: 5,
      },
    })
      .then((result: any) => {
        if (isMounted.current) {
          vegaViewRef.current = result.view;

          // Force resize to fit container
          result.view.resize().run();
        }
      })
      .catch((err: Error) => {
        console.error("Error rendering chart:", err);
      });
  };

  // Re-render chart when theme changes
  useEffect(() => {
    if (chartSpecRef.current) {
      renderChart();
    }
  }, [currentTheme]);

  return (
    <div
      className={`w-full h-full ${isResizing ? "resizing" : ""}`}
      ref={containerRef}
      style={{
        backgroundColor:
          currentTheme === "dark" ? "var(--background)" : "var(--background)",
        transition: "all 0.2s ease-in-out",
        willChange: "transform",
      }}
    />
  );
}
