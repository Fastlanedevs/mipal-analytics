import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useRef,
} from "react";
import type {
  Message,
  Suggestion,
  ContentBlock,
  Artifact,
  IntentContent,
} from "../types/chat";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import { SuggestionList } from "./SuggestionList";
import {
  FileText,
  Image,
  File as FileIcon,
  Link,
  Eye,
  ChartBar,
  ArrowRight,
  BookOpen,
  Copy,
  Check,
  CircleAlert,
} from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";
import { useUser } from "@/store/hooks/useUser";
import { useDispatch, useSelector } from "react-redux";
import {
  removeArtifacts,
  setArtifacts,
  setIsArtifactPanelOpen,
} from "@/store/slices/artifactsSlice";
import {
  setReferences,
  setIsReferencePanelOpen,
} from "@/store/slices/referencesSlice";
import { RootState } from "@/store/store";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import MetaContent from "./MetaContent";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { tokenLimitsReached } from "@/constants/pricing";
import { useAppSelector } from "@/store/hooks";
import { PalEnum } from "../../_pals/PalConstants";
import MessageContentRenderer from "./MessageContentRenderer";

// Define the CodeProps interface
interface CodeProps {
  node?: any;
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
}

interface MessageItemProps {
  message: Message;
  onSuggestionSelect: (suggestion: Suggestion) => void;
  selectedSuggestions: Suggestion[];
  isLastMessage: boolean;
  showCursor: boolean;
  isCurrentLeaf: boolean;
  onAttachmentClick?: (attachment: Attachment) => void;
  isStreaming: boolean;
  handleArtifactUserMessage?: (messageId: string) => void;
}

// Add the getFileIcon function
const getFileIcon = (fileType: string) => {
  if (fileType.startsWith("image/")) {
    return <Image className="w-4 h-4" />;
  } else if (
    fileType.includes("text") ||
    fileType.includes("json") ||
    fileType.includes("markdown")
  ) {
    return <FileText className="w-4 h-4" />;
  }
  return <FileIcon className="w-4 h-4" />;
};

// Add this type guard before the handleSuggestionSelect function
const isIntentContent = (
  content: any
): content is IntentContent[] | IntentContent => {
  return (
    content &&
    typeof content === "object" &&
    "title" in content &&
    "text" in content &&
    typeof content.text === "string"
  );
};

const MipalAvatar = () => {
  const { theme } = useTheme();
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  return (
    <div className="flex-shrink-0 flex items-center gap-2 mt-1">
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
        />
        <text
          x="12"
          y="42"
          className="text-primary"
          fontSize="30"
          fill={isDark ? "#000000" : "#ffffff"}
        >
          MI
        </text>
      </svg>
      {/* <span className="font-medium">MI PAL</span> */}
    </div>
  );
};

const UserAvatar: React.FC = () => {
  const { user } = useUser();
  const name = user?.name || "User";

  const initials = name
    .split(" ")
    .map((part: string) => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="flex-shrink-0 flex items-center gap-2 mt-1">
      {/* <span className="font-semibold">{user?.name ?? "User"}</span> */}
      <div className="flex items-center justify-center flex-shrink-0 w-8 h-8 rounded-full bg-input dark:bg-subtle-bg-secondary text-primary">
        <span className="text-sm font-medium">{initials}</span>
      </div>
    </div>
  );
};

const AttachmentList: React.FC<{ attachments: Attachment[] }> = ({
  attachments,
}) => {
  const getFileIcon = (fileType: string) => {
    if (fileType.startsWith("image/")) {
      return <Image className="w-4 h-4" />;
    } else if (
      fileType.includes("text") ||
      fileType.includes("json") ||
      fileType.includes("markdown")
    ) {
      return <FileText className="w-4 h-4" />;
    }
    return <FileIcon className="w-4 h-4" />;
  };

  return (
    <div className="mt-2 space-y-2">
      {attachments.map((attachment, index) => (
        <div
          key={index}
          className="flex items-center gap-2 p-2 text-sm rounded-md bg-gray-50"
        >
          {getFileIcon(attachment.file_type)}
          <span className="font-medium">{attachment.file_name}</span>
          <span className="text-xs text-gray-500">
            ({Math.round(attachment.file_size / 1024)}KB)
          </span>
        </div>
      ))}
    </div>
  );
};

