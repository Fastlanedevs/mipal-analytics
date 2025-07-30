import React, { useState, useEffect } from "react";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  X,
  FileText,
  FileCode,
  FileVideo,
  FileAudio,
  FileArchive,
  FileType,
} from "lucide-react";
import { useMediaQuery } from "@/hooks/use-media-query";
import { Card } from "@/components/ui/card";
import { useTour } from "@/contexts/TourContext";
import { useGetTourGuideQuery } from "@/store/services/userApi";
import {
  GoogleDocsIcon,
  GoogleSheetsIcon,
  GoogleSlidesIcon,
  GoogleDrawingsIcon,
  GooglePDFIcon,
} from "@/components/icons/GoogleDriveIcons";
import { Badge } from "@/components/ui/badge";
import { AnimatePresence, motion } from "framer-motion";

interface Reference {
  type: string;
  title: string;
  content?: string;
  address?: string;
  description?: string;
}

interface ReferencePanelProps {
  references: Reference[];
  isOpen: boolean;
  onClose: () => void;
}

const getIconByType = (type: string, address?: string) => {
  // Check if it's a Google Drive URL
  if (
    address?.includes("drive.google.com") ||
    address?.includes("docs.google.com")
  ) {
    if (address.includes("/file/d/")) {
      return <GooglePDFIcon className="w-4 h-4" />;
    } else if (address.includes("/document/d/")) {
      return <GoogleDocsIcon className="w-4 h-4" />;
    } else if (address.includes("/spreadsheets/d/")) {
      return <GoogleSheetsIcon className="w-4 h-4" />;
    } else if (address.includes("/presentation/d/")) {
      return <GoogleSlidesIcon className="w-4 h-4" />;
    } else if (address.includes("/drawing/d/")) {
      return <GoogleDrawingsIcon className="w-4 h-4" />;
    } else if (address.includes("/script/d/")) {
      return <FileCode className="w-4 h-4 text-yellow-500" />;
    } else if (address.includes("/video/d/")) {
      return <FileVideo className="w-4 h-4 text-red-500" />;
    } else if (address.includes("/audio/d/")) {
      return <FileAudio className="w-4 h-4 text-pink-500" />;
    } else if (address.includes("/archive/d/")) {
      return <FileArchive className="w-4 h-4 text-gray-500" />;
    }
  }

  // Handle file extensions
  const extension = type.split(".").pop()?.toLowerCase();
  switch (extension) {
    case "pdf":
      return <GooglePDFIcon className="w-4 h-4" />;
    case "csv":
      return <GoogleDocsIcon className="w-4 h-4" />;
    case "doc":
    case "docx":
      return <FileText className="w-4 h-4 text-blue-500" />;
    default:
      return <FileType className="w-4 h-4 text-gray-500" />;
  }
};

export const ReferencePanel: React.FC<ReferencePanelProps> = ({
  references,
  isOpen,
  onClose,
}) => {
  const isMobile = useMediaQuery("(max-width: 768px)");
  const [width, setWidth] = useState(window.innerWidth * 0.25);
  const [isResizing, setIsResizing] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(width);
  const { startTour } = useTour();
  const { data: tourGuideState } = useGetTourGuideQuery();
  const [tourStarted, setTourStarted] = useState(false);

  useEffect(() => {
    if (
      isOpen &&
      tourGuideState &&
      !tourStarted &&
      !tourGuideState.knowledge_pal_tour
    ) {
      startTour("knowledgePal");
      setTourStarted(true);
    }
  }, [isOpen, startTour, tourGuideState, tourStarted]);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    setStartX(e.pageX);
    setStartWidth(width);
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";
  };

  const truncateContent = (content?: string) => {
    if (!content) return "";
    const truncated = content.slice(0, 150).split(" ").slice(0, -1).join(" ");
    return truncated + (content?.length > 150 ? "..." : "");
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const diff = startX - e.pageX;
      const windowWidth = window.innerWidth;
      const minWidth = windowWidth * 0.25;
      const maxWidth = windowWidth * 0.7;
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

  if (!references.length) return null;
  if (!isOpen && isMobile) return null;

  const renderReferenceList = () => {
    return (
      <div className="space-y-4 knowledge-pal-tour-start">
        {references.map((reference, index) => (
          <Card key={index} className="p-4">
            <div className="space-y-3 overflow-hidden">
              {reference.address ? (
                <>
                  <div className="flex items-start justify-between">
                    <h3 className="text-base font-semibold flex items-center gap-2 break-words">
                      <span className="shrink-0 flex-center rounded-md p-1 bg-primary/5">
                        {getIconByType(reference.type, reference.address)}
                      </span>
                      <span className="break-all">{reference.title}</span>
                    </h3>
                    <Badge variant="outline" className="text-xs">
                      {reference.type.split(".").pop()?.toUpperCase() || "LINK"}
                    </Badge>
                  </div>
                  <a
                    href={reference.address}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-blue-500 hover:underline line-clamp-1 truncate"
                    title={reference.address}
                  >
                    <span className="break-all">{reference.address}</span>
                  </a>
                </>
              ) : (
                <h3 className="text-lg font-semibold flex items-center gap-2 break-word hover:underlines">
                  {getIconByType(reference.type, reference.address)}
                  <span className="break-all">{reference.title}</span>
                </h3>
              )}
              {reference.description && (
                <p className="text-sm text-muted-foreground break-words">
                  {reference.description}
                </p>
              )}
              {reference.content && (
                <div className="text-sm line-clamp-2 break-words">
                  {truncateContent(reference.content)}
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    );
  };

  if (isMobile) {
    return (
      <Sheet open={isOpen} onOpenChange={onClose}>
        <SheetContent
          side="bottom"
          className="h-[50%] w-full z-50 rounded-t-xl"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">References</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full dark:hover:bg-gray-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <ScrollArea className="h-[calc(100%-5rem)]">
            <div className="pr-4 overflow-auto">{renderReferenceList()}</div>
          </ScrollArea>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              className={`flex items-center justify-center cursor-ew-resize z-50 w-2 hover:bg-blue-500/50 ${
                isResizing ? "bg-blue-500/50" : "bg-transparent"
              }`}
              onMouseDown={handleMouseDown}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            />
            <motion.div
              className="flex flex-col justify-center"
              style={{ width: `${width}px` }}
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            >
              <div
                className={`h-full lg:h-[95%] lg:right-8 lg:top-[2.5%] lg:rounded-l-xl bg-background border shadow-lg transform z-50 knowledge-pal`}
              >
                <div className="h-full flex flex-col">
                  <div className="p-4 border-b flex justify-between items-center">
                    <h2 className="text-lg font-semibold">References</h2>
                    <button
                      onClick={onClose}
                      className="p-2 hover:bg-gray-100 rounded-full dark:hover:bg-gray-800"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <ScrollArea className="flex-1">
                    <div className="p-4">{renderReferenceList()}</div>
                  </ScrollArea>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};
