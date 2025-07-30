import React from "react";

export const LoadingMessageSkeleton = () => {
  return (
    <div className="space-y-8">
      <div className="flex flex-row w-full items-start justify-end animate-fade-in gap-1">
        <div className="flex flex-col gap-2 p-4 rounded-2xl bg-muted/50 dark:bg-[hsl(var(--subtle-border))] max-w-full md:max-w-[90%] md:min-w-[80%] backdrop-blur-sm">
          <div className="space-y-4 mt-2">
            <div className="w-full h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-full h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-4/5 h-2 bg-foreground/10 rounded animate-pulse ml-auto" />
            <div className="w-4/5 h-2 bg-foreground/10 rounded animate-pulse ml-auto" />
          </div>
        </div>
        <div className="w-8 h-8 bg-foreground/10 rounded-full animate-pulse" />
      </div>
      <div className="flex flex-row w-full items-start justify-start animate-fade-in gap-1">
        <div className="flex flex-col gap-2 p-4 rounded-2xl  max-w-full w-full backdrop-blur-sm">
          <div className="space-y-4 text-start">
            <div className="w-full h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-full h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-4/5 h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-4/5 h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-full h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-full h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-full h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-4/5 h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-4/5 h-2 bg-foreground/10 rounded animate-pulse" />
            <div className="w-1/2 h-2 bg-foreground/10 rounded animate-pulse" />
          </div>
        </div>
      </div>
    </div>
  );
};
