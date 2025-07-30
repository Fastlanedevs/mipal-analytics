import { toast } from "@/hooks/use-toast";
import { Warning } from "@/app/(protected)/chat/types/chat";

export const WARNING_DURATIONS = {
  RATE_LIMIT: 10000,
  DEFAULT: 5000,
} as const;

export const WARNING_ACTIONS = {
  UPGRADE: "upgrade",
  RETRY: "retry",
  ACKNOWLEDGE: "acknowledge",
} as const;

export const handleWarningAction = (warning: Warning) => {
  const actionMessages = {
    [WARNING_ACTIONS.UPGRADE]: {
      title: "Upgrade Required",
      description: "Redirecting to upgrade page...",
    },
    [WARNING_ACTIONS.RETRY]: {
      title: "Retrying",
      description: "Attempting to retry the operation...",
    },
    [WARNING_ACTIONS.ACKNOWLEDGE]: {
      title: "Acknowledged",
      description: "Warning has been acknowledged",
    },
  } as const;

  const actionType = warning.action?.type as keyof typeof actionMessages;
  if (actionType && actionMessages[actionType]) {
    toast(actionMessages[actionType]);
  }
};

export const showWarningToast = (warning: Warning) => {
  const toastData = {
    title: warning.type.charAt(0).toUpperCase() + warning.type.slice(1),
    description: warning.message,
    variant:
      warning.level === "error"
        ? ("destructive" as const)
        : ("default" as const),
    duration:
      warning.type === "rate_limit"
        ? WARNING_DURATIONS.RATE_LIMIT
        : WARNING_DURATIONS.DEFAULT,
  };

  if (warning.action) {
    toast({
      ...toastData,
      action: {
        label: warning.action.label,
        onClick: () => handleWarningAction(warning),
      },
    });
  } else {
    toast(toastData);
  }
};

export const handleWarnings = (warnings?: Warning[]) => {
  if (Array.isArray(warnings)) {
    warnings.forEach(showWarningToast);
  }
};
