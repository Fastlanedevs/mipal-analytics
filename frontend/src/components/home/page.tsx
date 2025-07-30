"use client";
import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Paperclip,
  ArrowUp,
  MessagesSquare,
  Search,
  Globe,
  X,
  BookOpen,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  clearChatCreationDetails,
  setChatCreationDetails,
} from "@/store/slices/chatCreationSlice";
import { v4 as uuidv4 } from "uuid";
import { FileUploadHandler } from "@/app/(protected)/chat/components/FileUpload/FileUploadHandler";
import {
  Attachment,
  ChatConversation,
  FileUploadState,
} from "@/app/(protected)/chat/types/chat";
import { isComplexFile, readTextFile } from "@/lib/utils/fileProcessing";
import { toast } from "@/hooks/use-toast";
import { MobileLogo, DesktopLogo } from "@/assets/svg/MILogo";
import { useGetUserProfileQuery } from "@/store/services/userApi";
import { cn, formatDate } from "@/lib/utils";
import FilePreviewDialog from "@/app/(protected)/chat/components/FileUpload/FilePreviewDialog";
import { useGetRecentConversationsQuery } from "@/store/services/chatApi";
import { useGetPalsQuery } from "@/store/services/palApi";
import { Badge } from "@/components/ui/badge";
import { PalEnum, palIconMap } from "@/app/(protected)/_pals/PalConstants";
import {
  removeSelectedFile,
  resetSelectedFiles,
  SelectedFile,
} from "@/store/slices/fileSearchSlice";
import { SearchModal } from "@/components/search/SearchModal";
import { title } from "process";
import { ComingSoonDialog } from "@/components/ui/ComingSoonDialog";
import { removeArtifacts } from "@/store/slices/artifactsSlice";
import {
  clearModel,
  resetToInitialChatState,
  setModel,
  setWebSearchEnabled,
} from "@/store/slices/chatSlice";
import { useGetDatabasesQuery } from "@/store/services/analyticsApi";
import { resetAnalytics, setDatabases } from "@/store/slices/analyticsSlice";
import { clearSuggestions } from "@/store/slices/intentsSlice";
import { useTour } from "@/contexts/TourContext";
import { useGetTourGuideQuery } from "@/store/services/userApi";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useTranslations } from "next-intl";

const pulsingBorderClass = "animate-border-pulse";

// Add new interface for suggestion chips
interface SuggestionChip {
  id: string;
  name: string;
  pal_enum: string;
  description: string;
  type: "FREE_PLAN" | "ENTERPRISE_PLAN";
  is_active: boolean;
  suggestions: string[];
}

