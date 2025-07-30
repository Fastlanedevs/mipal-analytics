import React from "react";
import { Artifact } from "../../types/chat";
import { FileTextIcon } from "lucide-react";
import { MarkdownRenderer } from "../MarkdownRenderer";
import { cn } from "@/lib/utils";

interface MarkdownArtifactProps {
  artifact: Artifact;
}

export const MarkdownArtifact: React.FC<MarkdownArtifactProps> = ({
  artifact,
}) => {
  const content =
    typeof artifact.content === "string"
      ? artifact.content
      : JSON.stringify(artifact.content);
  return (
    <div className="mt-4">
      {artifact.title && (
        <div className="flex items-center mb-2 space-x-2">
          <FileTextIcon className="w-4 h-4" />
          <span className="font-medium">{artifact.title}</span>
        </div>
      )}
      <div
        className={cn(
          "markdown-content",
          "prose prose-sm max-w-none dark:prose-invert"
        )}
      >
        <MarkdownRenderer content={content.trim()} />
      </div>
    </div>
  );
};
