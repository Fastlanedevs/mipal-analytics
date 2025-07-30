import React from "react";
import { Artifact } from "../../types/chat";
import { FileIcon } from "lucide-react";
import { Card } from "@/components/ui/card";

interface DocumentArtifactProps {
  artifact: Artifact;
}

export const DocumentArtifact: React.FC<DocumentArtifactProps> = ({
  artifact,
}) => {
  return (
    <div className="mt-4">
      <Card className="flex items-center p-4 space-x-2">
        <FileIcon className="w-6 h-6" />
        <div>
          <p className="font-medium">{artifact.title}</p>
          <p className="text-sm text-muted-foreground">{artifact.file_type}</p>
        </div>
      </Card>
    </div>
  );
};
