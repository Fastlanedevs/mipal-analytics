import React from "react";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { FileUploadState } from "../../types/chat";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  FileIcon,
  ImageIcon,
  FileTextIcon,
  CodeIcon,
  XIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";

interface FilePreviewDialogProps {
  file: FileUploadState | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  extractedContent?: string;
}

const isCodeFile = (fileName: string): boolean => {
  const codeExtensions = [
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".rb",
    ".php",
    ".html",
    ".css",
    ".json",
    ".md",
    ".yml",
    ".yaml",
  ];
  return codeExtensions.some((ext) => fileName.toLowerCase().endsWith(ext));
};

const FilePreviewDialog: React.FC<FilePreviewDialogProps> = ({
  file,
  isOpen,
  onOpenChange,
  extractedContent,
}) => {
  const t = useTranslations("chatPage.fileUploadHandler");
  if (!file) return null;

  const isImage = file.file.type.startsWith("image/");
  const isCode = isCodeFile(file.file.name);

  const getFileIcon = () => {
    if (isImage) return <ImageIcon className="w-5 h-5" />;
    if (isCode) return <CodeIcon className="w-5 h-5" />;
    return <FileIcon className="w-5 h-5" />;
  };

  return (
    <AlertDialog open={isOpen} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-4xl lg:max-h-[80vh] flex flex-col">
        <AlertDialogHeader>
          {/* Close Icon */}
          <XIcon
            className="absolute top-2.5 right-2.5 w-6 h-6 cursor-pointer p-1 hover:bg-accent-foreground/80 rounded-lg hover:text-background"
            onClick={() => onOpenChange(false)}
          />
          <AlertDialogTitle className="flex items-center gap-2">
            {getFileIcon()}
            <span className="truncate">{file.file.name}</span>
            <span className="ml-2 text-sm text-muted-foreground">
              ({(file.file.size / 1024).toFixed(2)} KB)
            </span>
          </AlertDialogTitle>
        </AlertDialogHeader>

        <div className="flex-1 min-h-0 mt-4">
          <ScrollArea className="h-[60vh] rounded-md border">
            <div className="p-4">
              {isImage && file.preview ? (
                <div className="flex items-center justify-center">
                  <img
                    src={file.preview}
                    alt={file.file.name}
                    className="max-w-full max-h-[55vh] object-contain rounded-md"
                  />
                </div>
              ) : (
                <div className="font-mono text-sm whitespace-pre-wrap">
                  {extractedContent || t("noContentExtracted")}
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export default FilePreviewDialog;
