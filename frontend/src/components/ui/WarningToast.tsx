import { Warning } from "@/app/(protected)/chat/types/chat";
import { Toast } from "@/components/ui/toast";
import { AlertCircle, AlertTriangle, Info } from "lucide-react";

interface WarningToastProps {
  warning: Warning;
  onAction?: () => void;
}

export const WarningToast: React.FC<WarningToastProps> = ({
  warning,
  onAction,
}) => {
  const getIcon = () => {
    switch (warning.level) {
      case "error":
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-warning" />;
      default:
        return <Info className="h-4 w-4 text-info" />;
    }
  };

  // Map warning level to toast variant
  const getVariant = () => {
    switch (warning.level) {
      case "error":
        return "destructive";
      case "warning":
      case "info":
        return "default";
      default:
        return "default";
    }
  };

  return (
    <Toast variant={getVariant()}>
      <div className="flex items-start gap-2">
        {getIcon()}
        <div className="flex-1">
          <p className="font-medium">{warning.message}</p>
          {warning.action && (
            <button
              onClick={onAction}
              className="text-sm underline hover:no-underline"
            >
              {warning.action.label}
            </button>
          )}
        </div>
      </div>
    </Toast>
  );
};
