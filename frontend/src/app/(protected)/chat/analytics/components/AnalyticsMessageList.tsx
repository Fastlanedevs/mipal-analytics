import React, { useEffect, useRef } from "react";
import { Message, Suggestion, Attachment } from "../../types/chat";
import { MessageItem } from "../../components/MessageItem";
import { useParams } from "next/navigation";
import { useTheme } from "@/contexts/ThemeContext";
import { FileSpreadsheet, BarChart, Database, Table } from "lucide-react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "@/store/store";
import { cn } from "@/lib/utils";
import {
  setSelectedArtifactMessageContent,
  setSelectedArtifactMessageId,
} from "@/store/slices/chatSlice";
import { LoadingMessageSkeleton } from "../../components/LoadingMessageSkeleton";
import { useTranslations } from "next-intl";

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  onSuggestionSelect: (suggestion: Suggestion) => void;
  selectedSuggestions: Suggestion[];
  currentLeafMessageId?: string;
  onAttachmentClick?: (attachment: Attachment) => void;
  isSetupComplete?: boolean;
  isInitialMessageSent?: boolean;
  isLoadingConversation?: boolean;
}

export const AnalyticsMessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  isStreaming,
  onSuggestionSelect,
  selectedSuggestions,
  currentLeafMessageId,
  onAttachmentClick,
  isSetupComplete,
  isInitialMessageSent,
  isLoadingConversation,
}) => {
  const t = useTranslations("chatPage.analytics.messageList");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();
  const chat = useSelector((state: RootState) => state.chat);
  const dispatch = useDispatch();
  const { selectedDatabase, selectedTable } = useSelector(
    (state: RootState) => state.analytics
  );

  useEffect(() => {
    if (shouldAutoScrollRef.current && messagesEndRef.current) {
      // Clear existing timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }

      // Debounce the scroll
      scrollTimeoutRef.current = setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  }, [messages.length]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  if (isLoadingConversation) {
    return (
      <div className="space-y-8 pt-12">
        <LoadingMessageSkeleton />
      </div>
    );
  }

  if (!chat?.activeConversationId && chat?.conversations?.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 space-y-6">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
          <BarChart className="w-8 h-8 text-primary" />
        </div>
        <div className="space-y-2 text-center max-w-md">
          <h3 className="text-lg font-semibold">
            {t("welcomeToAnalyticsPAL")}
          </h3>
          <p className="text-muted-foreground text-sm leading-relaxed">
            {t("getStarted")}
          </p>
        </div>
        <div className="flex flex-col items-center gap-6 text-sm text-muted-foreground mt-4">
          <div className="flex flex-col items-center gap-4">
            <div className="flex items-center gap-2">
              {
                <div
                  className={cn(
                    "flex gap-5 items-center",
                    !selectedDatabase &&
                      "bg-muted/90 dark:bg-subtle-bg/90 p-2 rounded-md border border-muted-foreground/20"
                  )}
                >
                  <span className="flex items-center gap-2">
                    <Database className="w-4 h-4" />
                    {t("connectToDatabase")}
                  </span>
                </div>
              }
            </div>
            <span>↓</span>
            <div
              className={cn(
                "flex items-center gap-2",
                selectedDatabase &&
                  selectedDatabase?.type !== "postgres" &&
                  !selectedTable &&
                  "bg-muted/90 dark:bg-subtle-bg/90 p-2 rounded-md border border-muted-foreground/20"
              )}
            >
              <Table className="w-4 h-4" />
              <span>{t("selectTables")}</span>
            </div>
            <span>↓</span>
            <div
              className={cn(
                "flex items-center gap-2",
                (selectedDatabase?.type === "postgres" || selectedTable) &&
                  "bg-muted/90 dark:bg-subtle-bg/90 p-2 rounded-md border border-muted-foreground/20"
              )}
            >
              <BarChart className="w-4 h-4" />
              <span>{t("askQuestionsOrSelectSuggestions")}</span>
            </div>
          </div>
          <p className="text-xs text-center max-w-sm">
            {t("youCanAlsoSelectFromSuggestedQueriesInTheBottomOfRightPanel")}
          </p>
        </div>
      </div>
    );
  }

  // Handle empty state
  if (!messages || messages.length === 0) {
    return (
      <div className="space-y-4">
        {!isSetupComplete && isInitialMessageSent && (
          <div className="space-y-6 px-4">
            <div className="flex items-center justify-center gap-2 py-2">
              <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:-0.3s]" />
              <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:-0.15s]" />
              <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce" />
            </div>
            <p className="text-center text-muted-foreground w-full text-sm font-medium">
              {t("settingUpNewConversation")}
            </p>
            {/* Loading Message Skeletons */}
            <LoadingMessageSkeleton />
          </div>
        )}
      </div>
    );
  }

  const handleArtifactUserMessage = (messageId: string) => {
    // Find the index of the message
    const index = messages.findIndex((message) => message.id === messageId);
    // set the previous user message content to the selected artifact message content
    dispatch(
      setSelectedArtifactMessageContent(
        messages[index - 1].content.slice(0, 99)
      )
    );
    dispatch(setSelectedArtifactMessageId(messageId));
  };

  return (
    <div className="space-y-4">
      <div className="h-6 md:hidden" />
      {messages.map((message, index) => (
        <MessageItem
          key={message.id}
          message={message}
          onSuggestionSelect={onSuggestionSelect}
          selectedSuggestions={selectedSuggestions}
          isLastMessage={index === messages.length - 1}
          showCursor={isLoading && index === messages.length - 1}
          isCurrentLeaf={message.id === currentLeafMessageId}
          onAttachmentClick={onAttachmentClick}
          isStreaming={isStreaming && index === messages.length - 1}
          handleArtifactUserMessage={handleArtifactUserMessage}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};
