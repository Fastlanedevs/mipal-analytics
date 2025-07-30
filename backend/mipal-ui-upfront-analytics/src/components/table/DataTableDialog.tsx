import {
  DataContent,
  MetadataContent,
  ColumnsContent,
} from "@/app/(protected)/chat/types/chat";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DataTable } from "./DataTable";
import { useTranslations } from "next-intl";
interface DataTableDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  content: DataContent;
  columnsContent?: ColumnsContent;
  metadataContent?: MetadataContent;
}

export const DataTableDialog = ({
  isOpen,
  onOpenChange,
  content,
  columnsContent,
  metadataContent,
}: DataTableDialogProps) => {
  const t = useTranslations("chatPage.analyticsPal.analyticsDataArtifact");
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-[90vw] max-h-[90vh] overflow-auto"
        useBackButton={true}
      >
        <DialogHeader>
          <DialogTitle useBackButton={true}>{t("viewDataTable")}</DialogTitle>
        </DialogHeader>
        <div className="">
          <DataTable
            content={content}
            columnsContent={columnsContent}
            metadataContent={metadataContent}
            showColumnTypes={true}
            showColumnIcons={true}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
};
