import React, { useEffect, useRef } from "react";
import { Message, Suggestion, ContentBlock, Attachment } from "../types/chat";
import { MessageItem } from "./MessageItem";
import { useParams } from "next/navigation";
import { useTheme } from "@/contexts/ThemeContext";
import { File as FileIcon } from "lucide-react";
import { useTranslations } from "next-intl";

const LoadingLogo = () => {
  const { theme } = useTheme();
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 60 60"
      className="w-8 h-8"
    >
      <rect
        x="5"
        y="5"
        width="50"
        height="50"
        rx="10"
        fill={isDark ? "#ffffff" : "#000000"}
        className="animate-pulse"
      />
      <text
        x="12"
        y="42"
        className="text"
        fontSize="30"
        fill={isDark ? "#000000" : "#ffffff"}
      >
        MI
      </text>
    </svg>
  );
};

const LoadingMessage = () => (
  <div className="flex items-center gap-4 p-4 bg-muted/50 dark:bg-subtle-bg/60">
    <LoadingLogo />
    <div className="space-y-2">
      <div className="w-24 h-4 rounded bg-muted/50 dark:bg-subtle-hover/50 animate-pulse" />
      <div className="w-64 h-4 rounded bg-muted/50 dark:bg-subtle-hover/50 animate-pulse" />
    </div>
  </div>
);

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  onSuggestionSelect: (suggestion: Suggestion) => void;
  selectedSuggestions: Suggestion[];
  currentLeafMessageId?: string;
  onAttachmentClick?: (attachment: Attachment) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  isStreaming,
  onSuggestionSelect,
  selectedSuggestions,
  currentLeafMessageId,
  onAttachmentClick,
}) => {
  const t = useTranslations("chatPage.messagesList");
  const params = useParams();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);

  useEffect(() => {
    if (shouldAutoScrollRef.current && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length]);

  // Handle empty state
  if (!messages || messages.length === 0) {
    return (
      <div className="space-y-4">
        {isLoading || params?.id ? (
          <div className="flex flex-col items-center justify-center py-8 space-y-3">
            <LoadingLogo />
            <span className="text-muted-foreground dark:text-subtle-fg">
              {t("loadingConversation")}
            </span>
          </div>
        ) : (
          <div className="py-8 text-center text-muted-foreground dark:text-subtle-fg">
            {t("startConversation")}
          </div>
        )}
      </div>
    );
  }

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
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};
