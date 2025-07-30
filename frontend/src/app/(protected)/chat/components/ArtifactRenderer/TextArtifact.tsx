import React from "react";
import { Artifact } from "../../types/chat";
import { FileTextIcon } from "lucide-react";
import { MarkdownRenderer } from "../MarkdownRenderer";
import { cn } from "@/lib/utils";
import mermaid from "mermaid";

interface TextArtifactProps {
  artifact: Artifact;
}

export const TextArtifact: React.FC<TextArtifactProps> = ({ artifact }) => {
  React.useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: document.documentElement.classList.contains("dark")
        ? "dark"
        : "default",
      securityLevel: "loose",
      fontFamily: "inherit",
    });

    // Add this to force re-render of mermaid diagrams
    setTimeout(() => {
      mermaid.contentLoaded();
    }, 100);
  }, [artifact.content]);

  const processContent = (content: string) => {
    // Remove excessive indentation
    const lines = content.split("\n");
    const minIndent = lines
      .filter((line) => line.trim().length > 0)
      .reduce((min, line) => {
        const indent = line.match(/^\s*/)?.[0].length || 0;
        return Math.min(min, indent);
      }, Infinity);

    // Process mermaid code blocks
    let processedContent = lines
      .map((line) => line.slice(minIndent))
      .join("\n")
      .trim();

    // Ensure mermaid code blocks have proper class
    processedContent = processedContent.replace(
      /```mermaid/g,
      '```mermaid class="mermaid"'
    );

    return processedContent;
  };

  const isMarkdownContent = () => {
    return (
      artifact.file_type === "md" ||
      artifact.language === "md" ||
      /[*#\[\]`]|```mermaid/.test(artifact.content as string)
    );
  };

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
          isMarkdownContent() && "prose prose-sm max-w-none dark:prose-invert",
          "markdown-content"
        )}
      >
        {isMarkdownContent() ? (
          <MarkdownRenderer
            content={processContent(artifact.content as string)}
          />
        ) : (
          <div className="p-4 whitespace-pre-wrap rounded-md bg-muted">
            {artifact.content as string}
          </div>
        )}
      </div>
    </div>
  );
};
