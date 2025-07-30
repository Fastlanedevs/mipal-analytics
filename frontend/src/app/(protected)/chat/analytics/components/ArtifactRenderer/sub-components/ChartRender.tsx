import React, { useEffect, useRef, useState } from "react";
import embed from "vega-embed";

interface ChartRenderProps {
  chartData: any;
  chartSchema: any;
  isDarkMode: boolean;
}

export const ChartRender: React.FC<ChartRenderProps> = ({
  chartData,
  chartSchema,
  isDarkMode: initialIsDarkMode,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const [vegaView, setVegaView] = useState<any>(null);
  const [isDarkMode, setIsDarkMode] = useState(initialIsDarkMode);

  // Watch for theme changes using MutationObserver
  useEffect(() => {
    // Initial theme state
    const currentIsDarkMode =
      document.documentElement.classList.contains("dark");
    setIsDarkMode(currentIsDarkMode);

    // Set up observer to watch for class changes on html element
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (
          mutation.attributeName === "class" &&
          mutation.target === document.documentElement
        ) {
          const newIsDarkMode =
            document.documentElement.classList.contains("dark");
          if (newIsDarkMode !== isDarkMode) {
            setIsDarkMode(newIsDarkMode);
          }
        }
      });
    });

    // Start observing
    observer.observe(document.documentElement, { attributes: true });

    // Cleanup
    return () => observer.disconnect();
  }, []); // Empty dependency array to run only once on mount

  // Convert string numbers to actual numbers
  const processData = (data: any[]) => {
    return data.map((item) => {
      const result: Record<string, any> = {};

      Object.entries(item).forEach(([key, value]) => {
        if (typeof value === "string" && !isNaN(Number(value))) {
          result[key] = Number(value);
        } else {
          result[key] = value;
        }
      });

      return result;
    });
  };

  useEffect(() => {
    if (!chartRef.current || !chartData || !chartSchema) return;

    // Clean up previous view
    if (vegaView) {
      try {
        vegaView.finalize();
      } catch (e) {
        console.error("Error cleaning up previous view", e);
      }
    }

    const container = chartRef.current;
    container.innerHTML = "";

    // Create a deep copy of the schema
    const spec = JSON.parse(JSON.stringify(chartSchema));

    // Process the data
    const processedData = processData(chartData);

    // Apply data to the spec
    spec.data = { values: processedData };

    // Ensure proper sizing
    spec.width = "container";
    spec.height = "container";
    spec.autosize = { type: "fit", contains: "padding" };

    // Apply theme configuration
    spec.config = {
      ...spec.config,
      background: isDarkMode ? "transparent" : "white",
      axis: {
        ...spec.config?.axis,
        labelColor: isDarkMode ? "#e5e7eb" : "#374151",
        titleColor: isDarkMode ? "#e5e7eb" : "#374151",
        domainColor: isDarkMode ? "#4b5563" : "#9ca3af",
        tickColor: isDarkMode ? "#4b5563" : "#9ca3af",
        gridColor: isDarkMode
          ? "rgba(75, 85, 99, 0.2)"
          : "rgba(156, 163, 175, 0.2)",
      },
      title: {
        ...spec.config?.title,
        color: isDarkMode ? "#e5e7eb" : "#374151",
      },
      legend: {
        ...spec.config?.legend,
        labelColor: isDarkMode ? "#e5e7eb" : "#374151",
        titleColor: isDarkMode ? "#e5e7eb" : "#374151",
      },
      view: {
        ...spec.config?.view,
        stroke: isDarkMode ? "#4b5563" : "#e5e7eb",
      },
    };

    // Render the chart
    const renderChart = async () => {
      try {
        const result = await embed(container, spec, {
          renderer: "svg",
          actions: false,
          theme: isDarkMode ? "dark" : "light",
          padding: { left: 20, right: 20, top: 20, bottom: 20 },
          tooltip: {
            // Customize tooltip behavior for better display
            debounce: 50,
            offsetX: 5,
            offsetY: 5,
          },
        });

        setVegaView(result.view);

        // Force resize to fit container
        result.view.resize().run();
      } catch (error) {
        console.error("Error rendering chart:", error);
      }
    };

    renderChart();

    // Cleanup on unmount
    return () => {
      if (vegaView) {
        try {
          vegaView.finalize();
        } catch (e) {
          console.error("Error finalizing view", e);
        }
      }
    };
  }, [chartData, chartSchema, isDarkMode]);

  return <div ref={chartRef} style={{ width: "100%", height: "400px" }} />;
};
