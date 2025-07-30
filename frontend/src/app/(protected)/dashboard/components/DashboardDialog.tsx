import React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useTranslations } from "next-intl";
interface DashboardDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  dashboardName: string;
  dashboardDescription: string;
  onDashboardNameChange: (name: string) => void;
  onDashboardDescriptionChange: (description: string) => void;
  onSubmit: () => void;
  submitButtonText: string;
  trigger?: React.ReactNode;
  isLoading: boolean;
}

const DashboardDialog: React.FC<DashboardDialogProps> = ({
  isOpen,
  onOpenChange,
  title,
  description,
  dashboardName,
  dashboardDescription,
  onDashboardNameChange,
  onDashboardDescriptionChange,
  onSubmit,
  submitButtonText,
  trigger,
  isLoading,
}) => {
  const t = useTranslations("chatPage.analyticsPal.chartsArtifact");
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <label htmlFor="name" className="text-right">
              {t("name")}
            </label>
            <Input
              id="name"
              value={dashboardName}
              onChange={(e) => onDashboardNameChange(e.target.value)}
              className="col-span-3"
              placeholder={t("namePlaceholder")}
              onKeyDown={(e) => {
                if (e.key === "Enter") onSubmit();
              }}
              autoFocus
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <label htmlFor="description" className="text-right">
              {t("description")}
            </label>
            <Input
              id="description"
              value={dashboardDescription}
              onChange={(e) => onDashboardDescriptionChange(e.target.value)}
              className="col-span-3"
              placeholder={t("descriptionPlaceholder")}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("cancel")}
          </Button>
          <Button onClick={onSubmit} disabled={isLoading}>
            {isLoading ? t("saving") : submitButtonText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DashboardDialog;
