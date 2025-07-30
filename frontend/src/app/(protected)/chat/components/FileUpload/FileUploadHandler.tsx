import React, { useRef } from "react";
import { FileUploadState } from "../../types/chat";
import { FilePreviewGrid } from "./FilePreviewGrid";
import { SelectedFile } from "@/store/slices/fileSearchSlice";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

interface FileUploadHandlerProps {
  onFileUpload: (files: File[]) => void;
  files: FileUploadState[];
  onRemoveFile: (id: string) => void;
  onFileClick: (file: FileUploadState) => void;
  processingFiles: Set<string>;
  remoteFiles: FileUploadState[] | [];
  selectedFiles: SelectedFile[] | [];
  showScrollButton: boolean | undefined;
  scrollToBottom: () => void | undefined;
}

export const FileUploadHandler: React.FC<FileUploadHandlerProps> = ({
  onFileUpload,
  files,
  onRemoveFile,
  onFileClick,
  processingFiles,
  remoteFiles = [],
  selectedFiles = [],
  showScrollButton = false,
  scrollToBottom = () => {},
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (selectedFiles.length > 0) {
      onFileUpload(selectedFiles);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="w-full space-y-4 relative">
      <Button
        variant="secondary"
        size="icon"
        className={cn(
          "absolute md:right-8 right-4 z-50 rounded-xl shadow-md md:h-10 md:w-10 h-9 w-9",
          "!bg-background backdrop-blur-sm",
          "transition-opacity duration-200 border border-muted-foreground/50 dark:border-muted-foreground/60 hover:opacity-100 active:opacity-80",
          showScrollButton ? "opacity-80" : "hidden opacity-0",
          "bottom-[calc(100%+1rem)]",
          files.length === 0 && remoteFiles.length === 0 && "bottom-4"
        )}
        onClick={scrollToBottom}
      >
        <ChevronDown className="h-4 w-4" />
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileChange}
        className="hidden"
        multiple
        accept=".txt,.js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.cs,.rb,.php,.html,.css,.json,.md,.yml,.yaml,image/*,.pdf,.doc,.docx,.csv"
      />
      <div className="sticky bottom-0 w-full">
        {(files.length > 0 || remoteFiles.length > 0) && (
          <FilePreviewGrid
            files={files}
            onRemoveFile={onRemoveFile}
            onPreviewFile={(id) => {
              if (selectedFiles.find((f: SelectedFile) => f.id === id)) {
                window.open(
                  selectedFiles.find((f: SelectedFile) => f.id === id)?.address,
                  "_blank"
                );
              } else {
                const fileState = files.find((f) => f.id === id);
                if (fileState) {
                  onFileClick(fileState);
                }
              }
            }}
            remoteFiles={remoteFiles}
          />
        )}
      </div>
    </div>
  );
};
