import {
  DataContent,
  MetadataContent,
  ColumnsContent,
} from "../../../types/chat";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  TooltipProvider,
  TooltipContent,
  TooltipTrigger,
  Tooltip,
} from "@/components/ui/tooltip";
import {
  LayoutDashboard,
  Maximize2,
  Download,
  ArrowRight,
  ArrowUpRight,
} from "lucide-react";
import { useState, useRef } from "react";
import {
  useGetAllDashboardsQuery,
  useAddDataframeToDashboardMutation,
  useCreateDashboardMutation,
} from "@/store/services/dashboardApi";
import { AddToDashboardDialog } from "@/components/dashboard/AddToDashboardDialog";
import DashboardDialog from "@/app/(protected)/dashboard/components/DashboardDialog";
import { useRouter } from "next/navigation";
import { DataTable, DataTableDialog } from "@/components/table";
import { useTranslations } from "next-intl";
import { toast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import { cn, thinHorizontalScrollbar } from "@/lib/utils";

interface AnalyticsDataArtifactProps {
  content: DataContent;
  columnsContent?: ColumnsContent;
  metadataContent?: MetadataContent;
}

export const AnalyticsDataArtifact = ({
  content,
  columnsContent,
  metadataContent,
}: AnalyticsDataArtifactProps) => {
  const t = useTranslations("chatPage.analyticsPal.analyticsDataArtifact");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAddToDashboardDialogOpen, setIsAddToDashboardDialogOpen] =
    useState(false);
  const [isCreateDashboardDialogOpen, setIsCreateDashboardDialogOpen] =
    useState(false);
  const [newDashboardName, setNewDashboardName] = useState("");
  const [newDashboardDescription, setNewDashboardDescription] = useState("");
  const addToDashboardButtonRef = useRef<HTMLButtonElement>(null);
  const { data: dashboards, isLoading: isLoadingDashboards } =
    useGetAllDashboardsQuery();
  const [addDataframeToDashboard] = useAddDataframeToDashboardMutation();
  const [createDashboard] = useCreateDashboardMutation();
  const router = useRouter();
  const [isDashboardAdded, setIsDashboardAdded] = useState(false);

  // Helper function to format numbers with commas and 2 decimal places
  const formatNumber = (num: number) => {
    // return new Intl.NumberFormat("en-US", {
    //   minimumFractionDigits: 2,
    //   maximumFractionDigits: 2,
    // }).format(num);
    return new Intl.NumberFormat("en-US").format(num);
  };

  // Parse content if it's a string
  let parsedContent: any = content;
  if (typeof content === "string") {
    try {
      parsedContent = JSON.parse(content);
    } catch (e) {
      console.error("Error parsing data content:", e);
      return <div>Error parsing data content</div>;
    }
  }

  // Get results from parsed content
  const results = Array.isArray(parsedContent)
    ? parsedContent
    : parsedContent.results || [];

  // Get column headers from the first result object
  const columns = results.length > 0 ? Object.keys(results[0]) : [];

  // Parse columns content if it's a string
  let parsedColumnsContent: any[] = [];
  if (columnsContent) {
    if (typeof columnsContent === "string") {
      try {
        parsedColumnsContent = JSON.parse(columnsContent as string);
      } catch (e) {
        console.error("Error parsing columns content:", e);
      }
    } else {
      parsedColumnsContent = columnsContent as any;
    }
  }

  // Create a map of column names to display names
  const columnDisplayNames: Record<string, string> = {};
  if (parsedColumnsContent && Array.isArray(parsedColumnsContent)) {
    parsedColumnsContent.forEach((column: any) => {
      if (column.name && column.display_name) {
        columnDisplayNames[column.name] = column.display_name;
      }
    });
  } else if (metadataContent?.columns) {
    metadataContent.columns.forEach((column) => {
      columnDisplayNames[column.name] = column.display_name;
    });
  }

  const handleAddToDashboard = async (dashboardId: string) => {
    try {
      setIsDashboardAdded(true);
      await addDataframeToDashboard({
        dashboardId,
        data: {
          content: JSON.stringify(content),
          columns: JSON.stringify(columnsContent),
          metadata: JSON.stringify(metadataContent || {}),
        },
      }).unwrap();
      setIsDashboardAdded(false);
      setIsAddToDashboardDialogOpen(false);
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
      // Set the current path in local storage before navigating
      localStorage.setItem("previousPath", window.location.pathname);

      // router.push(`/dashboard?dashboard=${dashboardId}`);
    } catch (error) {
      console.error("Failed to add dataframe to dashboard:", error);
    }
  };

  const handleViewDashboard = (dashboardId: string) => {
    router.push(`/dashboard?dashboard=${dashboardId}`);
    // Set the current path in local storage before navigating
    localStorage.setItem("previousPath", window.location.pathname);
  };

  const handleCreateNewDashboard = async () => {
    if (!newDashboardName.trim()) return;

    try {
      const newDashboard = await createDashboard({
        title: newDashboardName,
        description: newDashboardDescription,
      }).unwrap();

      // Add the dataframe to the newly created dashboard
      await addDataframeToDashboard({
        dashboardId: newDashboard.dashboard_id,
        data: {
          content: JSON.stringify(content),
          columns: JSON.stringify(columnsContent),
          metadata: JSON.stringify(metadataContent || {}),
        },
      }).unwrap();

      // Close dialogs
      setIsCreateDashboardDialogOpen(false);
      setIsAddToDashboardDialogOpen(false);

      // Navigate to the new dashboard
      router.push(`/dashboard?dashboard=${newDashboard.dashboard_id}`);
    } catch (error) {
      console.error("Failed to create dashboard:", error);
    }
  };

  const handleDownloadCSV = () => {
    // Get the data in the correct format
    const data = Array.isArray(parsedContent)
      ? parsedContent
      : parsedContent.results || [];

    if (data.length === 0) return;

    // Get headers from the first row
    const headers = Object.keys(data[0]);

    // Create CSV content
    const csvContent = [
      // Add headers
      headers.map((header) => columnDisplayNames[header] || header).join(","),
      // Add data rows
      ...data.map((row: any) =>
        headers
          .map((header) => {
            const value = row[header];
            // Handle special formatting for numbers
            if (header === "volume" || header === "total_volume") {
              return formatNumber(value);
            }
            // Handle special formatting for city names
            if (header === "city" || header === "customer_city") {
              return value
                .split(" ")
                .map(
                  (word: string) => word.charAt(0).toUpperCase() + word.slice(1)
                )
                .join(" ");
            }
            // Handle special formatting for payment types
            if (header === "payment_type" || header === "payment_method") {
              return value
                .split("_")
                .map(
                  (word: string) => word.charAt(0).toUpperCase() + word.slice(1)
                )
                .join(" ");
            }
            // Escape commas and quotes in the value
            return `"${String(value).replace(/"/g, '""')}"`;
          })
          .join(",")
      ),
    ].join("\n");

    // Create blob and download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "data.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative w-full shadow-sm overflow-hidden">
      <div className="flex justify-end pb-3 gap-2">
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
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsModalOpen(true)}
                className="px-2"
              >
                <Maximize2 className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent align="center">
              <p>{t("viewDataTable")}</p>
            </TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadCSV}
                className="px-2"
              >
                <Download className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent align="center">
              <p>{t("downloadAsCSV")}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <div
        className={cn(
          "overflow-auto max-h-[300px]",
          thinHorizontalScrollbar(2)
        )}
      >
        <DataTable
          content={content}
          columnsContent={columnsContent}
          metadataContent={metadataContent}
        />
      </div>

      <AddToDashboardDialog
        isOpen={isAddToDashboardDialogOpen}
        onOpenChange={setIsAddToDashboardDialogOpen}
        dashboards={dashboards}
        isLoadingDashboards={isLoadingDashboards}
        onAddToDashboard={handleAddToDashboard}
        onCreateNewDashboard={() => {
          setIsAddToDashboardDialogOpen(false);
          setIsCreateDashboardDialogOpen(true);
        }}
        buttonRef={addToDashboardButtonRef}
        onViewDashboard={handleViewDashboard}
        isDashboardAdded={isDashboardAdded}
      />

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
        onSubmit={handleCreateNewDashboard}
        submitButtonText={t("createDashboard")}
        isLoading={false}
      />

      <DataTableDialog
        isOpen={isModalOpen}
        onOpenChange={setIsModalOpen}
        content={content}
        columnsContent={columnsContent}
        metadataContent={metadataContent}
      />

      <Toaster />
    </div>
  );
};
