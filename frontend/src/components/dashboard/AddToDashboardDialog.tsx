import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { ArrowUpRight, Check, Loader2, Plus } from "lucide-react";
import { Dashboard } from "@/store/services/dashboardApi";
import { useTranslations } from "next-intl";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "@/hooks/use-toast";

interface AddToDashboardDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  dashboards: Dashboard[] | undefined;
  isLoadingDashboards: boolean;
  onAddToDashboard: (dashboardId: string) => void;
  onCreateNewDashboard: () => void;
  buttonRef?: React.RefObject<HTMLButtonElement>;
  onViewDashboard: (dashboardId: string) => void;
  isDashboardAdded: boolean;
}

export const AddToDashboardDialog: React.FC<AddToDashboardDialogProps> = ({
  isOpen,
  onOpenChange,
  dashboards,
  isLoadingDashboards,
  onAddToDashboard,
  onCreateNewDashboard,
  onViewDashboard,
  buttonRef,
  isDashboardAdded,
}) => {
  const t = useTranslations("chatPage.analyticsPal.dashboardModal");
  const [loadingDashboardId, setLoadingDashboardId] = useState<string | null>(
    null
  );

  const handleAddToDashboard = (dashboardId: string) => {
    setLoadingDashboardId(dashboardId);
    onAddToDashboard(dashboardId);
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        onOpenChange(open);
        // Restore focus when dialog closes
        if (!open && buttonRef?.current) {
          setTimeout(() => {
            buttonRef.current?.focus();
          }, 0);
        }
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t("addToDashboard")}</DialogTitle>
          <DialogDescription>
            {t("chooseADashboardToAddThisChartToOrCreateANewOne")}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <h4 className="text-sm font-medium">{t("existingDashboards")}</h4>
            <ScrollArea className="h-[200px] rounded-md border p-2">
              {isLoadingDashboards ? (
                <div className="flex items-center justify-center h-full">
                  <LoadingSpinner size={16} />
                </div>
              ) : dashboards?.length === 0 ? (
                <div className="text-center text-sm text-muted-foreground">
                  {t("noDashboardsFound")}
                </div>
              ) : (
                <div className="space-y-2">
                  {dashboards?.map((dashboard: Dashboard) => (
                    // <Button
                    //   key={dashboard.dashboard_id}
                    //   variant="outline"
                    //   className="w-full justify-start"
                    //   onClick={() => onAddToDashboard(dashboard.dashboard_id)}
                    // >
                    //   {dashboard.title}
                    // </Button>
                    <div
                      className="flex items-center justify-between"
                      key={dashboard.dashboard_id}
                    >
                      <Button
                        key={dashboard.dashboard_id}
                        variant="outline"
                        className="w-full justify-start cursor-default"
                      >
                        {dashboard.title}
                      </Button>
                      <div className="flex items-center">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="outline"
                                className="ml-2 shadow-none w-8 h-8 p-0"
                                onClick={(e) => {
                                  e.preventDefault();
                                  handleAddToDashboard(dashboard.dashboard_id);
                                }}
                                disabled={
                                  isDashboardAdded &&
                                  loadingDashboardId === dashboard.dashboard_id
                                }
                              >
                                <div className="w-4 h-4 flex items-center justify-center">
                                  {isDashboardAdded &&
                                  loadingDashboardId ===
                                    dashboard.dashboard_id ? (
                                    <Loader2 className="animate-spin" />
                                  ) : (
                                    <Plus />
                                  )}
                                </div>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{t("addToDashboard")}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>

                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="outline"
                                className="ml-2 shadow-none"
                                onClick={() => {
                                  onViewDashboard(dashboard.dashboard_id);
                                }}
                              >
                                {/* Replace with appropriate icon for redirect */}
                                <ArrowUpRight className="w-4 h-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{t("viewDashboard")}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-px bg-border" />
            <span className="text-sm text-muted-foreground">or</span>
            <div className="flex-1 h-px bg-border" />
          </div>
          <Button
            variant="outline"
            className="w-full"
            onClick={onCreateNewDashboard}
          >
            <Plus className="w-4 h-4 mr-2" />
            {t("createNewDashboard")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
