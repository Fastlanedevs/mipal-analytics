import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, FileText, Search } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

import { useRouter } from "next/navigation";
import { useGetAllTemplatesQuery } from "@/store/services/sourcingApi";

interface Template {
  id: string;
  template_id: string;
  industry: string;
  name: string;
  description: string;
  sections: {
    heading: string;
    subheading: string;
    content: string | null;
  }[];
  created_at: string;
  updated_at: string;
}

interface TemplateSelectionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTemplate: (template: Template) => void;
}

export const TemplateSelectionPanel: React.FC<TemplateSelectionPanelProps> = ({
  isOpen,
  onClose,
  onSelectTemplate,
}) => {
  const router = useRouter();
  const [width, setWidth] = useState(window.innerWidth * 0.3);
  const [isResizing, setIsResizing] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(width);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: templates, isLoading } = useGetAllTemplatesQuery(undefined, {
    skip: !isOpen,
  });

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
      const minWidth = windowWidth * 0.2; // 20% of window width
      const maxWidth = windowWidth * 0.5; // 50% of window width
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

  const handleTemplateClick = (template: Template) => {
    router.push(
      `/sourcing/rfp/create?template_id=${template.template_id || template.id}`
    );
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Resize handle */}
      <div
        className={cn(
          "fixed flex items-center justify-center cursor-ew-resize z-50 w-2 hover:bg-blue-500/50",
          isResizing ? "bg-blue-500/50" : "bg-transparent"
        )}
        style={{
          right: `calc(${width}px + 1px)`,
          top: "-2rem",
          bottom: 0,
          height: "calc(100vh + 2rem)",
        }}
        onMouseDown={handleMouseDown}
      />

      {/* Sidebar panel */}
      <div
        className="fixed right-0 bg-background border-l shadow-lg z-50"
        style={{
          width: `${width}px`,
          top: "-2rem",
          bottom: 0,
          height: "calc(100vh + 2rem)",
        }}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="shrink-0 p-4 border-b bg-background">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Template History</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="h-8 w-8"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Search bar */}
          <div className="shrink-0 p-4 border-b bg-background">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search templates..."
                className="pl-8"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Template list */}
          {/* if no templates, show a message */}
          {templates && templates.length === 0 && (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-muted-foreground">No templates found</p>
            </div>
          )}
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-4 pb-8">
              {isLoading ? (
                <div className="space-y-4 mb-4">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="p-4 border rounded-lg animate-pulse"
                    >
                      <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-muted rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : (
                templates &&
                templates
                  .filter((template) =>
                    template.name
                      .toLowerCase()
                      .includes(searchQuery.toLowerCase())
                  )
                  .map((template) => (
                    <div
                      key={template.id}
                      className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => handleTemplateClick(template)}
                    >
                      <div className="flex items-start gap-3">
                        <FileText className="h-5 w-5 text-muted-foreground mt-1" />
                        <div className="flex-1">
                          <h3 className="font-medium">{template.name}</h3>
                        </div>
                      </div>
                    </div>
                  ))
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </>
  );
};
