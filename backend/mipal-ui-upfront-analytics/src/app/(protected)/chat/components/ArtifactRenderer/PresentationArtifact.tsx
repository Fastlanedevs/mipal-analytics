import React from "react";
import { Artifact } from "../../types/chat";
import TsxRenderer from "../tsx-renderer";
import { Code2Icon } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTranslations } from "next-intl";

interface PresentationArtifactProps {
  artifact: Artifact;
}

export const PresentationArtifact: React.FC<PresentationArtifactProps> = ({
  artifact,
}) => {
  const t = useTranslations("chatPage.artifactPresentation");
  if (artifact.artifact_type === "presentation") {
    return (
      <div className="w-full space-y-4">
        <div className="border rounded-md">
          <div className="p-2 border-b bg-muted">
            <h3 className="text-sm font-medium">{t("interactivePreview")}</h3>
          </div>
          <div className="p-4">
            <TsxRenderer code={artifact.content as string} />
          </div>
        </div>
      </div>
    );
  }

  // For tsx/jsx types
  return (
    <div className="w-full">
      <div className="mb-4">
        <SyntaxHighlighter
          language="typescript"
          style={vscDarkPlus}
          className="rounded-md !bg-[#1E1E1E]"
          showLineNumbers
          customStyle={{
            margin: 0,
            background: "#1E1E1E",
          }}
        >
          {artifact.content as string}
        </SyntaxHighlighter>
      </div>
      <div className="p-4 border rounded-md">
        <h3 className="mb-2 text-sm font-medium">{t("preview")}</h3>
        <TsxRenderer code={artifact.content as string} />
      </div>
    </div>
  );
};
