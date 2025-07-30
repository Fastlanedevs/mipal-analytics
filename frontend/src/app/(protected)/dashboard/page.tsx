"use client";
import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "@/store/store";
import {
  Responsive as ResponsiveGridLayout,
  WidthProvider,
  Layouts,
} from "react-grid-layout";
import { Button } from "@/components/ui/button";
import {
  Plus,
  Trash2,
  Lock,
  Unlock,
  Save,
  ArrowLeft,
  Edit,
  Share,
  Maximize2,
  Hourglass,
  RefreshCcw,
} from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import { updateLayout } from "@/store/slices/dashboardSlice";
import { DashboardChart } from "@/components/analytics-dashboard/DashboardChart";
import { DashboardTable } from "@/components/analytics-dashboard/DashboardTable";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Dashboard as DashboardType,
  useGetDashboardByIdQuery,
  useLazyRefreshDashboardQuery,
} from "@/store/services/dashboardApi";
import { toast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateDashboardMutation,
  useGetAllDashboardsQuery,
  useUpdateDashboardMutation,
  useDeleteDashboardMutation,
  useShareDashboardMutation,
  useDeleteChartFromDashboardMutation,
  useDeleteDataframeFromDashboardMutation,
} from "@/store/services/dashboardApi";
import DashboardDialog from "./components/DashboardDialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { PageHeader } from "@/components/common/PageHeader";
import { v4 as uuidv4 } from "uuid";
import { resetToInitialChatState } from "@/store/slices/chatSlice";
import { removeArtifacts } from "@/store/slices/artifactsSlice";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useTour } from "@/contexts/TourContext";
import { useGetTourGuideQuery } from "@/store/services/userApi";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ShareDashboardDialog } from "./components/ShareDashboardDialog";
import { cn } from "@/lib/utils";
import { DataTableDialog } from "@/components/table/DataTableDialog";
import {
  DataContent,
  ColumnsContent,
  MetadataContent,
} from "@/app/(protected)/chat/types/chat";
import { useTranslations } from "next-intl";
import { useTheme } from "@/contexts/ThemeContext";

const GridLayout = WidthProvider(ResponsiveGridLayout);

interface DashboardItem {
  id: string;
  type: "chart" | "table";
  content: string;
  title: string;
  description?: string;
  chartData?: any;
}

