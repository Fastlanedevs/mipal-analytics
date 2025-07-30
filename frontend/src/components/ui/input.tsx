import * as React from "react";
import { cn } from "@/lib/utils";

const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full rounded-md border border-muted-foreground bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-secondary-foreground placeholder:text-muted-foreground focus:outline-none dark:focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-70 dark:border-muted-foreground/50",
        className
      )}
      ref={ref}
      {...props}
    />
  );
});
Input.displayName = "Input";

export { Input };