const SelectedSuggestionsList: React.FC<{ suggestions: Suggestion[] }> = ({
  suggestions,
}) => {
  const renderSuggestionContent = (suggestion: Suggestion) => {
    switch (suggestion.type) {
      case "Document": {
        const doc = suggestion.suggestion_content as DocumentContent;
        return (
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <span className="font-medium">{doc.title}</span>
            {doc.source_url && (
              <a
                href={doc.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto text-blue-600 hover:underline"
              >
                <Link className="w-3 h-3" />
              </a>
            )}
          </div>
        );
      }
      case "Person": {
        const person = suggestion.suggestion_content as PersonContent;
        return (
          <div className="flex items-center gap-2">
            {person.image ? (
              <img
                src={person.image}
                alt={person.Name}
                className="w-4 h-4 rounded-full"
              />
            ) : (
              <div className="w-4 h-4 bg-gray-200 rounded-full" />
            )}
            <span className="font-medium">{person.Name}</span>
            {person.Position && (
              <span className="text-sm text-gray-500">({person.Position})</span>
            )}
          </div>
        );
      }
      case "PAL": {
        const pal = suggestion.suggestion_content as PALContent;
        return (
          <div className="flex items-center gap-2">
            <Image className="w-4 h-4 text-blue-600" />
            <span className="font-medium">{pal.title}</span>
          </div>
        );
      }
      case "Text": {
        const text = suggestion.suggestion_content as { text: string };
        return (
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <span className="font-medium">{text.text}</span>
          </div>
        );
      }
      default:
        return null;
    }
  };

  return (
    <div className="mt-2 space-y-1">
      <div className="text-xs font-medium text-gray-500">Referenced:</div>
      <div className="space-y-1">
        {suggestions.map((suggestion, index) => (
          <div key={index} className="text-sm p-1.5 bg-blue-50 rounded-md">
            {renderSuggestionContent(suggestion)}
          </div>
        ))}
      </div>
    </div>
  );
};

// Add type definitions for suggestion content
interface DocumentContent {
  title: string;
  description?: string;
  source_url?: string;
  type?: string;
  uploaded_by?: string;
}

interface PersonContent {
  Name: string;
  Position?: string;
  image?: string;
}

interface PALContent {
  title: string;
  description?: string;
  model?: string;
}

interface TextContent {
  text: string;
}

interface Attachment {
  file_name: string;
  file_size: number;
  file_type: string;
  extracted_content: string;
}

// Add type guard functions
const isDocumentContent = (content: any): content is DocumentContent => {
  return "title" in content && !("Name" in content) && !("text" in content);
};

const isPersonContent = (content: any): content is PersonContent => {
  return "Name" in content;
};

const isPALContent = (content: any): content is PALContent => {
  return "title" in content && "model" in content;
};

const isTextContent = (content: any): content is TextContent => {
  return "text" in content;
};

export interface LocalThinkingDescription {
  title: string;
  execution?: string;
  status: "completed" | "inprogress" | "pending" | "error";
  description?: string;
  nestedDescriptions?: LocalThinkingDescription[];
  showMetaContent?: boolean;
}

// New ThinkingIndicator component to display streaming meta content
const ThinkingIndicator = ({
  metaContent,
  message,
  showCompleted = false,
  showMetaContent = false,
}: {
  metaContent?: any[];
  message?: Message;
  showCompleted?: boolean;
  showMetaContent?: boolean;
}) => {
  const t = useTranslations("chatPage.messageItem.thinkingIndicator");
  const [showTyping, setShowTyping] = useState(false);

  // Only use meta content from the backend
  const displayContent = useMemo(() => {
    // If showCompleted is true, mark all steps as completed (when not streaming)
    return metaContent && metaContent.length > 0
      ? metaContent
          // First filter out duplicates based on title and id
          .reduce((acc: any[], current) => {
            // Find if we already have an object with the same title and id
            const existingIndex = acc.findIndex(
              (item) => item.title === current.title || item.id === current.id
            );

            if (existingIndex === -1) {
              // If no duplicate found, add the current object
              acc.push(current);
            } else {
              // If duplicate found, replace it with the current object (keeping the latest)
              acc[existingIndex] = current;
            }
            return acc;
          }, [])
          // Then process the filtered content
          .map((step) => {
            // Check if any description has error status
            const hasErrorInDescriptions = step?.description?.some(
              (desc: LocalThinkingDescription) => desc.status === "error"
            );

            // Set parent status to error if any description has error
            const finalStatus = hasErrorInDescriptions
              ? "error"
              : showCompleted
                ? "completed"
                : step.status;

            return {
              ...step,
              status: finalStatus,
              description:
                step?.description && step.description.length > 0
                  ? step.description.map((desc: LocalThinkingDescription) => ({
                      ...desc,
                      status:
                        desc.status === "error"
                          ? "error"
                          : showCompleted
                            ? "completed"
                            : desc.status,
                    }))
                  : [],
            };
          })
      : [];
  }, [metaContent]);

  // Show typing effect for all steps
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowTyping(true);
    }, 300);
    return () => clearTimeout(timer);
  }, []);

  const hasInProgressStep = useMemo(() => {
    return displayContent.some((step) => step.status === "inprogress");
  }, [displayContent]);

  // Count the completed steps
  const completedStepsCount = useMemo(() => {
    return displayContent.filter((step) => step.status === "completed").length;
  }, [displayContent]);

  // If there's no content from backend, show simple spinner
  if (displayContent.length === 0) {
    return <StreamingStatus />;
  }

  return (
    showMetaContent && (
      <div className="py-3 px-1">
        <div className="text-xs text-muted-foreground/70 mb-2 flex items-center gap-1">
          {!showCompleted && <LoadingSpinner size={12} />}
          <span className="text-primary">
            {hasInProgressStep
              ? t("processingYourRequest")
              : t("analysisComplete")}
          </span>
        </div>

        <div className="space-y-4 bg-background rounded-lg p-3 dark:bg-subtle-hover opacity-80 border border-muted-foreground/10">
          {displayContent.map((step, stepIndex) => (
            <MetaContent
              key={step.id || stepIndex}
              step={step}
              stepIndex={stepIndex}
              showTyping={showTyping}
              showCompleted={showCompleted}
            />
          ))}
        </div>

        {/* Progress bar at the bottom */}
        {!showCompleted && displayContent.length > 1 && (
          <div className="mt-3 bg-muted-foreground/10 h-1 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-primary"
              initial={{ width: "0%" }}
              animate={{
                width: `${
                  (completedStepsCount / displayContent.length) * 100
                }%`,
              }}
              transition={{ duration: 0.5 }}
            />
          </div>
        )}
      </div>
    )
  );
};

