import React from "react";
import { Artifact } from "../../types/chat";
import { ChartArea, ImageIcon } from "lucide-react";

interface ImageArtifactProps {
  artifact: Artifact;
}

export const ImageArtifact: React.FC<ImageArtifactProps> = ({ artifact }) => {
  return (
    <div className="mt-4">
      {artifact.title && (
        <div className="flex items-center mb-2 space-x-2">
          {/* <ImageIcon className="w-4 h-4" /> */}
          <ChartArea className="w-4 h-4" />
          <span className="font-medium">{artifact.title}</span>
        </div>
      )}
      <div className="relative w-full">
        <img
          src={artifact.content as string}
          alt={artifact.title || "Analysis Image"}
          className="w-full h-auto rounded-md object-contain max-h-[600px]"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.onerror = null;
            target.src =
              "https://via.placeholder.com/400x300?text=Image+Load+Error";
          }}
        />
        {artifact.title && (
          <p className="mt-2 text-sm text-muted-foreground">{artifact.title}</p>
        )}
      </div>
    </div>
  );
};