const Dashboard = () => {
  const t = useTranslations("dashboard");
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isMobile, setIsMobile] = useState(false);
  const { startTour } = useTour();
  const { data: tourGuideState } = useGetTourGuideQuery();
  const { theme } = useTheme();

  useEffect(() => {
    if (tourGuideState) {
      startTour("dashboard");
    }
  }, [startTour, tourGuideState]);
  // Add useEffect for mobile check
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    // Check initially
    checkMobile();

    // Add event listener for resize
    window.addEventListener("resize", checkMobile);

    // Cleanup
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Get dashboardId from either path params or query params
  const dashboardId = searchParams?.get("dashboard");
  const dispatch = useDispatch();

  // Add state to track previous path
  const [previousPath, setPreviousPath] = useState<string | null>(null);

  const {
    data: dashboards,
    isLoading: isLoadingDashboards,
    refetch,
    isFetching: isFetchingDashboards,
  } = useGetAllDashboardsQuery();

  // Replace currentDashboard from Redux with local state
  const [selectedDashboard, setSelectedDashboard] =
    useState<DashboardType | null>(null);

  // Skip the query if dashboardId is null or undefined
  const { data: dashboard, isLoading: isLoadingDashboard } =
    useGetDashboardByIdQuery(dashboardId as string, {
      skip: !dashboardId,
    });

  const charts = selectedDashboard?.charts ?? [];
  const [layouts, setLayouts] = useState<Layouts>({});
  const [dimensions, setDimensions] = useState<{
    [key: string]: { width: number; height: number };
  }>({});
  const [containerHeight, setContainerHeight] = useState(800);
  const [isLayoutLocked, setIsLayoutLocked] = useState(false);
  const [newDashboardName, setNewDashboardName] = useState("");
  const [newDashboardDescription, setNewDashboardDescription] = useState("");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editDashboardName, setEditDashboardName] = useState("");
  const [editDashboardDescription, setEditDashboardDescription] = useState("");
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<
    Array<{ user_id: string; permission: "view" | "edit" }>
  >([]);
  const [refreshKey, setRefreshKey] = useState(0);

  // Simulate fetching dashboards from an API
  const dashboardsStore = useSelector(
    (state: RootState) => state.dashboard.dashboards
  );

  const [createDashboard, { isLoading: isCreatingDashboard }] =
    useCreateDashboardMutation();

  const [updateDashboard, { isLoading: isUpdatingDashboard }] =
    useUpdateDashboardMutation();

  const [deleteDashboard, { isLoading: isDeletingDashboard }] =
    useDeleteDashboardMutation();

  const [shareDashboard, { isLoading: isSharingDashboardLoading }] =
    useShareDashboardMutation();

  const [deleteChartFromDashboard] = useDeleteChartFromDashboardMutation();
  const [deleteDataframeFromDashboard] =
    useDeleteDataframeFromDashboardMutation();

  const [chartToDelete, setChartToDelete] = useState<{
    id: string;
    type: "chart" | "table";
  } | null>(null);

  const [parsedItems, setParsedItems] = useState<DashboardItem[]>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTableContent, setSelectedTableContent] = useState<{
    content: any;
    columnsContent?: string | ColumnsContent;
    metadataContent?: MetadataContent;
  } | null>(null);

  const [
    triggerRefreshDashboard,
    { data: refreshedDashboard, isLoading: isRefreshingDashboard },
  ] = useLazyRefreshDashboardQuery();

  // Refresh the dashboard and refetch the data of dashboards
  const handleRefreshDashboard = async () => {
    if (selectedDashboard?.dashboard_id) {
      await triggerRefreshDashboard(selectedDashboard.dashboard_id).unwrap();
      await refetch();
      toast({
        title: t("dashboardRefreshedSuccessfully"),
        description: t("dashboardRefreshedSuccessfullyDescription"),
      });
    }
  };

  useEffect(() => {
    if (selectedDashboard?.charts || selectedDashboard?.dataframes) {
      // Parse charts
      const charts =
        selectedDashboard.charts?.map((chart: any) => ({
          id: chart.id,
          type: "chart" as const,
          content: chart.chart_schema,
          title: chart.title,
          description: chart.description,
          chartData: chart.chart_data,
        })) || [];

      // Parse tables
      const tables =
        selectedDashboard.dataframes?.map((table: any) => ({
          id: table.dataframe_id,
          type: "table" as const,
          content: table.content,
          title: table.title || t("untitledTable"),
          description: table.description,
        })) || [];

      setParsedItems([...charts, ...tables]);

      // Force a refresh when items are first loaded
      setTimeout(() => {
        setRefreshKey((prev) => prev + 1);
      }, 1000);
    } else {
      setParsedItems([]);
    }
  }, [selectedDashboard]);

  useEffect(() => {
    // Handle dashboard selection from URL parameter or dashboard updates
    if (dashboardId && dashboards && dashboards.length > 0) {
      // Find dashboard by ID from URL parameter
      const dashboard = dashboards.find(
        (d: DashboardType) => d.dashboard_id === dashboardId
      );
      // Only update if dashboard exists and is different from current selection
      // This prevents infinite loops by avoiding unnecessary state updates
      if (
        dashboard &&
        dashboard.dashboard_id !== selectedDashboard?.dashboard_id
      ) {
        setSelectedDashboard(dashboard);
      }
    } else if (
      !dashboardId &&
      selectedDashboard &&
      dashboards &&
      dashboards.length > 0
    ) {
      // Update selected dashboard if it has been modified (e.g., after API updates)
      const updatedDashboard = dashboards.find(
        (d: DashboardType) => d.dashboard_id === selectedDashboard.dashboard_id
      );
      // Only update if the dashboard data has actually changed
      // JSON comparison prevents unnecessary re-renders when data is the same
      if (
        updatedDashboard &&
        JSON.stringify(updatedDashboard) !== JSON.stringify(selectedDashboard)
      ) {
        setSelectedDashboard(updatedDashboard);
      }
    }
  }, [dashboardId, dashboards]);

  useEffect(() => {
    // Fallback to Redux store dashboards if API dashboards are not available
    if (
      dashboardsStore.length > 0 &&
      !selectedDashboard &&
      !dashboards?.length
    ) {
      // Only set from store if no API dashboards are available and no dashboard is selected
      // This prevents conflicts between API data and store data
      const storeDashboard = dashboardsStore[0];
      if (storeDashboard) {
        setSelectedDashboard(storeDashboard);
      }
    }
  }, [dashboardsStore, selectedDashboard, dashboards]);

  useEffect(() => {
    if (selectedDashboard) {
      setEditDashboardName(selectedDashboard.title);
      setEditDashboardDescription(selectedDashboard.description || "");
    }
  }, [selectedDashboard]);

  // Add effect to capture previous path from localStorage on component mount
  useEffect(() => {
    // Get the previous path from localStorage (will be set by navigation)
    const prevPath = localStorage.getItem("previousPath");
    setPreviousPath(prevPath);

    // Store current path for future reference
    const currentPath = window.location.pathname;
    localStorage.setItem("previousPath", currentPath);
  }, []);

  useEffect(() => {
    // Handle individual dashboard fetch (when accessing via direct URL)
    if (
      dashboard &&
      dashboard.dashboard_id !== selectedDashboard?.dashboard_id
    ) {
      // Only update if the fetched dashboard is different from current selection
      // Prevents unnecessary re-renders when the same dashboard is fetched
      setSelectedDashboard(dashboard);
    }
  }, [dashboard, selectedDashboard?.dashboard_id]);

  const handleDashboardChange = (dashboardId: string) => {
    // Early return if invalid parameters to prevent unnecessary processing
    if (!dashboardId || !dashboards?.length) {
      return;
    }

    // Find the dashboard by ID
    const dashboard = dashboards.find(
      (d: DashboardType) => d.dashboard_id === dashboardId
    );

    // Only update if dashboard exists and is different from current selection
    // This prevents infinite loops when the same dashboard is selected repeatedly
    if (
      dashboard &&
      dashboard.dashboard_id !== selectedDashboard?.dashboard_id
    ) {
      setSelectedDashboard(dashboard);
      if (dashboard.layouts) {
        setLayouts(dashboard.layouts);
      }
    }
  };

  useEffect(() => {
    // Early return to prevent layout calculations when data is not ready
    // This prevents infinite loops during initial loading or when switching dashboards
    if (
      !selectedDashboard ||
      !selectedDashboard.dashboard_id ||
      parsedItems.length === 0
    ) {
      return;
    }
    // Wait for the dashboard to be loaded before loading the layouts
    setTimeout(() => {
      // Load saved layouts if they exist.
      if (
        selectedDashboard.layouts &&
        Object.keys(selectedDashboard.layouts).length > 0
      ) {
        // Check if there are new charts that aren't in the layout
        const existingChartIds = selectedDashboard.layouts.lg.map(
          (item: any) => item.i
        );
        const newItems = parsedItems.filter(
          (item: DashboardItem) => !existingChartIds.includes(item.id)
        );

        if (newItems.length > 0) {
          // There are new charts to add to the layout
          // Create a deep copy of the layouts object to ensure it's extensible
          const currentLayouts = JSON.parse(
            JSON.stringify(selectedDashboard.layouts)
          );

          // Find the bottom-most position in the current layout
          let maxY = 0;
          if (currentLayouts.lg && currentLayouts.lg.length > 0) {
            currentLayouts.lg.forEach((item: any) => {
              const bottomY = item.y + item.h;
              maxY = Math.max(maxY, bottomY);
            });
          }

          // Add each new chart to the layout at the bottom
          newItems.forEach((item: DashboardItem, index: number) => {
            const newItem = {
              i: item.id,
              x: (index * 4) % 12, // Position horizontally based on index
              y: maxY, // Position below existing charts
              w: 4, // Good default width (1/3 of the grid)
              h: 4, // Good default height
              minW: 2,
              minH: 2,
              maxW: undefined,
              maxH: undefined,
              isBounded: undefined,
              isDraggable: undefined,
              isResizable: undefined,
              static: false,
              moved: false,
              resizeHandles: undefined,
              chartData: item.chartData,
            };

            // Add to all breakpoint layouts
            ["lg", "md", "sm"].forEach((breakpoint) => {
              if (!currentLayouts[breakpoint]) {
                currentLayouts[breakpoint] = [];
              }
              currentLayouts[breakpoint].push(newItem);
            });
          });

          // Update the layouts state
          setLayouts(currentLayouts);

          // Calculate dimensions for all charts including new ones
          const newDimensions: {
            [key: string]: { width: number; height: number };
          } = {};

          let maxHeight = 0;
          currentLayouts.lg.forEach((item: any) => {
            const width = item.w * (1200 / 12) - 48;
            const height = item.h * 100 - 80;
            newDimensions[item.i] = { width, height };

            const bottomPosition = (item.y + item.h) * 100 + 32;
            maxHeight = Math.max(maxHeight, bottomPosition);
          });

          setDimensions(newDimensions);
          setContainerHeight(Math.max(1200, maxHeight));

          // Save the updated layout
          dispatch(
            updateLayout({
              dashboardId: dashboardId as string,
              layouts: currentLayouts,
            })
          );

          // Force a refresh after dimensions are set
          setTimeout(() => {
            setRefreshKey((prev) => prev + 1);
          }, 200);

          // Also save to the server
          updateDashboard({
            dashboardId: selectedDashboard.dashboard_id,
            data: {
              ...selectedDashboard,
              layouts: currentLayouts,
            },
          });
        } else {
          // No new charts, just use the existing layout
          setLayouts(selectedDashboard.layouts);
          // Calculate initial dimensions for the saved layout
          if (selectedDashboard.layouts.lg) {
            const newDimensions: {
              [key: string]: { width: number; height: number };
            } = {};
            let maxHeight = 0;

            selectedDashboard.layouts.lg.forEach((item: any) => {
              const width = item.w * (1200 / 12) - 48;
              const height = item.h * 100 - 80;
              newDimensions[item.i] = { width, height };

              const bottomPosition = (item.y + item.h) * 100 + 32;
              maxHeight = Math.max(maxHeight, bottomPosition);
            });

            setDimensions(newDimensions);
            setContainerHeight(Math.max(1200, maxHeight));

            // Force a refresh after dimensions are set
            setTimeout(() => {
              setRefreshKey((prev) => prev + 1);
            }, 100);
          }
        }
      } else {
        // Create default layout only if no saved layout exists
        const newLayout = parsedItems.map(
          (item: DashboardItem, index: number) => ({
            i: item.id,
            x: (index * 4) % 12,
            y: Math.floor(index / 3) * 4,
            w: 4,
            h: 3,
            minW: 2,
            minH: 2,
            maxW: undefined,
            maxH: undefined,
            isBounded: undefined,
            isDraggable: undefined,
            isResizable: undefined,
            static: false,
            moved: false,
            resizeHandles: undefined,
            chartData: item.chartData,
          })
        );
        const initialLayouts = { lg: newLayout, md: newLayout, sm: newLayout };
        setLayouts(initialLayouts);

        // Calculate initial dimensions for the default layout
        const newDimensions: {
          [key: string]: { width: number; height: number };
        } = {};

        newLayout.forEach((item: any) => {
          const width = item.w * (1200 / 12) - 48;
          const height = item.h * 100 - 80;
          newDimensions[item.i] = { width, height };
        });

        setDimensions(newDimensions);

        // Force a refresh after dimensions are set
        setTimeout(() => {
          setRefreshKey((prev) => prev + 1);
        }, 200);

        dispatch(
          updateLayout({
            dashboardId: dashboardId as string,
            layouts: initialLayouts,
          })
        );
      }
    });
  }, [selectedDashboard?.dashboard_id, charts, dashboardId]); // Add updateDashboard to dependencies

  useEffect(() => {
    const handleResize = () => {
      const newIsMobile = window.innerWidth < 768;
      setIsLayoutLocked(newIsMobile);
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleRemoveChart = (id: string, type: "chart" | "table") => {
    setChartToDelete({ id, type });
  };

  const handleDeleteChart = async () => {
    if (!chartToDelete || !selectedDashboard) return;

    try {
      if (chartToDelete.type === "chart") {
        const result = await deleteChartFromDashboard({
          dashboardId: selectedDashboard.dashboard_id,
          chartId: chartToDelete.id,
        }).unwrap();

        if (result) {
          // Update the local state by filtering out the deleted chart
          if (selectedDashboard) {
            setSelectedDashboard({
              ...selectedDashboard,
              charts: selectedDashboard.charts.filter(
                (chart) => chart.id !== chartToDelete.id
              ),
            });
          }
        }
      } else {
        const result = await deleteDataframeFromDashboard({
          dashboardId: selectedDashboard.dashboard_id,
          dataframeId: chartToDelete.id,
        }).unwrap();

        if (result) {
          // Update the local state by filtering out the deleted dataframe
          if (selectedDashboard) {
            setSelectedDashboard({
              ...selectedDashboard,
              dataframes: selectedDashboard.dataframes?.filter(
                (df) => df.dataframe_id !== chartToDelete.id
              ),
            });
          }
        }
      }

      // Update parsed items state
      setParsedItems((prevItems) =>
        prevItems.filter((item) => item.id !== chartToDelete.id)
      );

      // Update layouts by removing the deleted item's layout
      setLayouts((prevLayouts) => {
        const newLayouts = { ...prevLayouts };
        Object.keys(newLayouts).forEach((breakpoint) => {
          newLayouts[breakpoint] = newLayouts[breakpoint].filter(
            (item: any) => item.i !== chartToDelete.id
          );
        });
        return newLayouts;
      });

      // Update dimensions by removing the deleted item's dimensions
      setDimensions((prevDimensions) => {
        const newDimensions = { ...prevDimensions };
        delete newDimensions[chartToDelete.id];
        return newDimensions;
      });

      toast({
        title: t(
          `${chartToDelete.type === "chart" ? "chart" : "table"}Deleted`
        ),
        description: t(
          `${
            chartToDelete.type === "chart" ? "chart" : "table"
          }hasbeensuccessfullydeleted.`
        ),
      });
      setChartToDelete(null);
    } catch (error) {
      console.error("Failed to delete item:", error);
      toast({
        title: t(
          `${chartToDelete.type === "chart" ? "chart" : "table"}FailedToDelete`
        ),
        description: t(
          `${
            chartToDelete.type === "chart"
              ? "deleteChartError"
              : "deleteTableError"
          }`
        ),
        variant: "destructive",
      });
    }
  };

  const handleLayoutChange = useCallback(
    (layout: any, newLayouts: any) => {
      // Handle grid layout changes and update component dimensions
      // This callback is memoized to prevent unnecessary re-renders

      // Update dimensions and container height
      const newDimensions: {
        [key: string]: { width: number; height: number };
      } = {};
      let maxHeight = 0;

      layout.forEach((item: any) => {
        // Calculate width based on grid cell width (1200/12 = 100 per cell)
        const width = item.w * (1200 / 12) - 48; // Account for padding/margins

        // Calculate height based on row height (100 per row)
        // Subtract header height (approx 40px) and padding
        const height = item.h * 100 - 60;

        newDimensions[item.i] = { width, height };

        const bottomPosition = (item.y + item.h) * 100 + 32;
        maxHeight = Math.max(maxHeight, bottomPosition);
      });

      // Batch state updates to prevent multiple re-renders
      setDimensions(newDimensions);
      setContainerHeight(Math.max(1200, maxHeight));
      setLayouts(newLayouts);

      // Debounce the layout save to reduce frequent state updates
      // Only save if we have a valid dashboard selected
      if (selectedDashboard?.dashboard_id) {
        dispatch(
          updateLayout({
            dashboardId: selectedDashboard.dashboard_id,
            layouts: newLayouts,
          })
        );
      }
    },
    [selectedDashboard, dispatch]
  );

  const handleCreateDashboard = async () => {
    if (!newDashboardName.trim()) {
      toast({
        title: t("dashboardNameRequired"),
        description: t("pleaseEnterNameForDashboard"),
        variant: "destructive",
      });
      return;
    }

    try {
      // Make API call to create dashboard
      const result = await createDashboard({
        title: newDashboardName,
        description: newDashboardDescription,
      }).unwrap();

      // Add the dashboard to the Redux store
      // dispatch(createDashboardAction(result));
      refetch();
      // Update UI state
      setSelectedDashboard(result);
      setNewDashboardName("");
      setIsAddDialogOpen(false);
      setParsedItems([]);

      toast({
        title: t("dashboardCreated"),
        description: `"${newDashboardName}" ${t("hasBeenCreatedSuccessfully")}`,
      });
    } catch (error) {
      console.error("Failed to create dashboard:", error);
      toast({
        title: t("failedToCreateDashboard"),
        description: t("thereWasAnErrorCreatingYourDashboardPleaseTryAgain"),
        variant: "destructive",
      });
    }
  };

  const handleUpdateDashboard = async () => {
    if (!editDashboardName.trim() || !selectedDashboard) {
      toast({
        title: t("dashboardNameRequired"),
        description: t("pleaseEnterNameForDashboard"),
        variant: "destructive",
      });
      return;
    }

    try {
      // Call the API to update the dashboard
      await updateDashboard({
        dashboardId: selectedDashboard.dashboard_id,
        data: {
          ...selectedDashboard,
          title: editDashboardName,
          description: editDashboardDescription,
        },
      }).unwrap();

      setIsEditDialogOpen(false);

      toast({
        title: t("dashboardUpdated"),
        description: `"${editDashboardName}" ${t(
          "hasBeenUpdatedSuccessfully"
        )}`,
      });
    } catch (error) {
      console.error("Failed to update dashboard:", error);
      toast({
        title: t("failedToUpdateDashboard"),
        description: t("thereWasAnErrorUpdatingYourDashboardPleaseTryAgain"),
        variant: "destructive",
      });
    }
  };

  const handleDeleteDashboard = async () => {
    if (!selectedDashboard) return;

    try {
      // Call the API to delete the dashboard
      await deleteDashboard(selectedDashboard.dashboard_id).unwrap();

      refetch();

      // Close the dialog
      setIsDeleteDialogOpen(false);

      // If there are other dashboards, select the first one
      if (dashboards && dashboards.length > 1) {
        const remainingDashboards = dashboards.filter(
          (d) => d.dashboard_id !== selectedDashboard.dashboard_id
        );
        setSelectedDashboard(remainingDashboards[0]);
      } else {
        setSelectedDashboard(null);
      }

      toast({
        title: t("dashboardDeleted"),
        description: `"${selectedDashboard.title}" ${t(
          "hasBeenDeletedSuccessfully"
        )}`,
      });
    } catch (error) {
      console.error("Failed to delete dashboard:", error);
      toast({
        title: t("failedToDeleteDashboard"),
        description: t("thereWasAnErrorDeletingYourDashboardPleaseTryAgain"),
        variant: "destructive",
      });
    }
  };

  const handleSaveLayout = async () => {
    if (!selectedDashboard) {
      toast({
        title: t("noDashboardSelected"),
        description: t("pleaseSelectADashboardToSaveTheLayout"),
        variant: "destructive",
      });
      return;
    }

    try {
      // Call the API to update the dashboard with the current layouts
      await updateDashboard({
        dashboardId: selectedDashboard.dashboard_id,
        data: {
          ...selectedDashboard,
          layouts: layouts,
        },
      }).unwrap();

      toast({
        title: t("layoutSaved"),
        description: t("dashboardLayoutHasBeenSavedSuccessfully"),
      });
    } catch (error) {
      console.error("Failed to save dashboard layout:", error);
      toast({
        title: t("failedToSaveLayout"),
        description: t(
          "thereWasAnErrorSavingYourDashboardLayoutPleaseTryAgain"
        ),
        variant: "destructive",
      });
    }
  };

  // Add a useEffect to trigger a refresh when the component mounts
  useEffect(() => {
    // Initial refresh
    setRefreshKey((prev) => prev + 1);

    // Secondary refresh after a delay to ensure charts render correctly
    const timer = setTimeout(() => {
      setRefreshKey((prev) => prev + 1);
    }, 500);

    return () => clearTimeout(timer);
  }, []);

  // Add this effect to handle automatic selection of first dashboard
  useEffect(() => {
    // Auto-select first dashboard only when specific conditions are met
    if (
      dashboards &&
      dashboards.length > 0 &&
      !selectedDashboard &&
      !dashboardId
    ) {
      // Only auto-select if no dashboard is specified in the URL and no dashboard is currently selected
      // This prevents conflicts with URL-based dashboard selection
      const firstDashboard = dashboards[0];
      if (firstDashboard && firstDashboard.dashboard_id) {
        handleDashboardChange(firstDashboard.dashboard_id);
      }
    }
  }, [dashboards, selectedDashboard, dashboardId]);

  const handleGoToAnalyticsChat = () => {
    dispatch(resetToInitialChatState());
    dispatch(removeArtifacts());
    const newUid = uuidv4();
    router.push(`/chat/analytics/${newUid}`);
  };

  // Reset selected users when dialog closes
  useEffect(() => {
    if (!isShareDialogOpen) {
      setSelectedUsers([]);
    }
  }, [isShareDialogOpen]);

  const handleShareDashboard = async () => {
    if (!selectedDashboard) return;

    const users = selectedUsers.map((user) => ({
      user_id: user.user_id,
      permission: user.permission,
    }));

    // if (users.length === 0) {
    //   toast({
    //     title: t("noUsersSelected"),
    //     description: t("pleaseSelectAtLeastOneUserToShareWith"),
    //     variant: "destructive",
    //   });
    //   return;
    // }

    try {
      // Wait for the API call to complete
      const result = await shareDashboard({
        dashboardId: selectedDashboard.dashboard_id,
        users,
      }).unwrap();

      // Only proceed with UI updates after successful API response
      if (result) {
        setIsShareDialogOpen(false);
        setSelectedUsers([]);

        toast({
          title: t("dashboardShared"),
          // description: `Dashboard "${selectedDashboard.title}" ${t(
          //   "hasBeenSharedSuccessfully"
          // )}`,
          description: t("hasBeenSharedSuccessfully", {
            dashboardTitle: selectedDashboard.title,
          }),
        });
      }
    } catch (error) {
      console.error("Failed to share dashboard:", error);
      toast({
        title: t("failedToShareDashboard"),
        description: t("thereWasAnErrorSharingYourDashboardPleaseTryAgain"),
        variant: "destructive",
      });
    }
  };

  const handleUserPermissionChange = (
    userId: string,
    permission: "view" | "edit"
  ) => {
    setSelectedUsers((prev) => {
      // Remove existing entry for this user if it exists
      const filtered = prev.filter((user) => user.user_id !== userId);
      const currentUser = prev.find((user) => user.user_id === userId);
      if (currentUser?.permission === permission) {
        return [...filtered];
      }
      // Add new entry with updated permission
      return [...filtered, { user_id: userId, permission }];
    });
  };

  // const handleUserSelectionChange = (userId: string, checked: boolean) => {
  //   if (checked) {
  //     setSelectedUsers((prev) => [
  //       ...prev,
  //       { user_id: userId, permission: "view" },
  //     ]);
  //   } else {
  //     setSelectedUsers((prev) =>
  //       prev.filter((user) => user.user_id !== userId)
  //     );
  //   }
  // };

  const handleTableClick = (item: DashboardItem) => {
    try {
      let parsedData: any[] = [];
      const content = item.content;

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

      setSelectedTableContent({
        content: parsedData,
        columnsContent: JSON.stringify(
          parsedData.length > 0
            ? Object.keys(parsedData[0]).map((key) => ({
                name: key,
                display_name: key,
                type: "string",
                icon: "text",
                sortable: true,
                filterable: true,
                sample_values: [],
              }))
            : []
        ),
      });
      setIsModalOpen(true);
    } catch (error) {
      console.error("Error parsing table content:", error);
      // Fallback to raw content if parsing fails
      setSelectedTableContent({
        content: item.content,
      });
      setIsModalOpen(true);
    }
  };

  const handleBlockBackgroung = useMemo(() => {
    if (theme === "dark") {
      if (isLayoutLocked) {
        return "bg-muted-foreground/10";
      }
      return "bg-muted-foreground/20";
    } else {
      return "bg-background";
    }
  }, [isLayoutLocked, theme]);

  // Move the mobile check after all hooks
  if (isMobile) {
    return (
      <div className="p-6 mx-auto">
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <h2 className="text-xl font-semibold mb-2">
              {t("desktopExperienceRecommended")}
            </h2>
            <p className="text-muted-foreground mb-4">
              {t("theDashboardFeatureIsOptimizedForLargerScreensPlease")}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Add safeguard to prevent infinite loops when loading
  // This prevents the component from rendering and causing state update loops
  // when dashboards are still being fetched from the API
  if (isLoadingDashboards && !dashboards) {
    return (
      <div className="p-6 mx-auto">
        <Card className="border-dashed bg-card text-card-foreground transition-colors duration-100">
          <CardContent className="flex flex-col items-center justify-center py-12 min-h-[500px]">
            <LoadingSpinner size={26} />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 mx-auto dashboard-tour-start mb-20">
      {/* Back button section */}
      {previousPath?.includes("/chat/analytics") && (
        <div className="flex justify-between items-center">
          <Button
            variant="outline"
            size="icon"
            onClick={() => router.back()}
            className="h-10 w-10 mb-4"
            title="Go back"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </div>
      )}
      <div className="flex flex-col items-center w-full">
        {/* Replace the existing header with PageHeader */}
        <PageHeader
          title={t("dashboard")}
          // className="max-w-7xl"
          className="w-full max-w-7xl lg:px-16"
          description={
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {t("visualizeAndOrganizeYourDataInsights")}
              </p>
            </div>
          }
          isLoading={
            isLoadingDashboard || isLoadingDashboards || isFetchingDashboards
          }
          actions={
            <div className="flex gap-2">
              <TooltipProvider>
                {selectedDashboard?.dashboard_id && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="inline-block">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => handleRefreshDashboard()}
                          title={t("refreshDashboard")}
                          className="w-10 h-10"
                          disabled={isRefreshingDashboard}
                        >
                          <RefreshCcw
                            className={cn(
                              "h-4 w-4 cursor-pointer",
                              isRefreshingDashboard && "animate-spin"
                            )}
                          />
                        </Button>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t("refreshDashboard")}</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </TooltipProvider>
              <Select
                value={selectedDashboard?.dashboard_id || ""}
                onValueChange={(value) => handleDashboardChange(value)}
              >
                <SelectTrigger className="w-64 text-xl font-medium focus:ring-0 text-md dashboard-dropdown">
                  <SelectValue
                    placeholder={t("selectDashboard")}
                    // className="text-sm"
                  />
                </SelectTrigger>
                <SelectContent>
                  {isLoadingDashboards || isFetchingDashboards ? (
                    <SelectItem value="none" disabled>
                      {t("loadingDashboards")}
                    </SelectItem>
                  ) : dashboards && dashboards?.length > 0 ? (
                    dashboards.map((dashboard: DashboardType) => (
                      <SelectItem
                        key={dashboard.dashboard_id}
                        value={dashboard.dashboard_id}
                      >
                        {dashboard.title}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="none" disabled>
                      {t("noDashboardsAvailable")}
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>

              <TooltipProvider>
                {selectedDashboard && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="inline-block">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => setIsEditDialogOpen(true)}
                          title={t("editDashboard")}
                          className="w-10 h-10"
                        >
                          <Edit className="h-4 w-4 cursor-pointer" />
                        </Button>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t("editDashboard")}</p>
                    </TooltipContent>
                  </Tooltip>
                )}

                {selectedDashboard && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="inline-block">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => setIsDeleteDialogOpen(true)}
                          title={t("deleteDashboard")}
                          className="w-10 h-10 text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 className="h-4 w-4 cursor-pointer" />
                        </Button>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t("deleteDashboard")}</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </TooltipProvider>

              <DashboardDialog
                isOpen={isAddDialogOpen}
                onOpenChange={setIsAddDialogOpen}
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
                trigger={
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div>
                          <Button
                            variant="outline"
                            size="icon"
                            className="w-10 h-10"
                            onClick={() => setIsAddDialogOpen(true)}
                          >
                            <Plus className="h-4 w-4 cursor-pointer" />
                          </Button>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{t("createNewDashboard")}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                }
                isLoading={isCreatingDashboard}
              />

              {selectedDashboard && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="inline-block">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => {
                            setIsShareDialogOpen(true);
                          }}
                          className="h-10 w-10"
                        >
                          <Share className="h-4 w-4 cursor-pointer" />
                        </Button>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t("shareDashboard")}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="inline-block">
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => setIsLayoutLocked(!isLayoutLocked)}
                        className="h-10 w-10"
                        title={
                          isLayoutLocked ? t("unlockLayout") : t("lockLayout")
                        }
                      >
                        {isLayoutLocked ? (
                          <Lock className="h-4 w-4 cursor-pointer" />
                        ) : (
                          <Unlock className="h-4 w-4 cursor-pointer" />
                        )}
                      </Button>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>
                      {isLayoutLocked ? t("unlockLayout") : t("lockLayout")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {/* Save Layout Button */}
              <Button
                size="icon"
                onClick={handleSaveLayout}
                className="h-10 w-28 dashboard-save"
                title={t("saveLayout")}
                disabled={isUpdatingDashboard}
              >
                {isUpdatingDashboard ? (
                  <Hourglass className="h-4 w-4 mr-2 cursor-pointer" />
                ) : (
                  <Save className="h-4 w-4 mr-2 cursor-pointer" />
                )}
                <label className="text-sm cursor-pointer">
                  {isUpdatingDashboard ? t("saving") : t("save")}
                </label>
              </Button>
            </div>
          }
        />
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground"></span>
          </div>
        </div>
      </div>

      <div className="mt-6 dashboard-edit">
        {!parsedItems?.length ? (
          isLoadingDashboards || isFetchingDashboards ? (
            <Card className="border-dashed bg-card text-card-foreground transition-colors duration-100">
              <CardContent className="flex flex-col items-center justify-center py-12 min-h-[500px]">
                <LoadingSpinner size={26} />
              </CardContent>
            </Card>
          ) : (
            <Card className="border-dashed bg-card text-card-foreground transition-colors duration-100">
              <CardContent className="flex flex-col items-center justify-center py-12 min-h-[500px]">
                <p className="mb-4">
                  {t("noChartsAvailablePleaseAddChartsFromTheAnalyticsChat")}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleGoToAnalyticsChat}
                  className="mt-2"
                >
                  {t("goToAnalyticsChat")}
                </Button>
              </CardContent>
            </Card>
          )
        ) : (
          <div>
            <GridLayout
              className="layout"
              layouts={layouts}
              cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
              rowHeight={100}
              width={1200}
              margin={[16, 16]}
              containerPadding={[5, 5]}
              isResizable={!isLayoutLocked}
              isDraggable={!isLayoutLocked}
              onLayoutChange={handleLayoutChange}
              transformScale={1}
              useCSSTransforms={true}
              compactType="vertical"
              preventCollision={false}
              onResize={(layout, oldItem, newItem) => {
                // Only trigger refresh when resize is complete
                if (oldItem.w !== newItem.w || oldItem.h !== newItem.h) {
                  // Update dimensions in real-time during resize
                  setDimensions((prev) => ({
                    ...prev,
                    [newItem.i]: {
                      width: newItem.w * (1200 / 12) - 48,
                      height: newItem.h * 100 - 60,
                    },
                  }));
                }
              }}
              onResizeStop={() => {
                setRefreshKey((prev) => prev + 1);
              }}
              onDragStop={() => {
                setRefreshKey((prev) => prev + 1);
              }}
              style={{
                border: cn(
                  "1px hsl(var(--border))",
                  isLayoutLocked ? "solid" : "dashed"
                ),
                borderRadius: "16px",
                minHeight: `${containerHeight}px`,
                background: isLayoutLocked
                  ? ""
                  : "hsl(var(--muted-foreground)/0.1)",
                transition: "background-color 0.1s ease-in-out",
              }}
            >
              {parsedItems.map((item: DashboardItem) => (
                <div key={item.id} className="h-full w-full dashboard-edit">
                  <Card
                    className={cn(
                      `h-full w-full overflow-hidden p-1 rounded-xl flex flex-col text-card-foreground transition-colors duration-100`,
                      handleBlockBackgroung
                    )}
                    style={{ transition: "width 0.2s, height 0.2s" }}
                  >
                    <CardContent
                      className={cn(
                        "w-full p-2 flex-grow flex flex-col overflow-hidden"
                        // item.type === "table" && "overflow-auto"
                      )}
                      style={{ transition: "all 0.2s ease" }}
                    >
                      <div className="flex flex-row w-full justify-end min-w-fit mb-2">
                        <div className="flex flex-row gap-3">
                          {item.type === "table" && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <div className="inline-block">
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => handleTableClick(item)}
                                      className="h-9 w-9 text-muted-foreground 
              hover:text-destructive bg-muted"
                                    >
                                      <Maximize2 className="w-4 h-4" />
                                    </Button>
                                  </div>
                                </TooltipTrigger>
                                <TooltipContent align="center">
                                  <p>{t("viewDataTable")}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() =>
                              handleRemoveChart(item.id, item.type)
                            }
                            className="h-9 w-9 text-muted-foreground 
              hover:text-destructive bg-muted"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      {item.type === "chart" ? (
                        <DashboardChart
                          key={`${item.id}-${refreshKey}`}
                          content={item.content}
                          chartData={item.chartData}
                          height={dimensions[item.id]?.height ?? 300}
                          width={dimensions[item.id]?.width ?? 400}
                          forceRender={refreshKey}
                        />
                      ) : (
                        <DashboardTable
                          key={`${item.id}-${refreshKey}`}
                          content={item.content}
                          height={dimensions[item.id]?.height ?? 300}
                          width={dimensions[item.id]?.width ?? 400}
                          forceRender={refreshKey}
                        />
                      )}
                    </CardContent>
                  </Card>
                </div>
              ))}
            </GridLayout>
          </div>
        )}
      </div>

      <DashboardDialog
        isOpen={isEditDialogOpen}
        onOpenChange={setIsEditDialogOpen}
        title={t("editDashboard")}
        description={t("updateYourDashboardDetails")}
        dashboardName={editDashboardName}
        dashboardDescription={editDashboardDescription}
        onDashboardNameChange={setEditDashboardName}
        onDashboardDescriptionChange={setEditDashboardDescription}
        onSubmit={handleUpdateDashboard}
        submitButtonText={t("updateDashboard")}
        isLoading={isUpdatingDashboard}
      />

      <AlertDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("areYouSureYouWantToDeleteTheDashboard")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("thisWillPermanentlyDeleteTheDashboard")}
              {selectedDashboard?.title}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteDashboard}
              className="bg-destructive hover:bg-destructive/90"
              disabled={isDeletingDashboard}
            >
              {isDeletingDashboard ? t("deleting") : t("deleteDashboard")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={chartToDelete !== null}
        onOpenChange={() => setChartToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("areYouSureYouWantToDeleteTheChart")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t(
                `${
                  chartToDelete?.type === "chart"
                    ? "chartDeleteDescription"
                    : "tableDeleteDescription"
                }`
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setChartToDelete(null)}>
              {t("cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteChart}
              className="bg-destructive hover:bg-destructive/90"
            >
              {t("deleteChart")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <ShareDashboardDialog
        isOpen={isShareDialogOpen}
        onOpenChange={setIsShareDialogOpen}
        orgId={selectedDashboard?.org_id || ""}
        dashboardId={selectedDashboard?.dashboard_id || ""}
        selectedUsers={selectedUsers}
        onUserPermissionChange={handleUserPermissionChange}
        onShare={handleShareDashboard}
        isSharingDashboardLoading={isSharingDashboardLoading}
        setSelectedUsers={setSelectedUsers}
      />

      <DataTableDialog
        isOpen={isModalOpen}
        onOpenChange={setIsModalOpen}
        content={selectedTableContent?.content || {}}
        columnsContent={
          selectedTableContent?.columnsContent
            ? JSON.parse(selectedTableContent.columnsContent as string)
            : undefined
        }
        metadataContent={selectedTableContent?.metadataContent}
      />
    </div>
  );
};

export default Dashboard;
