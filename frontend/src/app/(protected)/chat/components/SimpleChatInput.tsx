import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ArrowUp, Globe, Loader2, Paperclip, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import TextareaAutosize from "react-textarea-autosize";

interface SimpleChatInputProps {
  onSendMessage: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
  isLoading?: boolean;
}

export const SimpleChatInput: React.FC<SimpleChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Reply to MI PAL...",
  isLoading = false,
}) => {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && !isLoading) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (message.trim() && !disabled && !isLoading) {
        onSendMessage(message.trim());
        setMessage("");
      }
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="relative w-full max-w-[800px] mx-auto flex flex-col gap-5"
    >
      <div
        className={cn(
          "relative flex items-end w-full gap-2 bg-background dark:bg-subtle-bg/30 rounded-2xl border dark:border-subtle-border transition-all duration-200 overflow-hidden",
          (disabled || isLoading) && "opacity-70"
        )}
      >
        <div className="flex flex-col gap-2 w-full px-5 py-3">
          {/* Textarea */}
          <div className="flex-1 w-full">
            <TextareaAutosize
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isLoading ? "Generating questions..." : placeholder}
              disabled={disabled || isLoading}
              className={cn(
                "flex-1 resize-none !bg-transparent min-h-[64px] !rounded-none w-full !outline-none",
                "text-sm placeholder:text-muted-foreground dark:placeholder:text-subtle-fg/50",
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
          {/* <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl"
              onClick={() => console.log("clicked")}
              disabled={disabled}
            >
              <Paperclip className="w-5 h-5" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl"
              onClick={() => console.log("clicked")}
            >
              <Search className="w-5 h-5" />
            </Button>
            <div className="relative group">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className={cn(
                  "h-8 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl left-10"
                )}
                // style={{
                //   color: webSearchEnabled ? "#2563eb" : "",
                // }}
                onClick={() => console.log("clicked")}
              >
                <Globe className="w-5 h-5" />
              </Button>
              <div className="absolute bottom-full left-12 -translate-x-1/2 mb-2 hidden group-hover:block z-50">
                <div className="bg-popover text-popover-foreground px-3 py-1.5 rounded-md text-sm whitespace-nowrap shadow-md transform origin-bottom">
                  Web search
                </div>
              </div>
            </div>
          </div> */}
        </div>

        {/* Send Button */}
        <Button
          type="submit"
          size="icon"
          disabled={!message || !message.trim() || disabled || isLoading}
          className={cn(
            "absolute right-3 bottom-3 h-8 w-8 md:right-4 md:bottom-4 md:h-9 md:w-9 rounded-xl",
            "bg-primary hover:bg-primary/90 dark:bg-primary/90 dark:hover:bg-primary",
            "disabled:bg-muted-foreground/60 dark:disabled:bg-subtle-fg/20",
            "transition-colors duration-200"
          )}
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 text-primary-foreground animate-spin" />
          ) : (
            <ArrowUp className="w-5 h-5 text-primary-foreground" />
          )}
        </Button>
      </div>
    </form>
  );
};
