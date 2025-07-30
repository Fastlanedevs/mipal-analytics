"use client";

import { Button } from "@/components/ui/button";
import {
  User,
  Wallet,
  LogOut,
} from "lucide-react";
import { useRouter, usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useGetUserProfileQuery } from "@/store/services/userApi";
import { signOut } from "next-auth/react";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("settings");

  const { data: userProfile } = useGetUserProfileQuery({});

  return (
    <div className="flex flex-col md:flex-row h-[calc(100vh-4rem)] mt-9 md:mt-0">
      {/* Sidebar Navigation - Hidden scrollbar */}
      <div className="w-full md:w-64 border-b md:border-b-0 dark:border-subtle-border shrink-0 rounded-lg">
        <div className="p-4 md:p-6">
          <h1 className="text-xl md:text-2xl font-semibold mb-4 md:mb-6 dark:text-subtle-fg">
            {t("title")}
          </h1>
          <div className="flex md:flex-col space-x-2 md:space-x-0 md:space-y-2 overflow-x-auto scrollbar-hide md:overflow-x-visible">
            <Button
              variant="ghost"
              className={`justify-start flex-shrink-0 md:w-full ${
                pathname === "/settings/profile"
                  ? "bg-primary-foreground dark:bg-foreground dark:text-background"
                  : "dark:hover:bg-foreground dark:hover:text-background"
              }`}
              onClick={() => router.push("/settings/profile")}
            >
              <User className="w-4 h-4 mr-2" />
              {t("navigation.profile")}
            </Button>
           
       
            {!userProfile?.organisation?.id && (
              <Button
                variant="ghost"
                className={`justify-start flex-shrink-0 md:w-full dark:hover:bg-foreground dark:hover:text-background`}
                onClick={() => {
                  signOut();
                }}
              >
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Content Area - Scrollable with custom scrollbar */}
      <div className="flex-1 overflow-y-auto [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/20 [&::-webkit-scrollbar-thumb]:rounded-full">
        <div className="h-full">{children}</div>
      </div>
    </div>
  );
}
