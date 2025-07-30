import React from "react";
import { Button } from "@/components/ui/button";
import { Maximize2, Minimize2 } from "lucide-react";

interface ResizablePanelProps {
  children: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
}

export const ResizablePanel: React.FC<ResizablePanelProps> = ({
  children,
  isExpanded,
  onToggle,
}) => {
  return (
    <div
      className={`h-full transition-all duration-300 ease-in-out ${
        isExpanded ? "w-full" : "w-1/2"
      }`}
    >
      {!isExpanded && (
        <div className="flex items-center justify-between p-2 border-b">
          <h2 className="text-lg font-semibold text-black">Code Preview</h2>
          <Button variant="ghost" size="sm" onClick={onToggle}>
            <Maximize2 className="w-4 h-4" />
          </Button>
        </div>
      )}
      <div className="relative h-full">
        {children}
        {isExpanded && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className="absolute top-2 right-2"
          >
            <Minimize2 className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  );
};
