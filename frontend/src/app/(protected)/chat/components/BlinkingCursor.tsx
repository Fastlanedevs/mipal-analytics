import { cn } from "@/lib/utils";

export const BlinkingCursor = () => (
  <span
    className={cn(
      "inline-block w-2 h-4 -mb-0.5 bg-foreground dark:bg-subtle-fg",
      "animate-[blink_1s_steps(2)_infinite]"
    )}
  />
);
