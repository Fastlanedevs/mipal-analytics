"use client";
import React from "react";
import { Toaster } from "@/components/ui/toaster";
import { usePathname } from "next/navigation";
import {
  useGetUserSettingsQuery,
  useUpdateUserSettingsMutation,
} from "@/store/services/userApi";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTranslations } from "next-intl";
import { Languages } from "lucide-react";
import { languages } from "@/constants";
import { cn } from "@/lib/utils";
interface LayoutProps {
  children: React.ReactNode;
  childrenClassName?: string;
}

export default function Layout({ childrenClassName, children }: LayoutProps) {
  const pathname = usePathname();
  const t = useTranslations();
  const { data: userSettings } = useGetUserSettingsQuery({});
  const [updateUserSettings] = useUpdateUserSettingsMutation();

  if (pathname?.includes("/chat")) {
    return children;
  }

  const handleLanguageChange = async (language: string) => {
    try {
      await updateUserSettings({ language });
      // Reload the page to apply the new language
      window.location.reload();
    } catch (error) {
      console.error("Failed to update language:", error);
    }
  };

  return (
    <div className="flex flex-col h-screen home-tour-start">
      {/* Main content area */}
      <div className="flex-1 overflow-x-hidden overflow-y-auto">
        {pathname === "/home" && (
          <div className="flex justify-end p-4">
            <Select
              value={userSettings?.language || "en"}
              onValueChange={handleLanguageChange}
            >
              <SelectTrigger
                className="w-fit h-8 border-transparent hover:border-input"
                showIcon={false}
              >
                {/* language icon  */}
                {/* <Languages className="w-4 h-4 mr-1" /> */}

                <SelectValue placeholder="Select language" />
              </SelectTrigger>
              <SelectContent align="end">
                {languages.map((language) => (
                  <SelectItem key={language.value} value={language.value}>
                    <span className="mr-2">{language.icon}</span>
                    {language.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <div
          className={cn(
            `pt-6 mx-auto max-w-7xl sm:px-6 lg:px-8 min-h-screen ${childrenClassName}`,
            pathname.includes("/settings") && "max-w-full"
          )}
        >
          {children}
        </div>
      </div>
      <Toaster />
    </div>
  );
}
