import React, { useEffect, useState, useRef, useCallback } from "react";
import { Artifact } from "../../../types/chat";
import { Button } from "@/components/ui/button";
// Import vega-embed with proper type declaration
import embed from "vega-embed";
import {
  Plus,
  ArrowRight,
  RefreshCcw,
  MessageSquare,
  Sparkles,
  History,
  LayoutDashboard,
  AlertCircle,
  Info,
  Download,
  Maximize2,
  ArrowUpRight,
} from "lucide-react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "@/store/store";
import { useRouter } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectSeparator,
} from "@/components/ui/select";
import {
  useGetChartDataMutation,
  useGetChartsByMessageQuery,
} from "@/store/services/chartsApi";
import {
  Dashboard,
  useGetAllDashboardsQuery,
  useCreateDashboardMutation,
  useAddChartToDashboardMutation,
} from "@/store/services/dashboardApi";
import { AlternativeVisualizationQuery } from "@/store/services/chartsApi";
import DashboardDialog from "@/app/(protected)/dashboard/components/DashboardDialog";
import { cacheChartData } from "@/store/slices/chartDataSlice";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { motion, AnimatePresence } from "framer-motion";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useTheme } from "@/contexts/ThemeContext";
import { FetchBaseQueryError } from "@reduxjs/toolkit/query";
import { SerializedError } from "@reduxjs/toolkit";
import { AddToDashboardDialog } from "@/components/dashboard/AddToDashboardDialog";
import { useTranslations } from "next-intl";
import { ChartDialog } from "@/components/chart";
import { ChartRender } from "./sub-components/ChartRender";
import { formatDateWithTime } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";

// Helper function to check if error is a FetchBaseQueryError
const isFetchBaseQueryError = (
  error: FetchBaseQueryError | SerializedError | undefined
): error is FetchBaseQueryError => {
  return error !== undefined && "data" in error;
};