export function LandingPage() {
  const t = useTranslations("home");
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [inputMessage, setInputMessage] = useState("");
  const [isMobile, setIsMobile] = useState(false);
  const { startTour } = useTour();
  const { data: tourGuideState } = useGetTourGuideQuery();
  const [tourStarted, setTourStarted] = useState(false);
  const [pageReady, setPageReady] = useState(false);
  const {
    data: userProfile,
    isLoading,
    error,
    refetch,
  } = useGetUserProfileQuery({});
  const [fileStates, setFileStates] = useState<FileUploadState[]>([]);
  const [processingFiles, setProcessingFiles] = useState<Set<string>>(
    new Set()
  );
  const [processedAttachments, setProcessedAttachments] = useState<
    Attachment[]
  >([]);
  const [isFilePreviewOpen, setIsFilePreviewOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFileState, setSelectedFileState] =
    useState<FileUploadState | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>("");
  const [isProcessingFiles, setIsProcessingFiles] = useState(false);
  const {
    data: recentConversations,
    isLoading: isRecentConversationsLoading,
    error: recentConversationsError,
  } = useGetRecentConversationsQuery();
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedChip, setSelectedChip] = useState<SuggestionChip | null>(null);
  const { data: pals } = useGetPalsQuery();

  const knowledgePal = pals?.find(
    (pal) => pal.pal_enum === PalEnum.KNOWLEDGE_PAL
  );

  const [isInProgress, setIsInProgress] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [remoteFileAttachments, setRemoteFileAttachments] = useState<
    FileUploadState[]
  >([]);
  const webSearchEnabled = useAppSelector(
    (state) => state.chat.webSearchEnabled
  );

  const [isComingSoonOpen, setIsComingSoonOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // The API is being hit because it takes time to fetch the databases
  // TO DO: Remove this once the fetch time will decrease
  const { data: databases } = useGetDatabasesQuery();

  useEffect(() => {
    dispatch(setDatabases(databases || []));
  }, [databases?.length]);

  const suggestionBackgroundClass =
    "border border-t-0 dark:border-subtle-border shadow-file-upload-shadow dark:shadow-file-upload-shadow-dark";

  const selectedFiles = useAppSelector(
    (state) => state.fileSearch.selectedFiles
  );

  useEffect(() => {
    dispatch(clearModel());
    dispatch(setWebSearchEnabled(false));
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkIfMobile();
    window.addEventListener("resize", checkIfMobile);

    // Mark the page as ready when it's rendered
    setPageReady(true);

    return () => window.removeEventListener("resize", checkIfMobile);
  }, []);

  // Separate useEffect for starting the tour
  useEffect(() => {
    if (pageReady && !tourStarted && tourGuideState) {
      // Add a small delay to ensure DOM is fully rendered
      const timer = setTimeout(() => {
        startTour("home");
        setTourStarted(true);
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [pageReady, tourStarted, startTour, tourGuideState]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  useEffect(() => {
    if (selectedFiles.length > 0) {
      // Create virtual file states for all selected files
      const virtualFileStates = selectedFiles.map((file: SelectedFile) => ({
        id: file.id,
        file: new File([], file.title), // Create empty file just for display
        status: "complete" as const,
        progress: 100,
        preview: file.address,
      }));
      setRemoteFileAttachments(virtualFileStates);
    } else {
      setRemoteFileAttachments([]);
    }
  }, [selectedFiles]);

  const handleKeyPress = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleStartChat();
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    const greeting =
      hour < 12
        ? t("greetings.morning")
        : hour < 18
          ? t("greetings.afternoon")
          : t("greetings.evening");
    return (
      <>
        <span className="text-gray-800/70 dark:text-white/70 animate-fade animate-once animate-delay-500">
          {greeting}
        </span>
        <span className="text-gray-800/70 dark:text-white/70 animate-fade animate-once animate-delay-500">
          ,{" "}
        </span>
        <span className="text-gray-800 dark:text-white animate-fade animate-once animate-delay-700">
          {userProfile?.name || "there"}
        </span>
      </>
    );
  };

  const handleRecentConversationsClick = (conversation: ChatConversation) => {
    dispatch(resetToInitialChatState());
    dispatch(removeArtifacts());
    if (conversation.model === PalEnum.ANALYST_PAL) {
      router.push(`/chat/analytics/${conversation.id}`);
    } else {
      router.push(`/chat/${conversation.id}`);
    }
  };

  const handleFileUpload = async (newFiles: File[]) => {
    try {
      setIsProcessingFiles(true);

      const newId = uuidv4();

      const newFileStates: FileUploadState[] = newFiles.map((file) => ({
        id: newId,
        file,
        status: "pending",
        progress: 0,
        preview: file.type.startsWith("image/")
          ? URL.createObjectURL(file)
          : undefined,
      }));

      setFileStates((prev) => [...prev, ...newFileStates]);

      for (const fileState of newFileStates) {
        setProcessingFiles((prev) => new Set(prev).add(fileState.file.name));

        try {
          if (isComplexFile(fileState.file)) {
            const formData = new FormData();
            formData.append("file", fileState.file);

            // Add progress tracking
            setFileStates((states) =>
              states.map((state) =>
                state.id === fileState.id
                  ? { ...state, status: "uploading", progress: 0 }
                  : state
              )
            );

            // Simulate upload progress
            const progressInterval = setInterval(() => {
              setFileStates((states) =>
                states.map((state) =>
                  state.id === fileState.id && state.status === "uploading"
                    ? {
                        ...state,
                        progress: Math.min((state.progress || 0) + 10, 90),
                      }
                    : state
                )
              );
            }, 200);

            const response = await fetch("/api/proxy/chat/extract", {
              method: "POST",
              body: formData,
            });

            clearInterval(progressInterval);

            if (!response.ok) {
              throw new Error(`Failed to process file: ${fileState.file.name}`);
            }

            const processedFile = await response.json();

            setProcessedAttachments((prev) => [
              ...prev,
              {
                id: newId,
                file_name: fileState.file.name,
                file_size: fileState.file.size,
                file_type: fileState.file.type,
                extracted_content: processedFile.extracted_content,
              },
            ]);

            setFileStates((states) =>
              states.map((state) =>
                state.id === fileState.id
                  ? { ...state, status: "complete", progress: 100 }
                  : state
              )
            );
          } else {
            // Handle simple text files
            const content = await readTextFile(fileState.file);
            setProcessedAttachments((prev) => [
              ...prev,
              {
                id: newId,
                file_name: fileState.file.name,
                file_size: fileState.file.size,
                file_type: fileState.file.type,
                extracted_content: content,
              },
            ]);

            setFileStates((states) =>
              states.map((state) =>
                state.id === fileState.id
                  ? { ...state, status: "complete", progress: 100 }
                  : state
              )
            );
          }

          setProcessingFiles((prev) => {
            const updated = new Set(prev);
            updated.delete(fileState.file.name);
            return updated;
          });
        } catch (error) {
          console.error(`Error processing file ${fileState.file.name}:`, error);
          toast({
            variant: "destructive",
            title: "Error",
            description: `Failed to process file: ${fileState.file.name}`,
          });

          setFileStates((states) =>
            states.map((state) =>
              state.id === fileState.id
                ? {
                    ...state,
                    status: "error",
                    error:
                      error instanceof Error
                        ? error.message
                        : "Failed to process file",
                  }
                : state
            )
          );

          setProcessingFiles((prev) => {
            const updated = new Set(prev);
            updated.delete(fileState.file.name);
            return updated;
          });
        }
      }
    } catch (error) {
      console.error("Error uploading files:", error);
    } finally {
      setIsProcessingFiles(false);
    }
  };

  const handleRemoveFile = (id: string) => {
    setProcessedAttachments((prev) => prev.filter((f) => f.id !== id));
    setFileStates((prev) => {
      const fileToRemove = prev.find((f) => f.id === id);
      if (fileToRemove?.preview) {
        URL.revokeObjectURL(fileToRemove.preview);
      }
      return prev.filter((f) => f.id !== id);
    });
    setRemoteFileAttachments((prev) => prev.filter((f) => f.id !== id));
    dispatch(removeSelectedFile(id));
  };

  const handleFileClick = (fileState: FileUploadState) => {
    setSelectedFileState(fileState);
    const fileAttachment = processedAttachments.find(
      (att) => att.file_name === fileState.file.name
    );
    setSelectedFileContent(fileAttachment?.extracted_content || "");
    setIsFilePreviewOpen(true);
  };

  const handleStartChat = () => {
    if (inputMessage.trim()) {
      const newChatId = uuidv4();

      setIsInProgress(true);

      dispatch(removeArtifacts());
      // Check if the selected PAL is RFP_PAL and redirect accordingly
      if (selectedChip?.pal_enum === PalEnum.ANALYST_PAL) {
        dispatch(resetToInitialChatState());
        router.push(`/chat/analytics/${newChatId}`);
      } else {
        dispatch(
          setChatCreationDetails({
            initialMessage: inputMessage.trim(),
            chatTitle: "",
            attachments: processedAttachments,
            model: selectedChip?.pal_enum || undefined,
            web_search: webSearchEnabled,
            files: selectedFiles.map((file: SelectedFile) => ({
              id: file.id,
              title: file.title,
              content: "",
              address: file.address,
            })),
          })
        );
        router.push(`/chat/${newChatId}`);
        dispatch(resetSelectedFiles());
      }
    }
  };

  const handleViewAllConversations = () => {
    router.push("/history");
  };

  useEffect(() => {
    if (!selectedChip) {
      setShowSuggestions(false);
      dispatch(clearChatCreationDetails());
      return;
    }
  }, [selectedChip, dispatch]);

  useEffect(() => {
    setShowSuggestions(false);
  }, [inputMessage]);

  useEffect(() => {
    if (selectedChip) {
      setShowSuggestions(selectedChip.suggestions.length > 0);
    }
  }, [selectedChip]);

  const handleChipClick = (
    chip: SuggestionChip,
    event: React.MouseEvent<HTMLButtonElement, MouseEvent>,
    suggestionsLength: number
  ) => {
    event.preventDefault();

    if (chip.type === "ENTERPRISE_PLAN") {
      setIsComingSoonOpen(true);
      return;
    }

    // If ANALYST_PAL is selected, redirect to Analytics chat without initial message
    if (chip.pal_enum === PalEnum.ANALYST_PAL) {
      const newChatId = uuidv4();
      // dispatch(
      //   setChatCreationDetails({
      //     initialMessage: "",
      //     chatTitle: "",
      //     model: chip.pal_enum,
      //   })
      // );
      dispatch(resetToInitialChatState());
      dispatch(removeArtifacts());
      dispatch(clearSuggestions());
      dispatch(resetAnalytics());
      router.push(`/chat/analytics/${newChatId}`);
    } else if (selectedChip?.id === chip.id) {
      setSelectedChip(null);
      setShowSuggestions(false);
      if (chip.pal_enum === PalEnum.KNOWLEDGE_PAL) {
        dispatch(clearModel());
      }
    } else {
      if (chip.pal_enum === PalEnum.KNOWLEDGE_PAL) {
        dispatch(setModel(PalEnum.KNOWLEDGE_PAL));
      } else {
        dispatch(clearModel());
      }
      setSelectedChip(chip);
    }
  };

  const suggestionChips: SuggestionChip[] =
    pals?.map((pal) => ({
      id: pal.id,
      name: pal.name,
      pal_enum: pal.pal_enum,
      description: pal.description,
      type: pal.type,
      is_active: pal.is_active,
      // Capitalize the first letter of each suggestion
      suggestions: pal.suggestions.map(
        (suggestion) => suggestion.charAt(0).toUpperCase() + suggestion.slice(1)
      ),
    })) ?? [];

  console.log("🚀 ~ suggestionChips:", suggestionChips);

  const adjustTextAreaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Store the current scroll position
      const scrollPos = window.scrollY;

      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = "auto";

      // Set the height to match the content with a smooth transition
      textarea.style.height = `${textarea.scrollHeight}px`;

      // Restore the scroll position
      window.scrollTo(0, scrollPos);
    }
  };

  // Add orientation change handler
  useEffect(() => {
    const handleResize = () => {
      // Add a small delay to ensure the new dimensions are available
      setTimeout(adjustTextAreaHeight, 100);
    };

    // Listen for both resize and orientationchange events
    window.addEventListener("resize", handleResize);
    window.addEventListener("orientationchange", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("orientationchange", handleResize);
    };
  }, []);

  // Keep existing useEffect for chip selection
  useEffect(() => {
    adjustTextAreaHeight();
  }, [selectedChip, inputMessage]); // Also trigger on inputMessage changes

  const handleTextAreaInput = (
    textOrEvent: string | React.ChangeEvent<HTMLTextAreaElement>
  ) => {
    // If it's an event, get the value from event.target
    const newValue =
      typeof textOrEvent === "string" ? textOrEvent : textOrEvent.target.value;

    setInputMessage(newValue);
    // Adjust height after the state update
    requestAnimationFrame(adjustTextAreaHeight);
  };

  return (
    <div className="flex flex-col pb-6 space-y-6 transition-all duration-300 ">
      <div className="home-tour-start" style={{ height: "1px" }}></div>
      <div className="flex flex-col items-center justify-center space-y-2 text-center">
        <div className="flex justify-center w-full">
          <DesktopLogo />
        </div>
        <h1 className="text-3xl font-bold sm:text-4xl">{getGreeting()}</h1>
      </div>

      {/* <Card className={cn("relative p-0 overflow-visible", pulsingBorderClass)}> */}
      {/* <div className="w-full h-full bg-white dark:bg-zinc-900/50 rounded-xl overflow-visible"> */}
      {/* <CardHeader>
            <CardTitle className="text-lg sm:text-xl">
              What are you looking for today?
            </CardTitle>
          </CardHeader> */}
      {/* <CardContent> */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleStartChat();
        }}
        // className="space-y-4"
      >
        <div className="relative ">
          <FileUploadHandler
            onFileUpload={handleFileUpload}
            files={fileStates}
            onRemoveFile={handleRemoveFile}
            processingFiles={processingFiles}
            onFileClick={handleFileClick}
            remoteFiles={remoteFileAttachments}
            selectedFiles={selectedFiles}
            showScrollButton={false}
            scrollToBottom={() => {}}
          />
          <div
            className={cn(
              "relative p-1 overflow-visible rounded-xl border text-card-foreground chat-input",
              "shadow-file-upload-shadow dark:shadow-file-upload-shadow-dark",
              pulsingBorderClass,
              isDragging &&
                "border border-dashed border-primary/30 dark:border-primary/30 bg-primary/5 dark:bg-primary/5"
            )}
            onDragEnter={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsDragging(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsDragging(false);
            }}
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsDragging(true);
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsDragging(false);
              const files = Array.from(e.dataTransfer.files);
              if (files.length > 0) {
                handleFileUpload(files);
              }
            }}
          >
            {isDragging && (
              <div className="absolute inset-0 z-10 flex items-center justify-center overflow-hidden rounded-xl bg-background/95 backdrop-blur-sm">
                <div className="flex flex-col items-center gap-2 text-primary/70 dark:text-primary/70">
                  <Paperclip className="w-8 h-8 animate-bounce" />
                  <span className="text-sm font-medium">
                    {t("dropFilesToUpload")}
                  </span>
                </div>
              </div>
            )}

            <div className="relative">
              {selectedChip && (
                <div className="absolute top-4 left-4 sm:top-5 z-50">
                  <Badge
                    variant="secondary"
                    className="px-2 py-1.5 text-xs font-medium bg-muted-foreground/10 dark:bg-primary/40 text-primary dark:text-primary-foreground rounded-full whitespace-nowrap flex gap-1 justify-center items-center z-50 backdrop-blur-md"
                  >
                    {selectedChip.name}
                    <X
                      className="w-4 h-4 text-muted-foreground/80 dark:text-primary/40 bg-foreground/10 dark:bg-background/40 rounded-full p-[2px] cursor-pointer"
                      onClick={() => {
                        setSelectedChip(null);
                        dispatch(clearModel());
                      }}
                    />
                  </Badge>
                </div>
              )}
              <textarea
                ref={textareaRef}
                placeholder={
                  isProcessingFiles
                    ? t("placeholders.processing")
                    : t("placeholders.input")
                }
                value={inputMessage}
                onChange={handleTextAreaInput}
                onKeyPress={handleKeyPress}
                className={cn(
                  "flex-1 w-full text-base bg-transparent placeholder:text-muted-foreground dark:placeholder:text-subtle-fg/50 resize-none relative rounded-xl border-transparent dark:border-transparent dark:bg-transparent dark:border-none dark:focus:border-none dark:focus:ring-0 dark:focus:outline-none dark:focus-visible:border-none focus-visible:border-none focus-visible:ring-0 focus-visible:outline-none focus-visible:focus-visible:border-none",
                  "transition-[height] duration-200 ease-out",
                  "overflow-y-auto",
                  selectedChip ? "pt-14 px-4 sm:pt-16" : "px-4 pt-4"
                )}
                disabled={isProcessingFiles}
                rows={1}
                style={{
                  height: "auto",
                  minHeight: selectedChip ? "96px" : "64px",
                  maxHeight: "300px",
                }}
              />
            </div>

            <div className="flex items-center justify-between px-4 py-2">
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "file-upload-input",
                    "h-9 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl",
                    isDragging && "hidden "
                  )}
                  onClick={() => {
                    const fileInput = document.querySelector(
                      'input[type="file"]'
                    ) as HTMLInputElement;
                    if (fileInput) {
                      fileInput.click();
                    }
                  }}
                >
                  <Paperclip className="w-5 h-5" />
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="search-input h-9 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl"
                  onClick={() => setIsSearchOpen(true)}
                >
                  <Search className="w-5 h-5" />
                </Button>
                <div className="relative group web-search-input">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className={cn(
                      "h-9 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl"
                    )}
                    style={{
                      color: webSearchEnabled ? "#2563eb" : "",
                    }}
                    onClick={() =>
                      dispatch(setWebSearchEnabled(!webSearchEnabled))
                    }
                  >
                    <Globe className="w-5 h-5" />
                  </Button>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block">
                    <div className="bg-popover text-popover-foreground px-3 py-1.5 rounded-md text-sm whitespace-nowrap shadow-md">
                      {t("buttons.webSearch")}
                    </div>
                  </div>
                </div>

                {knowledgePal && (
                  <div className="relative group web-search-input">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className={cn(
                        "h-9 w-9 text-muted-foreground hover:text-foreground dark:text-subtle-fg/70 dark:hover:text-subtle-fg rounded-xl"
                      )}
                      style={{
                        color:
                          selectedChip?.pal_enum === knowledgePal.pal_enum
                            ? "#2563eb"
                            : "",
                      }}
                      onClick={(event) => {
                        if (knowledgePal.type !== "FREE_PLAN") {
                          event.preventDefault();
                          return;
                        }
                        handleChipClick(
                          knowledgePal,
                          event,
                          knowledgePal.suggestions.length
                        );
                      }}
                    >
                      <BookOpen className="w-5 h-5" />
                    </Button>
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block">
                      <div className="bg-popover text-popover-foreground px-3 py-1.5 rounded-md text-sm whitespace-nowrap shadow-md">
                        {knowledgePal?.name || ""}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <Button
                type="submit"
                size="icon"
                disabled={
                  !inputMessage.trim() || isProcessingFiles || isInProgress
                }
                className={cn(
                  "h-9 w-9 rounded-xl",
                  "bg-primary hover:bg-primary/90 dark:bg-primary/90 dark:hover:bg-primary rotate-90",
                  "disabled:bg-muted-foreground/60 dark:disabled:bg-subtle-fg/20",
                  "transition-colors duration-200"
                )}
              >
                {isInProgress ? (
                  <div className="w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                ) : (
                  <ArrowUp className="w-5 h-5 text-primary-foreground" />
                )}
              </Button>
            </div>
          </div>

          <div
            className={cn(
              "w-full flex flex-col items-center transition-all duration-300",
              "origin-top",
              showSuggestions || suggestionChips?.length > 0
                ? "flex animate-expand"
                : "hidden animate-collapse"
            )}
          >
            {/* Add suggestion chips */}
            <div
              className={cn(
                "w-full rounded-b-xl max-w-[calc(100%-2rem)] overflow-hidden",
                suggestionBackgroundClass,
                showSuggestions ? "hidden" : ""
              )}
            >
              <div
                className={cn(
                  "flex flex-row flex-wrap gap-2 p-3 pt-5",
                  "md:flex-wrap", // Reset to wrap on medium screens and up
                  "max-md:flex-nowrap max-md:overflow-x-auto",
                  // Custom scrollbar styles
                  "max-md:[&::-webkit-scrollbar]:h-1.5",
                  "max-md:[&::-webkit-scrollbar-track]:bg-transparent",
                  "max-md:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/20",
                  "max-md:[&::-webkit-scrollbar-thumb]:hover:bg-muted-foreground/30",
                  "max-md:[&::-webkit-scrollbar-thumb]:rounded-full",
                  "max-md:scroll-px-2",
                  // Add padding for scrollbar
                  "max-md:pb-3",
                  "features-pals"
                )}
              >
                {/* show which are free plan */}
                <TooltipProvider>
                  {suggestionChips
                    // .filter((chip) => chip.type === "FREE_PLAN")
                    .map((chip, index) => {
                      const IconComponent =
                        palIconMap[chip.pal_enum]?.icon ||
                        palIconMap.DEFAULT_PAL.icon;
                      const iconColor =
                        palIconMap[chip.pal_enum]?.color ||
                        palIconMap.DEFAULT_PAL.color;

                      return (
                        <Tooltip key={index}>
                          <TooltipTrigger asChild>
                            <Button
                              key={index}
                              variant="outline"
                              size="sm"
                              className={cn(
                                "rounded-full max-md:whitespace-nowrap max-md:snap-start",
                                selectedChip?.name === chip.name
                                  ? "border-primary/60"
                                  : "",
                                chip.type !== "FREE_PLAN" &&
                                  "opacity-50 cursor-text"
                              )}
                              title={
                                chip.type !== "FREE_PLAN"
                                  ? "Requires Enterprise Plan"
                                  : undefined
                              }
                              // disabled={chip.type !== "FREE_PLAN"}
                              onClick={(event) => {
                                if (chip.type !== "FREE_PLAN") {
                                  event.preventDefault();
                                  return;
                                }
                                handleChipClick(
                                  chip,
                                  event,
                                  chip.suggestions.length
                                );
                              }}
                            >
                              <IconComponent
                                className={`mr-2 h-4 w-4 ${iconColor}`}
                              />
                              {chip.name}
                            </Button>
                          </TooltipTrigger>
                          {chip.type !== "FREE_PLAN" && (
                            <TooltipContent>
                              <p>Coming soon</p>
                            </TooltipContent>
                          )}
                        </Tooltip>
                      );
                    })}
                </TooltipProvider>
              </div>
            </div>

            {/* Add suggestions dropdown */}
            {showSuggestions &&
              selectedChip &&
              selectedChip.suggestions.length > 0 && (
                <div
                  className={cn(
                    "mx-4 sm:mx-0 animate-slide-down-fade text-left p-1 pt-3",
                    suggestionBackgroundClass,
                    "rounded-b-xl max-w-[calc(100%-2rem)] w-full"
                  )}
                >
                  <div className="">
                    <div className="flex items-center justify-between pr-1">
                      <p className="text-sm text-muted-foreground px-4 py-2">
                        {
                          pals?.find((pal) => pal.name === selectedChip.name)
                            ?.description
                        }
                      </p>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowSuggestions(false)}
                      >
                        <X className="w-4 h-4 text-muted-foreground/80" />
                      </Button>
                    </div>
                    <div className="space-y-2 overflow-y-auto pb-2">
                      {/* Existing suggestions */}
                      {selectedChip.suggestions.map((suggestion, index) => (
                        <div
                          key={index}
                          className="animate-slide-left-fade"
                          style={{
                            animationDelay: `${(index + 1) * 50}ms`,
                            animationFillMode: "forwards",
                            opacity: 0,
                          }}
                        >
                          <Button
                            variant="ghost"
                            className="w-full justify-start text-left hover:bg-primary/10 dark:hover:bg-primary/20 text-sm sm:text-base py-3 px-4"
                            onClick={() => {
                              handleTextAreaInput(suggestion);
                              // setInputMessage(suggestion);
                              setShowSuggestions(false);
                            }}
                          >
                            <span className="text-wrap">{suggestion}</span>
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
          </div>
        </div>
      </form>
      {/* </CardContent> */}
      {/* </div> */}
      {/* </Card> */}

      {!isRecentConversationsLoading &&
        recentConversations?.conversations &&
        recentConversations?.conversations?.length > 0 && (
          <div className="space-y-4 animate-fade-in-up">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold sm:text-2xl flex items-center justify-start gap-2 relative">
                <MessagesSquare className="opacity-50 w-5 h-5 md:absolute -left-7 top-3" />
                {t("titles.recentConversations")}
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleViewAllConversations()}
              >
                {t("buttons.viewAll")}
              </Button>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {recentConversations?.conversations
                ?.slice(0, 6)
                .map((conversation: ChatConversation, index: number) => (
                  <Card
                    key={conversation.id}
                    className={cn(
                      "group hover:bg-accent/50 dark:hover:bg-accent/25 transition-colors border dark:border-gray-800 cursor-pointer",
                      "animate-fade-in-up"
                    )}
                    style={{
                      animationDelay: `${index * 100}ms`,
                      animationFillMode: "backwards",
                    }}
                    onClick={() => handleRecentConversationsClick(conversation)}
                  >
                    <CardHeader className="p-4 sm:p-6 h-full justify-between">
                      <div className="space-y-2 sm:gap-4">
                        <CardTitle className="text-sm font-medium line-clamp-1 dark:text-gray-200 flex items-start justify-start gap-2">
                          {/* Maximum two lines */}
                          <p className="text-sm font-medium line-clamp-2 dark:text-gray-200 text-left">
                            {/* remove " from the name which occurs at the start and end of the text */}
                            {conversation?.name?.replace(/^"|"$/g, "") ||
                              t("titles.noTitle")}
                          </p>
                        </CardTitle>
                      </div>
                      <CardFooter className="p-0 justify-between">
                        {/* <div className="flex flex-wrap gap-2 items-center"> */}
                        {conversation?.model ? (
                          <Badge
                            variant="outline"
                            className="text-xs px-2 py-0.5 font-normal dark:border-gray-700 dark:bg-gray-800/50"
                          >
                            {conversation?.model?.replace(/_/g, " ")}
                          </Badge>
                        ) : (
                          <span />
                        )}
                        <Badge
                          variant="secondary"
                          className="text-xs px-2 py-0.5 font-normal dark:bg-gray-800 dark:text-gray-300"
                        >
                          {formatDate(conversation?.updated_at)}
                        </Badge>
                        {/* </div> */}
                      </CardFooter>

                      {/* <div className="absolute inset-0 border-2 border-primary/10 dark:border-primary/20 opacity-0 group-hover:opacity-100 rounded-lg transition-opacity" /> */}
                    </CardHeader>
                  </Card>
                ))}
            </div>
          </div>
        )}

      <FilePreviewDialog
        file={selectedFileState}
        isOpen={isFilePreviewOpen}
        onOpenChange={setIsFilePreviewOpen}
        extractedContent={selectedFileContent}
      />

      <SearchModal
        isSearchOpen={isSearchOpen}
        setIsSearchOpen={setIsSearchOpen}
      />

      <ComingSoonDialog
        isOpen={isComingSoonOpen}
        onClose={() => setIsComingSoonOpen(false)}
      />
    </div>
  );
}
