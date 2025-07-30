import React from "react";
import { FilePreviewCard } from "./FilePreviewCard";
import { FileUploadState } from "../../types/chat";

interface FilePreviewGridProps {
  files: FileUploadState[];
  onRemoveFile: (id: string) => void;
  onPreviewFile: (id: string) => void;
  remoteFiles: FileUploadState[];
}

export const FilePreviewGrid: React.FC<FilePreviewGridProps> = ({
  files,
  onRemoveFile,
  onPreviewFile,
  remoteFiles,
}) => {
  if (files.length === 0 && remoteFiles.length === 0) return null;

  return (
    <div className="w-full flex flex-col items-center justify-center">
      <div className="bg-white/10 dark:bg-black/10 backdrop-blur-lg supports-[backdrop-filter]:bg-white/5 dark:supports-[backdrop-filter]:bg-black/5 border border-b-0 border-subtle-border dark:border-subtle-border rounded-t-xl shadow-file-upload-shadow dark:shadow-file-upload-shadow-dark p-4 max-w-[calc(100%-2rem)] w-full flex-wrap flex flex-col gap-3">
        {(files.length > 0 || remoteFiles.length > 0) && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-6 overflow-y-auto max-h-[180px]">
            {files.map((file) => (
              <div
                key={file.id}
                className="transition-opacity cursor-pointer hover:opacity-90"
                onClick={
                  file.status === "complete"
                    ? () => onPreviewFile(file.id)
                    : undefined
                }
              >
                <FilePreviewCard
                  file={file}
                  onRemove={onRemoveFile}
                  onPreview={onPreviewFile}
                />
              </div>
            ))}
            {remoteFiles.map((file) => (
              <div
                key={file.id}
                className="transition-opacity cursor-pointer hover:opacity-90"
                onClick={
                  file.status === "complete"
                    ? () => onPreviewFile(file.id)
                    : undefined
                }
              >
                <FilePreviewCard
                  file={file}
                  onRemove={onRemoveFile}
                  onPreview={onPreviewFile}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
