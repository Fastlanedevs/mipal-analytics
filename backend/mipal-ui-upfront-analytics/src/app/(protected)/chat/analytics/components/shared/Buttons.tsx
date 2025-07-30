import React from "react";
import { Button } from "@/components/ui/button";
import { ChevronRight, LucideIcon } from "lucide-react";

interface ActionButtonProps {
  icon: LucideIcon;
  title: string;
  description: string;
  onClick: () => void;
}

export const ActionButton = ({
  icon: Icon,
  title,
  description,
  onClick,
}: ActionButtonProps) => (
  <Button
    variant="ghost"
    className="w-full justify-start h-auto p-4 group hover:bg-accent/50 active:bg-accent/70 border border-border rounded-2xl"
    onClick={onClick}
  >
    <div className="flex items-start gap-3 w-full">
      <div className="mt-0.5 flex-shrink-0 p-2 rounded-lg bg-primary/10">
        <Icon className="w-5 h-5 text-primary" />
      </div>
      <div className="text-left min-w-0 flex-1">
        <div className="font-medium text-sm mb-1 line-clamp-1 flex items-center justify-between text-foreground">
          {title}
          <ChevronRight className="w-4 h-4" />
        </div>
        <div className="text-xs text-muted-foreground opacity-70 text-wrap">
          {description}
        </div>
      </div>
    </div>
  </Button>
);

interface DatabaseMenuItemProps {
  name: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
}

export const DatabaseMenuItem = ({
  name,
  description,
  icon,
  onClick,
}: DatabaseMenuItemProps) => (
  <Button
    variant="ghost"
    className="w-full justify-start h-auto p-4 group hover:bg-accent/50 active:bg-accent/70 border border-border rounded-2xl ml-4"
    onClick={onClick}
  >
    <div className="flex items-start gap-3 w-full">
      <div className="mt-0.5 flex-shrink-0 p-2 rounded-lg bg-primary/10">
        {icon}
      </div>
      <div className="text-left min-w-0 flex-1">
        <div className="font-medium text-sm mb-1 line-clamp-1 flex items-center justify-between text-foreground">
          {name}
          <ChevronRight className="w-4 h-4" />
        </div>
        <div className="text-xs text-muted-foreground opacity-70">
          {description}
        </div>
      </div>
    </div>
  </Button>
);
