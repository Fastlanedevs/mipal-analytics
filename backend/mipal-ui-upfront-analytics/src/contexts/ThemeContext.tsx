"use client";

import { createContext, useContext } from "react";
import { useTheme as useNextTheme } from "next-themes";

export type Theme = "dark" | "light" | "system";

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function useTheme() {
  const { theme, setTheme } = useNextTheme();

  return {
    theme: theme as Theme,
    setTheme: (newTheme: Theme) => setTheme(newTheme),
  };
}

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>;
};
