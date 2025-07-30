"use client";

import AnalyticsChatInterface from "@/app/(protected)/chat/analytics/components/AnalyticsChatInterface";
import { AnalyticsPanel } from "../components/AnalyticsPanel";
import { useState, useRef, useEffect } from "react";
import { Attachment, FileUploadState } from "@/app/(protected)/chat/types/chat";
import { FileSpreadsheet, X } from "lucide-react";
import { useTour } from "@/contexts/TourContext";
import { useGetTourGuideQuery } from "@/store/services/userApi";
import { useTranslations } from "next-intl";

interface FileListProps {
  files: FileUploadState[];
  onRemove: (fileId: string) => void;
}

export default function ChatPage({ params }: { params: { id: string } }) {
  const [width, setWidth] = useState(window.innerWidth * 0.5);
  const [isResizing, setIsResizing] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(width);
  // const [csvAttachments, setCsvAttachments] = useState<Attachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { startTour } = useTour();
  const { data: tourGuideState } = useGetTourGuideQuery();
  const [tourStarted, setTourStarted] = useState(false);
  const [pageReady, setPageReady] = useState(false);
  const tD = useTranslations("chat");

  // Separate useEffect for starting the tour
  useEffect(() => {
    if (pageReady && !tourStarted && tourGuideState) {
      // Add a small delay to ensure DOM is fully rendered
      const timer = setTimeout(() => {
        startTour("analytics");
        setTourStarted(true);
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [pageReady, tourStarted, startTour, tourGuideState]);

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
      const minWidth = windowWidth * 0.3;
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

  // const handleCSVUploadSuccess = (
  //   fileName: string,
  //   extractedContent: string,
  //   fileSize: number
  // ) => {
  //   if (!fileName && !extractedContent) {
  //     setCsvAttachments([]);
  //     return;
  //   }

  //   const attachment: Attachment = {
  //     file_name: fileName,
  //     file_type: "text/csv",
  //     file_size: fileSize,
  //     extracted_content: extractedContent,
  //   };

  //   setCsvAttachments((prev) => [...prev, attachment]);
  // };

  // const handleUploadClick = () => {
  //   if (fileInputRef.current) {
  //     fileInputRef.current.click();
  //   }
  // };

  return (
    <div className="flex h-screen w-full analytics-container">
      <div
        className="flex-1 transition-all duration-300"
        style={{ width: `calc(100% - ${width}px)` }}
      >
        <div className="flex flex-col h-full bg-muted/10">
          <div className="analytics-tour-start" />
          <AnalyticsChatInterface
            chatId={params.id}
            // csvAttachments={csvAttachments}
            fileInputRef={fileInputRef}
            // handleCSVUploadSuccess={handleCSVUploadSuccess}
            setPageReady={setPageReady}
          />
          <div className="text-xs text-muted-foreground text-center pb-2 px-[6px]">
            {tD("disclaimer")}
          </div>
        </div>
      </div>

      <div
        className="flex items-center justify-center cursor-ew-resize z-50 w-2 hover:bg-blue-500/50"
        onMouseDown={handleMouseDown}
      />

      <div className="border-l" style={{ width: `${width}px` }}>
        <AnalyticsPanel
        // csvAttachments={csvAttachments}
        // onRemoveCSVAttachment={(index: number) => {
        //   setCsvAttachments((prev) => prev.filter((_, i) => i !== index));
        // }}
        />
      </div>
    </div>
  );
}