// Replace the existing ThinkingIndicator component
const StreamingStatus = () => {
  const t = useTranslations("chatPage.messageItem.thinkingIndicator");
  return (
    <div className=" text-sm text-muted-foreground dark:text-subtle-fg/70">
      <div className="flex items-center gap-2">
        <span className="relative inline-block">
          <span className="opacity-0">{t("thinking")}</span>
          <span
            className="absolute inset-0 bg-gradient-to-r from-primary/30 via-primary to-primary/30 bg-[length:300%_100%] bg-clip-text text-transparent animate-glare-text-delayed"
            style={{ WebkitBackgroundClip: "text" }}
          >
            {t("thinking")}
          </span>
        </span>
      </div>
    </div>
  );
};

// Add this function before the MessageItem component
const CopyButton = ({ content }: { content: string }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  return (
    <button
      onClick={copyToClipboard}
      className="absolute right-2 top-1 p-1.5 rounded-md bg-background/80 hover:bg-background/90 transition-colors opacity-0 group-hover:opacity-100 mr-2"
      aria-label="Copy code"
    >
      {copied ? (
        <Check className="w-4 h-4 text-green-500" />
      ) : (
        <Copy className="w-4 h-4 text-muted-foreground" />
      )}
    </button>
  );
};

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onSuggestionSelect,
  selectedSuggestions,
  isLastMessage,
  showCursor,
  isCurrentLeaf,
  onAttachmentClick,
  isStreaming,
  handleArtifactUserMessage,
}) => {
  const router = useRouter();
  const t = useTranslations("chatPage.messageItem");
  const t2 = useTranslations("sidebar");
  const isAssistant = message.role === "assistant";
  const dispatch = useDispatch();
  const isReferencePanelOpen = useSelector(
    (state: RootState) => state.references.isReferencePanelOpen
  );
  const pathname = usePathname();
  const isAnalytics = pathname.includes("/chat/analytics");
  const chatModel = useAppSelector((state: RootState) => state.chat.model);

  // Add renderSuggestionContent function inside the component
  const renderSuggestionContent = (suggestion: Suggestion) => {
    switch (suggestion.type) {
      case "Document": {
        if (!isDocumentContent(suggestion.suggestion_content)) return null;
        return (
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-500" />
            <span>{suggestion.suggestion_content.title}</span>
            {suggestion.suggestion_content.source_url && (
              <a
                href={suggestion.suggestion_content.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto text-blue-500 hover:underline"
              >
                <Link className="w-3 h-3" />
              </a>
            )}
          </div>
        );
      }
      case "Person": {
        if (!isPersonContent(suggestion.suggestion_content)) return null;
        return (
          <div className="flex items-center gap-2">
            {suggestion.suggestion_content.image ? (
              <img
                src={suggestion.suggestion_content.image}
                alt={suggestion.suggestion_content.Name}
                className="w-4 h-4 rounded-full"
              />
            ) : (
              <div className="w-4 h-4 bg-gray-200 rounded-full dark:bg-gray-700" />
            )}
            <span>{suggestion.suggestion_content.Name}</span>
            {suggestion.suggestion_content.Position && (
              <span className="text-sm text-muted-foreground dark:text-subtle-fg/70">
                ({suggestion.suggestion_content.Position})
              </span>
            )}
          </div>
        );
      }
      case "PAL": {
        if (!isPALContent(suggestion.suggestion_content)) return null;
        return (
          <div className="flex items-center gap-2">
            <Image className="w-4 h-4 text-blue-500" />
            <span>{suggestion.suggestion_content.title}</span>
          </div>
        );
      }
      case "Text": {
        if (!isTextContent(suggestion.suggestion_content)) return null;
        return (
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-500" />
            <span>{suggestion.suggestion_content.text}</span>
          </div>
        );
      }
      default:
        return null;
    }
  };

  // Extract suggestions from either stream or GET response format
  const getSuggestions = (message: Message): Suggestion[] => {
    // Handle stream format where suggestions are in content blocks
    if (Array.isArray(message.content)) {
      const suggestionBlock = message.content.find(
        (block) => block.type === "suggestions"
      );

      if (suggestionBlock?.suggestions) {
        return suggestionBlock.suggestions;
      }
    }

    // Handle GET response format where suggestions are directly in the message
    if (message.suggestions && Array.isArray(message.suggestions)) {
      return message.suggestions as Suggestion[];
    }

    return [];
  };

  const suggestions = getSuggestions(message);

  // const [isArtifactPanelOpen, setIsArtifactPanelOpen] = useState<boolean>(
  //   !!(isLastMessage && message.artifacts && message.artifacts.length > 0)
  // );

  const handleArtifactClick = (artifacts: Artifact[]) => {
    handleArtifactUserMessage && handleArtifactUserMessage(message.id);
    dispatch(setArtifacts(artifacts || []));
    dispatch(setIsArtifactPanelOpen(true));
  };

  useEffect(() => {
    if (isLastMessage) {
      // Handle artifacts
      if (message?.artifacts && message?.artifacts?.length > 0) {
        handleArtifactUserMessage && handleArtifactUserMessage(message.id);
        dispatch(setArtifacts(message.artifacts || []));
        dispatch(setIsArtifactPanelOpen(true));
      }

      // Handle references for KNOWLEDGE_PAL
      if (
        message?.model === "KNOWLEDGE_PAL" &&
        message?.references &&
        message?.references.length > 0
      ) {
        dispatch(setReferences(message.references));
        dispatch(setIsReferencePanelOpen(true));
      }
    }
  }, [isLastMessage, message?.artifacts, message?.references, message?.model]);

  // Add cleanup effect for references when pathname changes
  useEffect(() => {
    return () => {
      dispatch(setReferences([]));
      dispatch(setIsReferencePanelOpen(false));
      dispatch(removeArtifacts());
    };
  }, [pathname]);

  const handleArtifactViewButton = useCallback(() => {
    // Get metadata artifact
    const metadataArtifact = message?.artifacts?.find(
      (a: Artifact) => a.artifact_type === "metadata"
    );
    let metadata = null;
    if (metadataArtifact && metadataArtifact?.content) {
      metadata = JSON.parse(metadataArtifact?.content as string);
    }

    if (metadata?.is_ambiguous) {
      return false;
    }

    return true;
  }, [message.artifacts]);

  const [isMobileOrTablet, setIsMobileOrTablet] = useState(false);

  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobileOrTablet(window.innerWidth < 768);
    };

    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);
    return () => window.removeEventListener("resize", checkScreenSize);
  }, [pathname]);

  if (message.content && message.content === tokenLimitsReached) {
    return (
      <div className="flex flex-col items-center justify-center p-6 space-y-4 bg-muted/30 dark:bg-subtle-hover/30 rounded-xl border border-muted-foreground/10">
        <div className="flex items-center gap-3">
          <CircleAlert className="w-6 h-6 text-yellow-500" />
          <span className="text-base font-medium text-foreground">
            {t("creditLimitReached")}
          </span>
        </div>
        <p className="text-sm text-muted-foreground text-center max-w-md">
          {t("creditLimitReachedDescription")}
        </p>
        <Button
          variant="default"
          className="w-full max-w-[200px] gap-2"
          onClick={() => {
            router.push("/settings/plans");
          }}
        >
          <ArrowRight className="w-4 h-4" />
          {t2("upgrade")}
        </Button>
      </div>
    );
  }

  return (
    <div className={`flex flex-col md:flex-row w-full items-start gap-2`}>
      {/* if mobile */}
      {isMobileOrTablet && (
        <div
          className={cn(
            "flex items-center justify-start sticky w-full z-10",
            isAssistant ? "justify-start top-12" : "justify-end top-4 "
          )}
        >
          {!isAssistant && <UserAvatar />}
        </div>
      )}

      {/* {isAssistant && !isMobileOrTablet && (
        <div className="flex items-center justify-start sticky top-4">
          <MipalAvatar />
        </div>
      )} */}
      <div
        className={cn(
          "flex flex-col p-2 sm:p-3 overflow-hidden transition-colors rounded-2xl text-left",
          isAssistant
            ? "justify-start w-full"
            : "bg-muted/50 dark:bg-[hsl(var(--subtle-border))] justify-end ml-auto w-fit max-w-[85%] md:min-w-[300px]"
        )}
      >
        <div className="flex-1 min-w-0">
          <div className="text-foreground dark:text-subtle-fg">
            {isAssistant && message.isThinking ? (
              <ThinkingIndicator
                metaContent={message.metaContent}
                message={message}
                showMetaContent={
                  isAnalytics || chatModel === PalEnum.KNOWLEDGE_PAL
                }
              />
            ) : (
              <>
                {/* If the message is assistant and has meta_contents, show the thinking indicator */}
                {isAssistant &&
                  message?.metadata?.meta_contents?.length > 0 && (
                    <ThinkingIndicator
                      metaContent={message.metadata.meta_contents}
                      message={message}
                      showCompleted={true}
                      showMetaContent={
                        isAnalytics || chatModel === PalEnum.KNOWLEDGE_PAL
                      }
                    />
                  )}
                <div
                  className={cn(
                    "prose prose-sm sm:prose-base dark:prose-invert max-w-none break-words ",
                    isAssistant
                      ? "prose-p:leading-relaxed"
                      : "prose-p:leading-relaxed",
                    (message.artifacts && message.artifacts.length > 0) ||
                      (message.references &&
                        message.references.length > 0 &&
                        "cursor-pointer")
                  )}
                  onClick={() => {
                    if (message.artifacts && message.artifacts.length > 0) {
                      handleArtifactClick(message.artifacts || []);
                    } else if (
                      message.references &&
                      message.references.length > 0
                    ) {
                      dispatch(setReferences(message.references || []));
                      dispatch(setIsReferencePanelOpen(true));
                    }
                  }}
                >
                  {/* {formatMessageContent(message.content)} */}
                  <MessageContentRenderer content={message.content} />

                  {isAssistant && isStreaming && (
                    <span className="ml-1 animate-pulse">▋</span>
                  )}
                </div>
              </>
            )}

            <div className="flex flex-row flex-wrap justify-end w-full">
              {/* Show attachments for user messages */}
              {!isAssistant &&
                message.attachments &&
                message.attachments.length > 0 && (
                  <div className="flex flex-col items-end mt-3 space-y-2 w-full sm:max-w-[300px] bg-background rounded-xl">
                    {message.attachments.map((attachment, index) => (
                      <div
                        key={index}
                        onClick={() => onAttachmentClick?.(attachment)}
                        className="flex items-center gap-2 py-2 px-3 sm:px-4 transition-colors rounded-xl cursor-pointer group hover:bg-muted w-full text-left border border-muted-foreground/50 dark:border-muted-foreground/60"
                      >
                        <FileIcon className="w-4 h-4 transition-colors group-hover:text-primary flex-shrink-0" />
                        <div className="flex flex-col flex-1 min-w-0 text-left">
                          <span className="text-sm truncate transition-colors group-hover:text-primary">
                            {attachment.file_name}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            ({(attachment.file_size / 1024).toFixed(2)} KB)
                          </span>
                        </div>
                        <Eye className="w-4 h-4 transition-opacity opacity-0 group-hover:opacity-100 text-muted-foreground flex-shrink-0" />
                      </div>
                    ))}
                  </div>
                )}

              {/* Show remote attachments for user messages */}
              {!isAssistant && message.files && message.files.length > 0 && (
                <div className="flex flex-col items-end mt-3 space-y-2 w-full sm:w-[85%] lg:w-[75%] max-w-[500px] bg-background rounded-xl">
                  {message.files.map((attachment, index) => (
                    <div
                      key={index}
                      onClick={() => window.open(attachment?.address, "_blank")}
                      className="flex items-center gap-2 py-2 px-3 sm:px-4 transition-colors rounded-xl cursor-pointer group hover:bg-muted w-full border border-muted-foreground/50 dark:border-muted-foreground/60"
                    >
                      <FileIcon className="w-4 h-4 transition-colors group-hover:text-primary flex-shrink-0" />
                      <div className="flex flex-col flex-1 min-w-0 text-left">
                        <span className="text-sm truncate transition-colors group-hover:text-primary">
                          {attachment.title}
                        </span>
                        <span className="text-xs text-muted-foreground line-clamp-1">
                          ({attachment.address})
                        </span>
                      </div>
                      <Eye className="w-4 h-4 transition-opacity opacity-0 group-hover:opacity-100 text-muted-foreground flex-shrink-0" />
                    </div>
                  ))}
                </div>
              )}
            </div>
            {/* Show selected suggestions for user messages */}
            {!isAssistant &&
              message.selected_suggestions &&
              message.selected_suggestions.length > 0 && (
                <div className="mt-2 space-y-1">
                  <div className="text-xs font-medium text-muted-foreground dark:text-subtle-fg/70">
                    Referenced:
                  </div>
                  <div className="space-y-1">
                    {message.selected_suggestions.map((suggestion, index) => (
                      <div
                        key={index}
                        className="text-sm p-1.5 bg-muted/50 dark:bg-subtle-hover/50 rounded-md text-foreground dark:text-subtle-fg"
                      >
                        {renderSuggestionContent(suggestion as Suggestion)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </div>

          {/* Show suggestions for both user and assistant messages */}
          {suggestions && suggestions.length > 0 && (
            <SuggestionList
              suggestions={suggestions}
              selectedSuggestions={selectedSuggestions}
              onSuggestionSelect={onSuggestionSelect || (() => {})}
              isUserMessage={!isAssistant}
              isCurrentLeafMessage={isCurrentLeaf}
              isLastMessage={isLastMessage}
            />
          )}
        </div>
        {message.references && message.references.length > 0 && (
          <button
            onClick={() => {
              dispatch(setReferences(message.references || []));
              dispatch(setIsReferencePanelOpen(true));
            }}
            className="flex items-center w-full gap-4 p-2 mt-3 text-left transition-all duration-200 rounded-xl bg-muted/30 hover:bg-muted/50 border border-muted-foreground/10 hover:border-muted-foreground/20 group relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-muted/0 via-muted/5 to-muted/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 transform translate-x-[-100%] group-hover:translate-x-[100%]" />
            <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-muted/50 transition-all duration-200 group-hover:bg-muted/70 group-hover:scale-105 border border-muted-foreground/10">
              <BookOpen className="w-6 h-6 text-muted-foreground transition-transform duration-200" />
            </div>
            <div className="flex flex-col flex-1 relative">
              <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors duration-200">
                {t("viewReferences")}
              </span>
              <span className="text-xs text-muted-foreground group-hover:text-foreground/70 transition-colors duration-200">
                {t("clickToOpenDocument")}
              </span>
            </div>
            <div className="flex items-center self-center pr-1">
              <ArrowRight className="w-5 h-5 text-muted-foreground transition-transform duration-200 transform translate-x-0 group-hover:translate-x-1" />
            </div>
          </button>
        )}
        {message.artifacts &&
          message.artifacts.length > 0 &&
          handleArtifactViewButton() && (
            <button
              onClick={() => handleArtifactClick(message.artifacts || [])}
              className="flex items-center w-full gap-4 p-2 mt-3 text-left transition-all duration-200 rounded-xl bg-muted/30 hover:bg-muted/50 border border-muted-foreground/10 hover:border-muted-foreground/20 group relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-muted/0 via-muted/5 to-muted/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 transform translate-x-[-100%] group-hover:translate-x-[100%]" />
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-muted/50 transition-all duration-200 group-hover:bg-muted/70 border border-muted-foreground/10">
                <ChartBar className="w-6 h-6 text-muted-foreground transition-transform duration-200" />
              </div>
              <div className="flex flex-col flex-1 relative">
                <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors duration-200">
                  {t("analysisResults")}
                </span>
                <span className="text-xs text-muted-foreground group-hover:text-foreground/70 transition-colors duration-200">
                  {t("clickToOpenArtifact")}
                </span>
              </div>
              <div className="flex items-center self-center pr-1">
                <ArrowRight className="w-5 h-5 text-muted-foreground transition-transform duration-200 transform translate-x-0 group-hover:translate-x-1" />
              </div>
            </button>
          )}
      </div>
      {!isAssistant && !isMobileOrTablet && (
        <div className="flex items-center justify-start sticky top-4">
          <UserAvatar />
        </div>
      )}
    </div>
  );
};
