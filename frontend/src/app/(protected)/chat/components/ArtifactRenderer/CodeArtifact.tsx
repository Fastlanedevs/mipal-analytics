import React from "react";
import { Artifact } from "../../types/chat";
import { Code2Icon } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface CodeArtifactProps {
  artifact: Artifact;
}

export const CodeArtifact: React.FC<CodeArtifactProps> = ({ artifact }) => {
  return (
    <div className="mt-4">
      {artifact.title && (
        <div className="flex items-center mb-2 space-x-2">
          <Code2Icon className="w-4 h-4" />
          <span className="font-medium">{artifact.title}</span>
        </div>
      )}
      <SyntaxHighlighter
        language={artifact.language || "typescript"}
        style={vscDarkPlus}
        className="rounded-md !bg-[#1E1E1E]"
        showLineNumbers
        customStyle={{
          margin: 0,
          background: "#1E1E1E",
        }}
      >
        {typeof artifact.content === "string"
          ? artifact.content
          : JSON.stringify(artifact.content)}
      </SyntaxHighlighter>
    </div>
  );
};
