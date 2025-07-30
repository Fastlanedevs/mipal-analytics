import React from "react";
import { Button } from "@/components/ui/button";
import { Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

interface TrialPeriodProps {
  onClick?: () => void;
  className?: string;
  enable?: boolean;
  loading?: boolean;
  disabled?: boolean;
}

export default function TrialPeriod({
  onClick,
  className,
  enable = false,
  loading = false,
  disabled = false,
}: TrialPeriodProps) {
  const t = useTranslations("settings.pricing");

  if (!enable) {
    return null;
  }
  return (
    <Button
      onClick={onClick}
      variant="default"
      size="lg"
      disabled={disabled || loading}
      className={cn(
        "group relative overflow-hidden transition-all duration-300 hover:scale-[1.02] rounded-full",
        "bg-gradient-to-r from-primary to-primary/80",
        "shadow-lg hover:shadow-xl",
        (disabled || loading) && "opacity-70 cursor-not-allowed",
        className
      )}
    >
      <div className="flex items-center gap-2">
        {loading ? (
          <Loader2 className="h-5 w-5 text-primary-foreground animate-spin" />
        ) : (
          <Sparkles className="h-5 w-5 text-primary-foreground" />
        )}
        <span className="font-semibold text-primary-foreground">
          {loading ? t("loading") : t("freeTrial")}
        </span>
      </div>
      {!disabled && !loading && (
        <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-1000 group-hover:translate-x-full" />
      )}
    </Button>
  );
}
