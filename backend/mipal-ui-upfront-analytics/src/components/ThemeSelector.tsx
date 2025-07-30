"use client";

import { Theme, useTheme } from "@/contexts/ThemeContext";
import {
  useGetUserSettingsQuery,
  useUpdateUserSettingsMutation,
} from "@/store/services/userApi";
import { Moon, Sun, Monitor } from "lucide-react";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";

export function ThemeSelector({
  simplified = false,
}: {
  simplified?: boolean;
}) {
  const t = useTranslations("sidebar.themeSelector");
  const { data: userSettings } = useGetUserSettingsQuery({});
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    setTheme(userSettings?.theme || "light");
  }, [userSettings]);

  const [updateUserSettings] = useUpdateUserSettingsMutation();
  const handleThemeChange = (theme: Theme) => {
    setTheme(theme as Theme); // Casting to any to avoid type mismatch
    updateUserSettings({ theme });
  };

  // Simple toggle between dark and light
  if (simplified) {
    const toggleTheme = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      const newTheme = theme === "dark" ? "light" : "dark";
      handleThemeChange(newTheme);
    };

    return (
      <Button
        variant="ghost"
        size="icon"
        className="hover:bg-subtle-hover p-1.5"
        onClick={toggleTheme}
        aria-label={
          theme === "dark" ? t("switchToLightTheme") : t("switchToDarkTheme")
        }
      >
        {theme === "dark" ? (
          <Sun className="h-4 w-4" />
        ) : (
          <Moon className="h-4 w-4" />
        )}
      </Button>
    );
  }

  return (
    <div className="flex gap-2 items-center p-2 rounded-lg bg-card">
      <button
        onClick={() => handleThemeChange("light")}
        className={`p-2 rounded-lg transition-colors ${
          theme === "light"
            ? "bg-primary text-primary-foreground"
            : "hover:bg-secondary"
        }`}
        aria-label={t("lightTheme")}
      >
        <Sun className="w-5 h-5" />
      </button>
      <button
        onClick={() => handleThemeChange("dark")}
        className={`p-2 rounded-lg transition-colors ${
          theme === "dark"
            ? "bg-primary text-primary-foreground"
            : "hover:bg-secondary"
        }`}
        aria-label={t("darkTheme")}
      >
        <Moon className="w-5 h-5" />
      </button>
      <button
        onClick={() => handleThemeChange("system")}
        className={`p-2 rounded-lg transition-colors ${
          theme === "system"
            ? "bg-primary text-primary-foreground"
            : "hover:bg-secondary"
        }`}
        aria-label={t("systemTheme")}
      >
        <Monitor className="w-5 h-5" />
      </button>
    </div>
  );
}
