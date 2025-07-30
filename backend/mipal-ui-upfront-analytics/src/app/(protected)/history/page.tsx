"use client";
import React, { useState } from "react";
import { useGetRecentConversationsQuery } from "@/store/services/chatApi";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { ChatConversation } from "../chat/types/chat";
import { useAppDispatch } from "@/store/hooks";
import { MessagesSquare, Search } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { PalEnum } from "../_pals/PalConstants";
import { resetAnalytics } from "@/store/slices/analyticsSlice";
import { resetToInitialChatState } from "@/store/slices/chatSlice";
import { removeArtifacts } from "@/store/slices/artifactsSlice";
import { useTranslations } from "next-intl";

const HistoryPage = () => {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [searchQuery, setSearchQuery] = useState("");
  const t = useTranslations("history");
  const {
    data: recentConversations,
    isLoading,
    error,
  } = useGetRecentConversationsQuery();

  const handleRecentConversationsClick = (conversation: ChatConversation) => {
    dispatch(resetAnalytics());
    dispatch(removeArtifacts());
    dispatch(resetToInitialChatState());
    if (conversation.model === PalEnum.ANALYST_PAL) {
      router.push(`/chat/analytics/${conversation.id}`);
    } else {
      router.push(`/chat/${conversation.id}`);
    }
  };

  const filteredConversations = recentConversations?.conversations?.filter(
    (conversation: ChatConversation) =>
      conversation.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conversation.model?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 mx-auto max-w-7xl sm:px-6 lg:px-6 h-full">
      <div className="">
        <PageHeader
          title={t("chatHistory")}
          description={t("viewAndSearchYourPastConversations")}
          className="mb-8"
          // actions={
          //   <Button
          //     onClick={() => router.push("/home")}
          //     className="items-center gap-2 h-11"
          //   >
          //     <MessagesSquare size={18} />
          //     {t("newChat")}
          //   </Button>
          // }
          isLoading={isLoading}
        />

        <div className="mb-8">
          <div className="relative max-w-2xl mx-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              type="text"
              placeholder={t("searchConversations")}
              className="w-full pl-10 h-12 bg-background border-border rounded-xl"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="pb-8">
        <div className="space-y-4 max-w-2xl mx-auto">
          {error && (
            <p className="text-center py-12 text-red-500">
              {t("errorLoadingConversations")}
            </p>
          )}
          {!isLoading &&
            filteredConversations?.map((conversation: ChatConversation) => (
              <Card
                key={conversation.id}
                className="p-4 hover:shadow-md transition-all duration-200 group cursor-pointer flex flex-col gap-2"
                onClick={() => handleRecentConversationsClick(conversation)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-start gap-2">
                    <span className="w-4 h-4 text-muted-foreground pt-1">
                      <MessagesSquare className="w-4 h-4 text-muted-foreground" />
                    </span>
                    <h2 className="text-md font-medium group-hover:text-primary transition-colors line-clamp-2">
                      {conversation.name || "Untitled"}
                    </h2>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(conversation?.updated_at)}
                  </span>
                </div>
                {conversation?.model && (
                  <div className="flex gap-2 items-center">
                    <Badge variant="secondary" className="text-xs font-normal">
                      {conversation?.model?.replace(/_/g, " ")}
                    </Badge>
                  </div>
                )}
              </Card>
            ))}
          {!isLoading && filteredConversations?.length === 0 && (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                {t("noConversationsFound")}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
