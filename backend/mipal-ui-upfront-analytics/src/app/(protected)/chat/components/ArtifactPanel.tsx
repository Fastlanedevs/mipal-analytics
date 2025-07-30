import React, { useState, useEffect } from "react";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArtifactRenderer } from "./ArtifactRenderer";
import { Artifact } from "../types/chat";
import { X, FileText, Image, Code2, File } from "lucide-react";
import { useMediaQuery } from "@/hooks/use-media-query";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

interface ArtifactPanelProps {
  artifacts: Artifact[];
  isOpen: boolean;
  onClose: () => void;
}

const getArtifactIcon = (type: Artifact["artifact_type"]) => {
  switch (type) {
    case "image":
      return <Image className="w-4 h-4" />;
    case "code":
    case "tsx":
      return <Code2 className="w-4 h-4" />;
    case "text":
      return <FileText className="w-4 h-4" />;
    default:
      return <File className="w-4 h-4" />;
  }
};

export const ArtifactPanel: React.FC<ArtifactPanelProps> = ({
  artifacts,
  isOpen,
  onClose,
}) => {
  const t = useTranslations("chatPage.artifactPanel");
  const isMobile = useMediaQuery("(max-width: 768px)");
  const [width, setWidth] = useState(window.innerWidth * 0.5);
  const [isResizing, setIsResizing] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(width);
  const [selectedArtifactIndex, setSelectedArtifactIndex] = useState(0);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    setStartX(e.pageX);
    setStartWidth(width);
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const diff = startX - e.pageX;
      const windowWidth = window.innerWidth;
      const minWidth = windowWidth * 0.3; // 30% of window width
      const maxWidth = windowWidth * 0.7; // 70% of window width
      const newWidth = Math.min(
        Math.max(minWidth, startWidth + diff),
        maxWidth
      );
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, startX, startWidth]);

  // Reset selected artifact when panel opens
  useEffect(() => {
    if (isOpen) {
      setSelectedArtifactIndex(0);
    }
  }, [isOpen]);

  if (!artifacts.length || !isOpen) return null;

  const renderArtifactTabs = () => {
    const handleWheel = (e: React.WheelEvent) => {
      e.preventDefault();
      const container = e.currentTarget;
      container.scrollLeft += e.deltaY;
    };

    return (
      <div
        className="flex space-x-1 overflow-x-auto scrollbar-hide border-b"
        onWheel={handleWheel}
      >
        {artifacts.map((artifact, index) => (
          <button
            key={index}
            onClick={() => setSelectedArtifactIndex(index)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors",
              "border-b-2 -mb-px",
              selectedArtifactIndex === index
                ? "border-blue-500 text-blue-500"
                : "border-transparent hover:border-gray-200 text-gray-600 hover:text-gray-900 dark:hover:text-gray-100"
            )}
          >
            {getArtifactIcon(artifact.artifact_type)}
            <span className="truncate">
              {artifact.title || `Artifact ${index + 1}`}
            </span>
          </button>
        ))}
      </div>
    );
  };

  // For mobile, render as a bottom drawer
  if (isMobile) {
    return (
      <Sheet open={isOpen} onOpenChange={onClose}>
        <SheetContent side="bottom" className="h-full w-full z-50">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">{t("analysisResults")}</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full dark:hover:bg-gray-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          {renderArtifactTabs()}
          <ScrollArea className="h-[calc(100%-8rem)] mt-4">
            <div className="pr-4 overflow-auto">
              <ArtifactRenderer artifact={artifacts[selectedArtifactIndex]} />
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>
    );
  }

  // For desktop, render as a side panel overlay with resize handle
  return (
    <>
      {/* Resize handle */}
      <div
        className={`flex items-center justify-center cursor-ew-resize z-50 w-2 hover:bg-blue-500/50 ${
          isResizing ? "bg-blue-500/50" : "bg-transparent"
        }`}
        style={
          {
            // left: `calc(100% - ${width}px - 2px)`,
            // display: isOpen ? 'block' : 'none'
          }
        }
        onMouseDown={handleMouseDown}
      >
        {/* <div className="text-gray-400">
          <GripVertical className="w-4 h-4" />
        </div> */}
      </div>
      <div
        className="flex flex-col justify-center"
        style={{ width: `${width}px` }}
      >
        {/* Panel */}
        <div
          className={`h-full lg:h-[95%] lg:right-8 lg:top-[2.5%] lg:rounded-l-xl bg-background border shadow-lg transform transition-transform duration-200 ease-in-out z-50`}
        >
          <div className="h-full flex flex-col">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">{t("analysisResults")}</h2>
              <div className="flex items-center gap-2">
                {/* <span className="text-sm text-gray-500">
                  {width}px
                </span> */}
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 rounded-full dark:hover:bg-gray-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            {renderArtifactTabs()}
            <ScrollArea className="flex-1">
              <div className="p-4">
                <ArtifactRenderer artifact={artifacts[selectedArtifactIndex]} />
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </>
  );
};
