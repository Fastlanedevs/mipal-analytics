import { cn } from "@/lib/utils";
import { LoadingSpinner } from "./LoadingSpinner";

interface PageHeaderProps {
  title: string;
  description?: string | React.ReactNode;
  className?: string;
  align?: "start" | "center" | "end";
  actions?: React.ReactNode;
  isLoading?: boolean;
  loadingSize?: number;
}

export function PageHeader({
  title,
  description,
  className,
  align = "start",
  actions,
  isLoading = false,
  loadingSize = 20,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4",
        className
      )}
    >
      <div className={cn("space-y-3 flex-1", `text-${align}`)}>
        <h1 className="text-2xl font-bold tracking-tight sm:text-4xl flex items-center gap-4">
          {title}
          {isLoading && <LoadingSpinner size={loadingSize} />}
        </h1>
        {description && (
          <div className="text-sm text-muted-foreground sm:text-base">
            {description}
          </div>
        )}
      </div>
      {actions && (
        <div className="flex flex-col sm:flex-row gap-3">{actions}</div>
      )}
    </div>
  );
}