export const ChartsArtifact = () => {
  const t = useTranslations("chatPage.analyticsPal.chartsArtifact");
  const dispatch = useDispatch();
  const router = useRouter();
  const addToDashboardButtonRef = React.useRef<HTMLButtonElement>(null);
  const { data: dashboards, isLoading: isLoadingDashboards } =
    useGetAllDashboardsQuery();
  const [createDashboard, { isLoading: isCreatingDashboard }] =
    useCreateDashboardMutation();
  const [addChartToDashboard, { isLoading: isAddingChartToDashboard }] =
    useAddChartToDashboardMutation();
  const { theme } = useTheme();
  const [currentTheme, setCurrentTheme] = useState<"dark" | "light">("light");
  const [isDashboardAdded, setIsDashboardAdded] = useState(false);

  // Update current theme when theme changes
  useEffect(() => {
    const isDarkMode = document.documentElement.classList.contains("dark");
    setCurrentTheme(isDarkMode ? "dark" : "light");
  }, [theme]);

  const selectedArtifactMessageId = useSelector(
    (state: RootState) => state.chat.selectedArtifactMessageId
  );
  const cachedChartData = useSelector((state: RootState) =>
    selectedArtifactMessageId
      ? state.chartData.cache[selectedArtifactMessageId]
      : null
  );

  const [getChartData, { data: chartData, isLoading, error }] =
    useGetChartDataMutation();

  const [isCreateDashboardDialogOpen, setIsCreateDashboardDialogOpen] =
    useState(false);
  const [newDashboardName, setNewDashboardName] = useState("");
  const [newDashboardDescription, setNewDashboardDescription] = useState("");
  const [pendingChartData, setPendingChartData] = useState<any>(null);

  const [chatMessage, setChatMessage] = useState("");

  const [currentChartData, setCurrentChartData] = useState<any>(null);

  const [isAddToDashboardDialogOpen, setIsAddToDashboardDialogOpen] =
    useState(false);

  const [isHistoryDropdownOpen, setIsHistoryDropdownOpen] = useState(false);

  const {
    data: chartHistory,
    isLoading: isLoadingHistory,
    refetch: refetchHistory,
    isFetching: isFetchingHistory,
  } = useGetChartsByMessageQuery(selectedArtifactMessageId || "", {
    skip: !selectedArtifactMessageId || !isHistoryDropdownOpen,
  });

  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  const [isDownloading, setIsDownloading] = useState(false);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  const [isExpandedViewOpen, setIsExpandedViewOpen] = useState(false);

  const handleSendMessage = async () => {
    if (!chatMessage.trim()) return;

    try {
      const result = await getChartData({
        message_id: selectedArtifactMessageId,
        adjustment_query: chatMessage,
        force_create: true,
      }).unwrap();
      setCurrentChartData(result);
      setChatMessage(""); // Clear the input after sending
    } catch (error) {
      console.error("Failed to send adjustment query:", error);
    }
  };

  useEffect(() => {
    if (selectedArtifactMessageId) {
      getChartData({
        message_id: selectedArtifactMessageId,
        force_create: false,
      })
        .unwrap()
        .then((data) => {
          dispatch(
            cacheChartData({ messageId: selectedArtifactMessageId, data })
          );
        });
    }
  }, [selectedArtifactMessageId]);

  useEffect(() => {
    if (cachedChartData || chartData) {
      setCurrentChartData(chartData || cachedChartData);
    }
  }, [cachedChartData, chartData]);

  if (error) {
    return (
      <div className="p-4 text-muted-foreground flex flex-row items-center gap-2">
        <AlertCircle className="w-4 h-4" />
        {isFetchBaseQueryError(error)
          ? ((error.data as any)?.detail ?? t("errorLoadingChartData"))
          : (error.message ?? t("errorLoadingChartData"))}
      </div>
    );
  }

  if (isLoading || !currentChartData) {
    return (
      <div className="p-4 text-muted-foreground flex flex-row items-center gap-2">
        <LoadingSpinner size={16} />
        {t("loadingChartData")}
      </div>
    );
  }

  const handleAddToDashboard = async (dashboardId: string) => {
    try {
      setIsDashboardAdded(true);
      await addChartToDashboard({
        dashboardId,
        data: {
          chart_id: currentChartData.id,
          position_x: 0,
          position_y: 0,
          width: 4,
          height: 4,
          config: {},
        },
      }).unwrap();

      toast({
        title: t("addedToDashboard"),
        description: (
          <div className="flex items-center justify-between">
            {/* <span>{t("addedToDashboardDescription")}</span> */}
            <Button
              variant="ghost"
              size="sm"
              className="bg-primary/10 hover:bg-primary/20 mt-2"
              onClick={() => handleViewDashboard(dashboardId)}
            >
              {t("viewDashboard")}
            </Button>
          </div>
        ),
        // variant: "success",
      });

      // Return success to allow the dialog component to show toast
      setIsDashboardAdded(false);
      setIsAddToDashboardDialogOpen(false);
      // Store the path but don't navigate yet
      localStorage.setItem("previousPath", window.location.pathname);
      return true;
    } catch (error) {
      console.error("Failed to add chart to dashboard:", error);
      throw error; // Propagate error to dialog component
    }
  };

  const handleViewDashboard = (dashboardId: string) => {
    router.push(`/dashboard?dashboard=${dashboardId}`);
    // Set the current path in local storage before navigating
    localStorage.setItem("previousPath", window.location.pathname);
  };

  const handleCreateNewDashboard = () => {
    const newChart = {
      // id: uuidv4(),
      content: JSON.stringify(currentChartData.chart_schema),
      title: currentChartData.title || t("untitledChart"),
    };

    setNewDashboardName("");
    setNewDashboardDescription("");
    setPendingChartData(newChart);
    setIsCreateDashboardDialogOpen(true);
  };

  const handleCreateDashboard = async () => {
    if (!newDashboardName.trim()) return;

    try {
      // Step 1: Create a new dashboard
      const newDashboard = await createDashboard({
        title: newDashboardName,
        description: newDashboardDescription,
      }).unwrap();

      // Step 2: Add the chart to the newly created dashboard
      if (pendingChartData && newDashboard.dashboard_id) {
        await addChartToDashboard({
          dashboardId: newDashboard.dashboard_id,
          data: {
            chart_id: currentChartData.id,
            position_x: 0,
            position_y: 0,
            width: 4,
            height: 4,
            config: {},
          },
        });

        // Set the current path in local storage before navigating
        localStorage.setItem("previousPath", window.location.pathname);

        // Step 3: Redirect to the dashboard
        router.push(`/dashboard?dashboard=${newDashboard.dashboard_id}`);
      }

      // Reset state
      setIsCreateDashboardDialogOpen(false);
      setNewDashboardName("");
      setNewDashboardDescription("");
      setPendingChartData(null);
    } catch (error) {
      console.error("Failed to create dashboard:", error);
    }
  };

  const handleRefreshChart = async () => {
    await getChartData({
      message_id: selectedArtifactMessageId,
      force_create: true,
    })
      .unwrap()
      .then((result) => {
        setCurrentChartData(result);
      });
  };

  const handleHistoryDropdownChange = (open: boolean) => {
    setIsHistoryDropdownOpen(open);
    setTimeout(() => {
      if (open && chartHistory?.length && chartHistory?.length > 0) {
        refetchHistory();
      }
    });
  };

  const visualizationQueries =
    currentChartData?.alternative_visualization_queries || [];

  const handleDownloadChart = async (format: "svg" | "png") => {
    setIsDownloading(true);

    try {
      const container = chartContainerRef.current;
      if (!container) {
        throw new Error("Chart container not found");
      }

      // Get the SVG element directly from the DOM
      const svgElement = container.querySelector("svg");
      if (!svgElement) {
        throw new Error("SVG element not found");
      }

      // Convert SVG to string
      const svgString = new XMLSerializer().serializeToString(svgElement);
      const svgBlob = new Blob([svgString], { type: "image/svg+xml" });

      if (format === "svg") {
        // Download as SVG
        const url = URL.createObjectURL(svgBlob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `chart-${currentChartData?.id || "export"}.svg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        // Try simpler approach for PNG conversion to avoid errors
        try {
          // Method 1: Direct SVG to canvas conversion
          await directSvgToPng(svgElement, currentChartData?.id || "export");
        } catch (err) {
          console.error("First PNG method failed:", err);

          // Method 2: Use SVG data URL approach
          try {
            await svgDataUrlToPng(svgString, currentChartData?.id || "export");
          } catch (err2) {
            console.error("Second PNG method failed:", err2);
            throw new Error("All PNG conversion methods failed");
          }
        }
      }
    } catch (error) {
      console.error("Error downloading chart:", error);
      alert("Failed to download chart. Please try again.");
    } finally {
      setIsDownloading(false);
    }
  };

  // Helper function for direct SVG to PNG conversion
  const directSvgToPng = async (svgElement: SVGElement, filename: string) => {
    // Create a canvas with appropriate size
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    if (!ctx) {
      throw new Error("Could not get canvas context");
    }

    // Get dimensions
    const width = svgElement.getBoundingClientRect().width;
    const height = svgElement.getBoundingClientRect().height;

    // Handle high-DPI displays
    const scale = 2; // Fixed scale factor for consistent results

    // Set canvas dimensions
    canvas.width = width * scale;
    canvas.height = height * scale;

    // Scale for high resolution
    ctx.scale(scale, scale);

    // Create image from SVG
    const svgData = new XMLSerializer().serializeToString(svgElement);
    const svgUrl =
      "data:image/svg+xml;base64," +
      btoa(unescape(encodeURIComponent(svgData)));

    // Create image and wait for it to load
    const img = new Image();
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = reject;
      img.src = svgUrl;
    });

    // Draw and export
    ctx.drawImage(img, 0, 0);
    const pngUrl = canvas.toDataURL("image/png");

    // Download
    const link = document.createElement("a");
    link.href = pngUrl;
    link.download = `chart-${filename}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Alternative method using SVG data URL
  const svgDataUrlToPng = async (svgString: string, filename: string) => {
    // Create an image to load the SVG
    const img = new Image();

    // Convert SVG string to data URL
    const svgUrl =
      "data:image/svg+xml;base64," +
      btoa(unescape(encodeURIComponent(svgString)));

    // Wait for image to load
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("Failed to load SVG as image"));
      img.src = svgUrl;
    });

    // Create canvas matching image dimensions
    const canvas = document.createElement("canvas");
    const scale = 2;
    canvas.width = img.width * scale;
    canvas.height = img.height * scale;

    // Get context and draw
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      throw new Error("Could not get canvas context");
    }

    // Scale for higher quality
    ctx.scale(scale, scale);

    // Draw and export
    ctx.drawImage(img, 0, 0);
    const pngUrl = canvas.toDataURL("image/png");

    // Download
    const link = document.createElement("a");
    link.href = pngUrl;
    link.download = `chart-${filename}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="w-full space-y-3">
      {/* Chart Controls */}
      <div className="flex items-center justify-between bg-muted/30 p-3 rounded-md">
        <div className="flex items-center gap-2 flex-grow">
          {/* Chart Title */}
          <h3 className="text-sm font-medium">
            {t("chart")}:{" "}
            {currentChartData.chart_type
              .split("_")
              .join(" ")
              .charAt(0)
              .toUpperCase() +
              currentChartData.chart_type.split("_").join(" ").slice(1)}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {/* Regenerate Chart */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleRefreshChart}
                  className="w-10 h-8 shadow-none"
                >
                  <RefreshCcw className="h-[0.85rem] w-[0.85rem]" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{t("regenerateChart")}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Suggestions and Chat */}
          <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="w-10 h-8 shadow-none"
                    >
                      <MessageSquare className="h-[0.85rem] w-[0.85rem]" />
                    </Button>
                  </PopoverTrigger>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t("askMIPALToUpdateTheChart")}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <PopoverContent
              className="w-96 p-0 bg-background/95 backdrop-blur-sm border border-border/50 shadow-lg"
              align="end"
            >
              <div className="flex flex-col">
                {/* Suggestions Section */}
                <div className="px-4 pt-3 pb-2 border-b border-border/50">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-primary" />
                    <h4 className="text-sm font-medium">
                      {t("suggestedQueries")}
                    </h4>
                  </div>
                  <ScrollArea className="h-[130px] pr-4">
                    <div className="grid grid-cols-1 gap-2">
                      <AnimatePresence>
                        {visualizationQueries?.map(
                          (
                            query: AlternativeVisualizationQuery,
                            index: number
                          ) => (
                            <motion.div
                              key={index}
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -10 }}
                              transition={{
                                duration: 0.2,
                                delay: index * 0.05,
                              }}
                              className="text-xs px-3 py-1.5 rounded-xl bg-primary/10 hover:bg-primary/20 border border-primary/20 hover:border-primary/30 text-primary cursor-pointer transition-all duration-200 ease-in-out hover:scale-105 flex items-center gap-1 w-full"
                              onClick={() => {
                                setChatMessage(query.query);
                              }}
                            >
                              <span className="flex-1">{query.query}</span>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Info className="h-3 w-3 text-primary/70 hover:text-primary flex-shrink-0" />
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p className="text-xs max-w-[300px]">
                                      {query.description}
                                    </p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </motion.div>
                          )
                        )}
                      </AnimatePresence>
                    </div>
                  </ScrollArea>
                </div>
                {/* Chat Section */}
                <div className="p-4">
                  <div className="relative">
                    <Input
                      placeholder={t("askMIPALToUpdateTheChart")}
                      value={chatMessage}
                      onChange={(e) => setChatMessage(e.target.value)}
                      className="h-10 rounded-full border-border/50 bg-background/50 pr-10 focus:border-primary/50 transition-all duration-200"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          handleSendMessage();
                        }
                      }}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-10 w-10 rounded-full hover:bg-primary/10 transition-colors duration-200"
                      onClick={handleSendMessage}
                    >
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </PopoverContent>
          </Popover>

          {/* Chart History */}
          <TooltipProvider>
            <Select
              value={currentChartData?.id || ""}
              onValueChange={(value) => {
                const selectedHistory = chartHistory?.find(
                  (item: any) => item.id === value
                );
                if (selectedHistory) {
                  setCurrentChartData(selectedHistory);
                }
              }}
              onOpenChange={handleHistoryDropdownChange}
            >
              <SelectTrigger
                className="p-0 w-10 h-8 justify-center items-center hover:bg-accent"
                showIcon={false}
              >
                <Tooltip>
                  <TooltipTrigger asChild>
                    <History className="h-[0.85rem] w-[0.85rem]" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t("chartHistory")}</p>
                  </TooltipContent>
                </Tooltip>
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value={currentChartData?.id || ""}>
                  {t("currentVersion")}
                </SelectItem>
                <SelectSeparator />
                {isLoadingHistory || isFetchingHistory ? (
                  <SelectItem value="loading" disabled>
                    {t("loadingHistory")}
                  </SelectItem>
                ) : !chartHistory?.length ? (
                  <SelectItem value="no-history" disabled>
                    {t("noHistoryAvailable")}
                  </SelectItem>
                ) : (
                  chartHistory.map((item: any) => (
                    <SelectItem key={item.id} value={item.id}>
                      {item.chart_type} -{" "}
                      {new Date(item.created_at + "+00:00").toLocaleString(
                        undefined,
                        {
                          year: "numeric",
                          month: "numeric",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                          hour12: false,
                        }
                      )}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </TooltipProvider>

          {/* More Options */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="w-10 h-8 shadow-none"
                  ref={addToDashboardButtonRef}
                  onClick={() => {
                    setIsAddToDashboardDialogOpen(true);
                    // Store the current focus before opening dialog
                    addToDashboardButtonRef.current?.focus();
                  }}
                >
                  <LayoutDashboard className="h-[0.85rem] w-[0.85rem]" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{t("addToDashboard")}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Download Chart Dropdown */}
          <TooltipProvider>
            <Select
              onValueChange={(value) => {
                if (value === "svg" || value === "png") {
                  handleDownloadChart(value);
                }
              }}
              value=""
              disabled={isDownloading}
            >
              <SelectTrigger
                className="w-auto h-8 justify-center items-center hover:bg-accent"
                showIcon={false}
              >
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Download className="h-[0.85rem] w-[0.85rem]" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t("downloadChart")}</p>
                  </TooltipContent>
                </Tooltip>
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value="svg">
                  <div className="flex items-center">
                    <span className="text-xs font-mono">SVG</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {t("vectorFormat")}
                    </span>
                  </div>
                </SelectItem>
                <SelectItem value="png">
                  <div className="flex items-center">
                    <span className="text-xs font-mono">PNG</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {t("imageFormat")}
                    </span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </TooltipProvider>

          {/* Maximize Chart */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsExpandedViewOpen(true)}
                  className="px-2"
                >
                  <Maximize2 className="w-4 h-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent align="center">
                <p>{t("expandView")}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Chart visualization */}
      <div className="bg-card rounded-md overflow-hidden">
        {isLoading ? (
          <div className="p-4 text-muted-foreground">{t("loadingChart")}</div>
        ) : (
          <div ref={chartContainerRef} className="w-full h-[400px]">
            <ChartRender
              key={`chart-${currentChartData.id}-${currentTheme}`}
              chartData={currentChartData.chart_data}
              chartSchema={currentChartData.chart_schema}
              isDarkMode={currentTheme === "dark"}
            />
          </div>
        )}
      </div>

      {/* Title and Description Section */}
      <div className="border-t border-border/50 pt-4">
        {/* <h2 className="text-xl font-semibold">
          {currentChartData.title?.replace("# ", "") || "Analysis Results"}
        </h2> */}
        {currentChartData.description && (
          <p className="text-sm">{currentChartData.description}</p>
        )}
      </div>

      {/* Created at */}
      <div className="flex flex-row justify-end border-t border-border/50 pt-4">
        <label className="text-[11px] text-muted-foreground">
          Created at: {formatDateWithTime(currentChartData.created_at)}
          {/* {new Date(currentChartData.created_at + "+00:00").toLocaleString(
            undefined,
            {
              year: "numeric",
              month: "numeric",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            }
          )} */}
        </label>
      </div>

      {/* Add to Dashboard Dialog */}
      <AddToDashboardDialog
        isOpen={isAddToDashboardDialogOpen}
        onOpenChange={setIsAddToDashboardDialogOpen}
        dashboards={dashboards}
        isLoadingDashboards={isLoadingDashboards}
        onAddToDashboard={(dashboardId) => {
          handleAddToDashboard(dashboardId);
        }}
        onViewDashboard={handleViewDashboard}
        onCreateNewDashboard={() => {
          setIsAddToDashboardDialogOpen(false);
          handleCreateNewDashboard();
        }}
        buttonRef={addToDashboardButtonRef}
        isDashboardAdded={isDashboardAdded}
      />

      {/* Dashboard Dialog for creating a new dashboard */}
      <DashboardDialog
        isOpen={isCreateDashboardDialogOpen}
        onOpenChange={setIsCreateDashboardDialogOpen}
        title={t("createNewDashboard")}
        description={t(
          "giveYourDashboardADescriptiveNameToHelpYouOrganizeYourDataVisualizations"
        )}
        dashboardName={newDashboardName}
        dashboardDescription={newDashboardDescription}
        onDashboardNameChange={setNewDashboardName}
        onDashboardDescriptionChange={setNewDashboardDescription}
        onSubmit={handleCreateDashboard}
        submitButtonText={t("createDashboard")}
        isLoading={isCreatingDashboard || isAddingChartToDashboard}
      />

      {/* Chart Dialog */}
      {currentChartData && (
        <ChartDialog
          isOpen={isExpandedViewOpen}
          onOpenChange={setIsExpandedViewOpen}
          chartData={currentChartData}
        />
      )}

      {/* Add Toaster component */}
      <Toaster />
    </div>
  );
};
