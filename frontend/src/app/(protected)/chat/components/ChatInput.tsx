import React, { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Paperclip, ArrowUp, X, Search, Globe, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { Suggestion } from "../types/chat";
import TextareaAutosize from "react-textarea-autosize";
import { useSelector, useDispatch } from "react-redux";
// import { setSelectedSuggestion } from "@/store/slices/intentsSlice";
import { RootState } from "@/store/store";
import { setSelectedSuggestion } from "@/store/slices/intentsSlice";
import { useTranslations } from "next-intl";
import { PalEnum } from "../../_pals/PalConstants";
import { clearModel, setModel } from "@/store/slices/chatSlice";
import { useAppSelector } from "@/store/hooks";
import { useGetPalsQuery } from "@/store/services/palApi";

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  disabled?: boolean;
  onAttachmentClick?: () => void;
  selectedSuggestions?: Suggestion[];
  onRemoveSuggestion?: (suggestion: Suggestion) => void;
  hasFiles?: boolean;
  onFilesDrop?: (files: File[]) => void;
  isProcessingFiles?: boolean;
  setIsSearchOpen?: (isSearchOpen: boolean) => void | undefined;
  webSearchEnabled?: boolean;
  setWebSearchEnabled?: (webSearchEnabled: boolean) => void;
  isAnalytics?: boolean;
  maxWidth?: number;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled,
  onAttachmentClick,
  selectedSuggestions,
  onRemoveSuggestion,
  hasFiles,
  onFilesDrop,
  isProcessingFiles = false,
  setIsSearchOpen,
  webSearchEnabled = false,
  setWebSearchEnabled,
  isAnalytics = false,
  maxWidth,
}) => {
  const t = useTranslations("chatPage.chatInput");
  const [message, setMessage] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dragCounter = useRef(0);
  const dispatch = useDispatch();
  const selectedSuggestion = useSelector(
    (state: RootState) => state.intents.selectedSuggestion
  );

  const { data: pals } = useGetPalsQuery();

  // const activeKnowledgePal = useAppSelector(
  //   (state: RootState) => state.chatCreation.model
  // );

  const knowledgePal = pals?.find(
    (pal) => pal.pal_enum === PalEnum.KNOWLEDGE_PAL
  );

  const chatModel = useAppSelector((state: RootState) => state.chat.model);

  // useEffect(() => {
  //   setTimeout(() => {
  //     if (!chatModel && activeKnowledgePal === PalEnum.KNOWLEDGE_PAL) {
  //       dispatch(setModel(PalEnum.KNOWLEDGE_PAL));
  //     }
  //   }, 500);
  // }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (message.trim() && !disabled) {
        onSendMessage(message.trim());
        setMessage("");
      }
    }
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current += 1;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current -= 1;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounter.current = 0;

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0 && onFilesDrop) {
      onFilesDrop(files);
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const container = e.currentTarget;
    container.scrollLeft += e.deltaY;
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  useEffect(() => {
    // In Analytics chat, if an intent is selected, set the message to the suggestion text
    if (isAnalytics && selectedSuggestion) {
      setMessage(selectedSuggestion?.question);
    }
  }, [selectedSuggestion]);

  useEffect(() => {
    // In Analytics chat, if a message is changed is different from the selected intent, clear the selected suggestion
    if (
      isAnalytics &&
      message?.length > 0 &&
      selectedSuggestion?.question !== message.trim()
    ) {
      dispatch(setSelectedSuggestion(null));
    }
  }, [message]);

  const getSuggestionLabel = (suggestion: Suggestion): string => {
    if (!suggestion || !suggestion.suggestion_content) {
      return "Invalid suggestion";
    }

    const content = suggestion.suggestion_content;

    switch (suggestion.type) {
      case "Document":
        return "title" in content ? content.title : "Untitled Document";

      case "Person":
        return "Name" in content ? content.Name : "Unknown Person";

      case "PAL":
        if ("title" in content) {
          return content.title;
        }
        if (
          "description" in content &&
          typeof content.description === "string"
        ) {
          return content.description;
        }
        return "PAL Reference";

      case "Text":
        return "text" in content ? content.text : "Text Reference";

      default:
        return `${suggestion.type} Reference`;
    }
  };

  const handleKnowledgePalClick = () => {
    if (chatModel === PalEnum.KNOWLEDGE_PAL) {
      dispatch(clearModel());
    } else {
      dispatch(setModel(PalEnum.KNOWLEDGE_PAL));
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={`relative w-full max-w-[${maxWidth}px] mx-auto flex flex-col gap-5`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div
        className={cn(
          "relative flex items-end w-full gap-2 bg-background dark:bg-subtle-bg/30 rounded-2xl border dark:border-subtle-border transition-all duration-200 overflow-hidden",
          isDragging &&
            !isAnalytics &&
            "border-primary/50 dark:border-primary/50 bg-primary/5 dark:bg-primary/5",
          isProcessingFiles && "opacity-70",
          isAnalytics && "analytics-query-input"
        )}
      >
        {isDragging && !isAnalytics && (
          <div className="absolute inset-0 z-10 flex items-center justify-center overflow-hidden border-2 border-dashed rounded-2xl bg-primary/5 dark:bg-primary/5 border-primary/50 dark:border-primary/50">
            <div className="flex items-center gap-2 text-primary/70 dark:text-primary/70">
              <Paperclip className="w-5 h-5" />
              <span>{t("dropFilesToUpload")}</span>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-2 w-full px-5 py-3">
          {/* Textarea */}
          <div className="flex-1 w-full">
            <TextareaAutosize
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isProcessingFiles ? t("processingFiles") : t("replyToMI")
              }
              disabled={disabled || isProcessingFiles}
              className={cn(
                "flex-1 resize-none !bg-transparent min-h-[64px] !rounded-none w-full !outline-none",
                "text-base placeholder:text-muted-foreground dark:placeholder:text-subtle-fg/50",
                "focus:outline-none focus:ring-0 disabled:opacity-50",
                "scrollbar-thin scrollbar-thumb-muted-foreground/10 hover:scrollbar-thumb-muted-foreground/20 dark:scrollbar-thumb-subtle-fg/10 dark:hover:scrollbar-thumb-subtle-fg/20"
              )}
              style={{
                borderRadius: "1rem",
                WebkitBorderRadius: "1rem",
              }}
              maxRows={8}
            />
          </div>

          <div className="flex gap-1">
            {/* Attachment Button */}
            {!isAnalytics && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl"
                onClick={onAttachmentClick}
                disabled={disabled}
              >
                <Paperclip className="w-5 h-5" />
              </Button>
            )}
            {/* Search Button */}
            {!isAnalytics && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl"
                onClick={() => setIsSearchOpen?.(true)}
              >
                <Search className="w-5 h-5" />
              </Button>
            )}
            {/* Web Search Button */}
            <div className="relative group">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className={cn(
                  "h-8 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl left-10"
                )}
                style={{
                  color: webSearchEnabled ? "#2563eb" : "",
                }}
                onClick={() => setWebSearchEnabled?.(!webSearchEnabled)}
              >
                <Globe className="w-5 h-5" />
              </Button>
              <div className="absolute bottom-full left-12 -translate-x-1/2 mb-2 hidden group-hover:block z-50">
                <div className="bg-popover text-popover-foreground px-3 py-1.5 rounded-md text-sm whitespace-nowrap shadow-md transform origin-bottom">
                  {t("webSearch")}
                </div>
              </div>
            </div>
            {/* Knowledge Pal Button */}
            {!isAnalytics && knowledgePal && (
              <div className="relative group">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-8 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl left-10"
                  )}
                  style={{
                    color: chatModel === PalEnum.KNOWLEDGE_PAL ? "#2563eb" : "",
                  }}
                  onClick={handleKnowledgePalClick}
                >
                  <BookOpen className="w-5 h-5" />
                </Button>
                <div className="absolute bottom-full left-12 -translate-x-1/2 mb-2 hidden group-hover:block z-50">
                  <div className="bg-popover text-popover-foreground px-3 py-1.5 rounded-md text-sm whitespace-nowrap shadow-md transform origin-bottom">
                    Knowledge Pal
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Send Button */}
        <Button
          type="submit"
          size="icon"
          disabled={
            !message || !message.trim() || disabled || isProcessingFiles
          }
          className={cn(
            "absolute right-3 bottom-3 h-8 w-8 md:right-4 md:bottom-4 md:h-9 md:w-9 rounded-xl",
            "bg-primary hover:bg-primary/90 dark:bg-primary/90 dark:hover:bg-primary",
            "disabled:bg-muted-foreground/60 dark:disabled:bg-subtle-fg/20",
            "transition-colors duration-200"
          )}
        >
          <ArrowUp className="w-5 h-5 text-primary-foreground" />
        </Button>
      </div>

      {/* Selected Suggestions */}
      {selectedSuggestions && selectedSuggestions.length > 0 && (
        <div className="relative">
          <div
            className={cn(
              "flex flex-row flex-nowrap gap-2 overflow-x-auto",
              // Custom scrollbar styles
              "[&::-webkit-scrollbar]:h-1.5",
              "[&::-webkit-scrollbar-track]:bg-transparent",
              "[&::-webkit-scrollbar-thumb]:bg-muted-foreground/20",
              "[&::-webkit-scrollbar-thumb]:hover:bg-muted-foreground/30",
              "[&::-webkit-scrollbar-thumb]:rounded-full",
              "scroll-px-2",
              // Add padding for scrollbar
              "pb-3"
            )}
            onWheel={handleWheel}
          >
            {selectedSuggestions.map((suggestion, index) => (
              <div
                key={index}
                className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 text-sm rounded-xl bg-primary/10 text-primary dark:bg-primary/20 whitespace-nowrap"
              >
                <span className="truncate max-w-[200px]">
                  {getSuggestionLabel(suggestion)}
                </span>
                <button
                  type="button"
                  onClick={() => onRemoveSuggestion?.(suggestion)}
                  className="text-primary hover:text-primary/70 bg-foreground/20 p-1 rounded-full"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </form>
  );
};
