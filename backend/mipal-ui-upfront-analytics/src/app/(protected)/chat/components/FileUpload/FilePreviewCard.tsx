import React from "react";
import { FileUploadState } from "../../types/chat";
import { Progress } from "@/components/ui/progress";
import { X, Eye, FileIcon, Loader2 } from "lucide-react";
import Image from "next/image";
import { useTranslations } from "next-intl";
interface FilePreviewCardProps {
  file: FileUploadState;
  onRemove: (id: string) => void;
  onPreview: (id: string) => void;
}

export const FilePreviewCard: React.FC<FilePreviewCardProps> = ({
  file,
  onRemove,
  onPreview,
}) => {
  const isImage = file.file.type.startsWith("image/");
  const isPDF = file.file.type === "application/pdf";
  const t = useTranslations("chatPage.fileUploadHandler");
  const renderStatus = () => {
    switch (file.status) {
      case "uploading":
      case "processing":
        return (
          <div className="absolute inset-0 bg-background/50 backdrop-blur-sm flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        );
      case "error":
        return (
          <div className="absolute inset-0 bg-destructive/10 flex items-center justify-center">
            <div className="text-xs text-destructive text-center p-2">
              {t("errorLoadingFile")}
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="relative group rounded-lg border p-2 hover:bg-accent/50 transition-all bg-background/50">
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all rounded-lg" />

      {renderStatus()}

      <div className="absolute top-1 right-1 opacity-100 transition-opacity z-10 flex md:flex-row flex-col-reverse md:gap-1 gap-2">
        {/* {file.status === "complete" && (
          <button
            onClick={() => onPreview(file.id)}
            className="md:p-1.5 p-1 rounded-full bg-white/90 hover:bg-white shadow-sm text-black/80 hover:text-black transition-colors"
          >
            <Eye className="h-3.5 w-3.5" />
          </button>
        )} */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove(file.id);
          }}
          className="md:p-1.5 p-1 rounded-full bg-white/90 hover:bg-white shadow-sm text-black/80 hover:text-black transition-colors"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div
        className="aspect-square w-full relative h-[60px] rounded-md overflow-hidden"
        title={file.file.name}
      >
        {isImage && file.preview ? (
          <Image
            src={file.preview}
            alt={file.file.name}
            fill
            className="object-cover rounded"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <FileIcon className="h-6 w-6" />
          </div>
        )}
      </div>

      <div className="mt-1 space-y-0.5 relative z-[1] text-center">
        <p className="text-xs text-center truncate text-foreground/90">
          {file.file.name}
        </p>
        {(file.status === "uploading" || file.status === "processing") && (
          <Progress value={file.progress} className="h-1" />
        )}
        {file.error && (
          <p className="text-xs text-destructive truncate" title={file.error}>
            {file.error}
          </p>
        )}
      </div>
    </div>
  );
};
