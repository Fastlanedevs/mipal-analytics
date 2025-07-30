import React from "react";
import { Artifact } from "../../types/chat";
import { ImageArtifact } from "./ImageArtifact";
import { TextArtifact } from "./TextArtifact";
import { CodeArtifact } from "./CodeArtifact";
import { DocumentArtifact } from "./DocumentArtifact";
import { PresentationArtifact } from "./PresentationArtifact";
import { TipTapEditorPanel } from "../TipTapEditorPanel";

interface ArtifactRendererProps {
  artifact: Artifact;
}

export const ArtifactRenderer: React.FC<ArtifactRendererProps> = ({
  artifact,
}) => {
  const renderContent = () => {
    switch (artifact.artifact_type) {
      case "text":
        return <TextArtifact artifact={artifact} />;

      case "code":
        return <CodeArtifact artifact={artifact} />;

      case "image":
        return <ImageArtifact artifact={artifact} />;

      case "document":
        return <DocumentArtifact artifact={artifact} />;

      case "presentation":
      case "tsx":
      case "jsx":
        return <PresentationArtifact artifact={artifact} />;

      case "tiptap":
        return <TipTapEditorPanel content={artifact.content as string} />;
    }
  };

  return renderContent();
};
