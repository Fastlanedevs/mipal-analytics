"use client";

import React from "react";
import { History, ChevronRight } from "lucide-react";
import { AnalyticsSuggestions } from "./AnalyticsSuggestions";
import { ChatConversation } from "../../types/chat";
import { motion } from "framer-motion";
import { DataSourceSelector } from "./DataSourceSelector";
import { RootState } from "@/store/store";
import { useSelector } from "react-redux";
import { usePathname, useRouter } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { useGetRecentConversationsQuery } from "@/store/services/chatApi";
import { PalEnum } from "@/app/(protected)/_pals/PalConstants";
import { useTranslations } from "next-intl";
import { cn, thinHorizontalScrollbar } from "@/lib/utils";

export const AnalyticsPanel: React.FC = () => {
  const t = useTranslations("chatPage.analyticsPal.artifactPanel");
  const {
    selectedDatabase,
    selectedTable,
    isLoading: databasesLoading,
  } = useSelector((state: RootState) => state.analytics);

  const pathname = usePathname();

  const router = useRouter();

  const { data: recentConversations, isLoading: conversationsLoading } =
    useGetRecentConversationsQuery(PalEnum.ANALYST_PAL);

  return (
    <div
      className={cn(
        "container p-4 sm:px-6 sm:pb-6 sm:pt-0 mx-auto h-full overflow-auto",
        thinHorizontalScrollbar(2.5)
      )}
    >
      <div className="max-w-6xl mx-auto transition-all duration-300 space-y-3 min-w-[500px]">
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4 sm:gap-0 sm:pt-6">
          <div className="flex flex-col items-start gap-2 sm:gap-4 flex-1">
            <div className="flex flex-row justify-between w-full gap-2">
              <h2 className="text-lg sm:text-xl font-semibold">
                Analytics PAL
              </h2>
              <div className="flex items-center gap-2 sm:gap-3 w-full sm:w-auto flex-row">
                <Select
                  onValueChange={(value) => {
                    router.push(`/chat/analytics/${value}`);
                  }}
                >
                  <SelectTrigger className="max-w-[160px] min-w-[160px] truncate">
                    <History className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">{t("history")}</span>
                  </SelectTrigger>
                  <SelectContent className="z-[200]" align="end">
                    {conversationsLoading ? (
                      <SelectItem value="loading" disabled>
                        {t("loading")}
                      </SelectItem>
                    ) : (
                      recentConversations?.conversations?.map(
                        (conversation: ChatConversation) => {
                          if (pathname?.includes(conversation.id)) return;
                          return (
                            <SelectItem
                              key={conversation.id}
                              value={conversation.id}
                              className="flex flex-row items-center gap-2 max-w-[270px] w-full"
                              title={
                                conversation.name || `Chat ${conversation.id}`
                              }
                            >
                              <span className="flex-1 flex flex-row items-center gap-2">
                                <p className="truncate line-clamp-1 max-w-[200px] w-full">
                                  {conversation.name ||
                                    `Chat ${conversation.id}`}
                                </p>
                                <ChevronRight className="w-4 h-4" />
                              </span>
                            </SelectItem>
                          );
                        }
                      )
                    )}
                    {!conversationsLoading &&
                      (!recentConversations ||
                        recentConversations.conversations.length === 0) && (
                        <SelectItem value="empty" disabled>
                          {t("noConversationsYet")}
                        </SelectItem>
                      )}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </div>

        {/* Data Source Selector */}
        <DataSourceSelector />

        {/* Analytics Visualization */}
        <motion.div
          initial={false}
          animate={{
            y: selectedDatabase ? 0 : 20,
            opacity: selectedDatabase ? 1 : 0.7,
          }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="analytics-visualization"
        >
          <AnalyticsSuggestions />
        </motion.div>
      </div>
    </div>
  );
};
