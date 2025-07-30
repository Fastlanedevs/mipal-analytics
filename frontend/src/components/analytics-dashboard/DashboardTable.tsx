import React, { useEffect, useState, useRef } from "react";
import { useTheme } from "@/contexts/ThemeContext";
import { DataTable } from "@/components/table/DataTable";
import { DataContent } from "@/app/(protected)/chat/types/chat";
import { useTranslations } from "next-intl";
interface DashboardTableProps {
  content: string;
  height: number;
  width: number;
  forceRender?: number;
}

export function DashboardTable({
  content,
  height,
  width,
  forceRender,
}: DashboardTableProps) {
  const t = useTranslations("dashboard.table");
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<any[]>([]);
  const { theme } = useTheme();
  const [currentTheme, setCurrentTheme] = useState<"dark" | "light">(
    theme === "dark" ? "dark" : "light"
  );
  const [isResizing, setIsResizing] = useState(false);
  const resizeTimeoutRef = useRef<NodeJS.Timeout>();
  const [refreshKey, setRefreshKey] = useState<number>(0);

  // Update current theme when theme changes
  useEffect(() => {
    const isDarkMode = document.documentElement.classList.contains("dark");
    setCurrentTheme(isDarkMode ? "dark" : "light");
  }, [theme]);

  // Parse the content to extract data for the table
  useEffect(() => {
    try {
      // Handle both direct array data and Vega-Lite spec format
      let parsedData: any[] = [];

      if (typeof content === "string") {
        // First parse the outer JSON string
        const outerParsed = JSON.parse(content);

        // If the content is still a string, parse it again
        const parsedContent =
          typeof outerParsed === "string"
            ? JSON.parse(outerParsed)
            : outerParsed;

        // Check if it's a direct array of objects
        if (Array.isArray(parsedContent)) {
          parsedData = parsedContent;
        }
        // Extract data from the Vega-Lite spec
        else if (parsedContent.data?.values) {
          parsedData = parsedContent.data.values;
        }
      }

      setData(parsedData);
    } catch (error) {
      console.error("Error parsing table data:", error);
      setData([]);
    }
  }, [content, forceRender]);

  // Add resize observer for smooth resizing
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const container = containerRef.current;
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;

        // Calculate the available space
        const adjustedWidth = containerWidth - 16; // 8px padding on each side
        const adjustedHeight =
          containerHeight > 0 ? containerHeight - 16 : height;

        // Update dimensions if they've changed
        if (adjustedWidth !== width || adjustedHeight !== height) {
          // Force a re-render with new dimensions
          setRefreshKey((prev: number) => prev + 1);
        }
      }
    };

    // Initial update
    updateDimensions();

    // Add resize observer with debouncing
    const resizeObserver = new ResizeObserver((entries) => {
      // Clear any existing timeout
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current);
      }

      // Set resizing state to true when resize starts
      setIsResizing(true);

      // Update dimensions immediately for smoother experience
      updateDimensions();

      // Set resizing state to false after resize is complete
      resizeTimeoutRef.current = setTimeout(() => {
        setIsResizing(false);
      }, 150); // Reduced from 100ms to 150ms for smoother transition
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
  }, [height, width, forceRender]);

  return (
    <div
      className={`w-full flex-grow h-full flex flex-col ${
        isResizing ? "resizing" : ""
      }`}
      ref={containerRef}
      style={{
        backgroundColor:
          currentTheme === "dark" ? "var(--background)" : "var(--background)",
        transition: "all 0.2s ease-in-out",
        willChange: "transform",
        minHeight: "50%",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div className="flex-1 overflow-auto">
        {data.length > 0 ? (
          <DataTable content={data} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">{t("noDataAvailable")}</p>
          </div>
        )}
      </div>
    </div>
  );
}
