"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Attachment,
  Message,
  Suggestion,
  PALContent,
  FileUploadState,
  IntentContent,
} from "../../types/chat";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  setActiveConversation,
  addMessage,
  setLoading,
  addConversation,
  setMessages,
  updateMessage,
  clearMessages,
  setWebSearchEnabled,
} from "@/store/slices/chatSlice";
import { clearChatCreationDetails } from "@/store/slices/chatCreationSlice";
import { DEFAULT_PARENT_MESSAGE_ID } from "@/lib/utils/chat";
import {
  useCreateConversationMutation,
  useGetConversationQuery,
} from "@/store/services/chatApi";
import { isComplexFile, readTextFile } from "@/lib/utils/fileProcessing";
import { RootState } from "@/store/store";
import { toast } from "@/hooks/use-toast";
import { store } from "@/store/store";
import { createSelector } from "@reduxjs/toolkit";
import { MessageStreamHandler } from "../../services/messageHandler";
import { waitForStateUpdate } from "@/lib/utils/chatValidation";
import { cn } from "@/lib/utils";
import FilePreviewDialog from "../../components/FileUpload/FilePreviewDialog";
import { SearchModal } from "@/components/search/SearchModal";
import { SelectedFile } from "@/store/slices/fileSearchSlice";
import { AnalyticsMessageList } from "./AnalyticsMessageList";
import { setSelectedSuggestion } from "@/store/slices/intentsSlice";
import { ChatInput } from "../../components/ChatInput";
import { PalEnum } from "@/app/(protected)/_pals/PalConstants";
import { Button } from "@/components/ui/button";
import { ChevronDown } from "lucide-react";
import { removeArtifacts } from "@/store/slices/artifactsSlice";
import { resetAnalytics } from "@/store/slices/analyticsSlice";
import { v4 as uuidv4 } from "uuid";
import { useTranslations } from "next-intl";
interface ChatInterfaceProps {
  chatId: string;
  // csvAttachments: Attachment[];
  fileInputRef: React.RefObject<HTMLInputElement>;
  // handleCSVUploadSuccess: (
  //   fileName: string,
  //   extractedContent: string,
  //   fileSize: number
  // ) => void;
  setPageReady: (value: boolean) => void;
}

// Create memoized selector
const selectMessages = createSelector(
  [
    (state: RootState) => state.chat.activeConversationId,
    (state: RootState) => state.chat.messages,
  ],
  (activeConvId, messages) => {
    if (!activeConvId || !messages[activeConvId]) {
      return [];
    }

    return [...messages[activeConvId]];
  }
);

// Update the type guard to be more specific
const isPALContent = (content: any): content is PALContent => {
  return (
    content &&
    typeof content === "object" &&
    "title" in content &&
    typeof content.title === "string"
  );
};

// Add this type definition at the top of the file
interface FileDropHandler {
  (files: File[]): void;
}

// Add this type guard before the handleSuggestionSelect function
const isIntentContent = (content: any): content is IntentContent => {
  return (
    content &&
    typeof content === "object" &&
    "title" in content &&
    "text" in content &&
    typeof content.text === "string"
  );
};

const AnalyticsChatInterface: React.FC<ChatInterfaceProps> = ({
  chatId,
  // csvAttachments,
  fileInputRef,
  // handleCSVUploadSuccess,setPageReady
  setPageReady,
}) => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileId = searchParams?.get("fileId");
  const webSearch = fileId ? true : false;
  const dispatch = useAppDispatch();

  const [isMobile, setIsMobile] = useState(false);
  const t = useTranslations("chatPage.analytics");

  // Update cleanup effect
  useEffect(() => {
    // Clear messages when chatId changes
    dispatch(clearMessages());

    // Reset streaming and setup states
    setIsStreaming(false);
    setIsSetupComplete(false);
    setInitialMessageSent(false);

    // Clear selected suggestions
    setSelectedSuggestions([]);

    // Clear any ongoing streams
    if (streamAbortController.current) {
      streamAbortController.current.abort();
      streamAbortController.current = null;
    }
  }, []);

  // Get chat creation details from store
  const chatCreationDetails = useAppSelector((state: RootState) => ({
    initialMessage: state.chatCreation.initialMessage,
    chatTitle: state.chatCreation.chatTitle,
    pendingCreation: state.chatCreation.pendingCreation,
    attachments: state.chatCreation.attachments,
    model: state.chatCreation.model,
    web_search: state.chatCreation.web_search,
    files: state.chatCreation.files,
  }));

  const webSearchEnabled = useAppSelector(
    (state) => state.chat.webSearchEnabled
  );

  // Modify the query to skip for both new chat creation and no chatId

  const activeConversation = useAppSelector(
    (state: RootState) => state.chat.activeConversationId
  );

  const {
    data: conversationData,
    isLoading: isLoadingConversation,
    error: fetchError,
  } = useGetConversationQuery(chatId ?? "", {
    // Skip GET request if we're creating a new chat or don't have a chatId
    skip: !chatId,
    refetchOnMountOrArgChange: true,
  });

  const messages = useAppSelector(selectMessages);

  useEffect(() => {
    dispatch(removeArtifacts());
    dispatch(setSelectedSuggestion(null));
    dispatch(resetAnalytics());
  }, [chatId]);

  // Update this effect to properly handle conversation data
  useEffect(() => {
    if (messages.length === 0 && conversationData) {
      // Process messages to ensure consistent structure
      const processedMessages =
        conversationData.messages?.map((msg: Message) => ({
          ...msg,
          suggestions: msg.suggestions || [],
          attachments: msg.attachments || [],
          selected_suggestions: msg.selected_suggestions || [],
        })) || [];

      // Set active conversation
      dispatch(setActiveConversation(chatId));

      // Update conversation with processed messages
      // dispatch(
      //   addConversation({
      //     ...conversationData,
      //     messages: processedMessages,
      //   })
      // );
      if (processedMessages?.length > 0) {
        // Update messages separately to ensure proper state update
        dispatch(
          setMessages({
            conversationId: chatId,
            messages: processedMessages,
          })
        );
      }
    }
  }, [conversationData, chatId]);

  // Move createConversation mutation before isLoading selector
  const [createConversation, { isLoading: isCreating, error: createError }] =
    useCreateConversationMutation();

  // Update the loading state logic
  const isLoading = useAppSelector((state: RootState) => {
    // Only show loading during completion API call, not during conversation fetch
    return activeConversation && state.chat.isLoading[activeConversation];
  });

  const [initialMessageSent, setInitialMessageSent] = useState(false);
  // const [fileStates, setFileStates] = useState<FileUploadState[]>([]);
  // const messagesEndRef = useRef<HTMLDivElement>(null);
  const [currentMessage, setCurrentMessage] = useState<string | null>(null);
  // const [processingFiles, setProcessingFiles] = useState<Set<string>>(
  //   new Set()
  // );
  const [isSetupComplete, setIsSetupComplete] = useState(false);
  // Open the search modal
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const debugState = useAppSelector((state: RootState) => ({
    activeConversation: state.chat.activeConversationId,
    messages: state.chat.messages,
    isLoading: state.chat.isLoading,
    conversations: state.chat.conversations,
  }));

  const { selectedDatabase, selectedTable } = useAppSelector(
    (state: RootState) => state.analytics
  );

  // Add a ref to track streaming state
  // const isStreamingRef = useRef(false);
  const streamAbortController = useRef<AbortController | null>(null);

  // Add state for processed attachments
  const [processedAttachments, setProcessedAttachments] = useState<
    Attachment[]
  >([]);

  // Move these state variables to component level (outside handleSendMessage)
  const [isInCodeBlock, setIsInCodeBlock] = useState(false);
  const [codeBlockLanguage, setCodeBlockLanguage] = useState<string>("");

  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Add new state for selected suggestions
  const [selectedSuggestions, setSelectedSuggestions] = useState<Suggestion[]>(
    []
  );

  // Add new state for remote file attachments
  // const [remoteFileAttachments, setRemoteFileAttachments] = useState<
  //   FileUploadState[]
  // >([]);

  // // Remote files from the file search modal
  // const selectedFiles = useAppSelector(
  //   (state) => state.fileSearch.selectedFiles
  // );

  // useEffect(() => {
  //   if (selectedFiles.length > 0) {
  //     // Create virtual file states for all selected files
  //     const virtualFileStates = selectedFiles.map((file: SelectedFile) => ({
  //       id: file.id,
  //       file: new File([], file.title), // Create empty file just for display
  //       status: "complete" as const,
  //       progress: 100,
  //       preview: file.address,
  //     }));
  //     setRemoteFileAttachments(virtualFileStates);
  //   } else {
  //     setRemoteFileAttachments([]);
  //   }
  // }, [selectedFiles]);

  // Update suggestion handler to handle PAL differently
  const handleSuggestionSelect = (suggestion: Suggestion) => {
    if (suggestion.type === "QUERY" && suggestion.suggestion_content) {
      if (isIntentContent(suggestion.suggestion_content)) {
        handleSendMessage(suggestion.suggestion_content.text, undefined, [
          suggestion,
        ]);
      }
    } else if (suggestion.type === "PAL") {
      const content = suggestion.suggestion_content;
      if (isPALContent(content)) {
        handleSendMessage(content.title, undefined, [suggestion]);
      }
    } else {
      // For other types, update selected suggestions
      setSelectedSuggestions((prev) => {
        const isSelected = prev.some(
          (selected) =>
            JSON.stringify(selected.suggestion_content) ===
            JSON.stringify(suggestion.suggestion_content)
        );

        if (isSelected) {
          return prev.filter(
            (selected) =>
              JSON.stringify(selected.suggestion_content) !==
              JSON.stringify(suggestion.suggestion_content)
          );
        } else {
          return [...prev, suggestion];
        }
      });
    }
  };

  // Add new state for streaming
  const [isStreaming, setIsStreaming] = useState(false);

  // First, modify setupChat to return a Promise
  const setupChat = async () => {
    if (apiCallInProgress.current || isSetupComplete) {
      return false; // Return false to indicate setup was skipped
    }

    try {
      apiCallInProgress.current = true;

      if (!chatId) {
        throw new Error("No chat ID provided");
      }

      let conversation;

      if (!activeConversation) {
        const response = await createConversation({
          id: chatId,
          model: PalEnum.ANALYST_PAL,
        }).unwrap();

        conversation = response;
      } else {
        const response = await fetch(`/api/proxy/chat/conversations/${chatId}`);
        if (!response.ok) {
          throw new Error("Failed to fetch conversation");
        }

        const data = await response.json();
        const processedMessages =
          data.chat_messages?.map((msg: Message) => ({
            ...msg,
            suggestions: msg.suggestions || [],
            attachments: msg.attachments || [],
            selected_suggestions: msg.selected_suggestions || [],
          })) || [];

        conversation = {
          ...data,
          messages: processedMessages,
        };
      }

      // Initialize Redux state
      dispatch(setActiveConversation(chatId));
      dispatch(addConversation(conversation));
      dispatch(
        setMessages({
          conversationId: chatId,
          messages: conversation.messages || [],
        })
      );

      await waitForStateUpdate();

      // Validate state
      const state = store.getState();
      const isStateValid =
        state.chat.activeConversationId === chatId &&
        Array.isArray(state.chat.messages[chatId]);

      if (!isStateValid) {
        throw new Error("State initialization failed");
      }

      setIsSetupComplete(true);

      if (chatCreationDetails.pendingCreation) {
        dispatch(clearChatCreationDetails());
      }

      return true; // Return success
    } catch (error) {
      console.error("🔴 [Setup] Failed:", error);
      toast({
        variant: "destructive",
        title: "Setup Failed",
        description:
          error instanceof Error ? error.message : "Failed to initialize chat",
      });
      return false; // Return failure
    } finally {
      apiCallInProgress.current = false;
    }
  };

  // Update handleSendMessage to properly handle setup and streaming
  const handleSendMessage = React.useCallback(
    async (
      content: string,
      initialAttachments?: Attachment[],
      forcedSuggestions?: Suggestion[]
    ) => {
      const currentState = store.getState();

      // Check if chat needs setup
      if (!currentState.chat.activeConversationId || !isSetupComplete) {
        const setupSuccess = await setupChat();
        if (!setupSuccess) {
          return; // Exit if setup failed
        }
      }

      if (!content.trim()) {
        return;
      }

      try {
        // Rest of your existing handleSendMessage code...
        // let messageAttachments: Attachment[] = [];

        // if (initialAttachments) {
        //   messageAttachments = initialAttachments;
        // } else {
        //   messageAttachments = [...processedAttachments];
        // }

        // Get fresh state after setup
        const updatedState = store.getState();
        const conversationMessages =
          updatedState.chat.messages[updatedState.chat.activeConversationId];
        const parent_message_id =
          conversationMessages?.length > 0
            ? conversationMessages[conversationMessages.length - 1].id
            : DEFAULT_PARENT_MESSAGE_ID;

        const messageSuggestions = forcedSuggestions || selectedSuggestions;

        // Create messages first
        const userMessage: Message = {
          id: uuidv4(),
          content,
          role: "user",
          parent_message_id,
          conversation_id: updatedState.chat.activeConversationId,
          created_at: new Date().toISOString(),
          // attachments: messageAttachments,
          selected_suggestions: messageSuggestions,
          suggestions: [],
          artifacts: [],
          // files: selectedFiles.map((file: SelectedFile) => ({
          //   id: file.id,
          //   title: file.title,
          //   content: "",
          //   address: file.address,
          // })),
        };

        const assistantMessageId = uuidv4();
        const assistantMessage: Message = {
          id: assistantMessageId,
          content: "",
          role: "assistant",
          parent_message_id: userMessage.id,
          conversation_id: updatedState.chat.activeConversationId,
          created_at: new Date().toISOString(),
          suggestions: [],
          artifacts: [],
        };

        // Prepare request body
        const requestBody = {
          prompt: content,
          parent_message_id,
          // attachments: messageAttachments,
          database_uid: selectedDatabase?.uid || "",
          table_uid: selectedTable?.uid || "",
          // files:
          //   selectedFiles.length > 0
          //     ? selectedFiles.map((file: SelectedFile) => ({
          //         id: file.id,
          //         title: file.title,
          //         content: "",
          //         address: file.address,
          //       }))
          //     : chatCreationDetails.files,
          selected_suggestions: messageSuggestions,
          rendering_mode: "messages",
          sync_sources: [],
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          model: PalEnum.ANALYST_PAL,
          web_search: webSearchEnabled,
        };

        // Add messages to state
        dispatch(
          addMessage({
            conversationId: updatedState.chat.activeConversationId,
            message: userMessage,
          })
        );

        // Add assistant message immediately with thinking state
        dispatch(
          addMessage({
            conversationId: updatedState.chat.activeConversationId,
            message: {
              ...assistantMessage,
              isThinking: true,
              content: "",
            },
          })
        );

        // Clear suggestions and files immediately
        setSelectedSuggestions([]);
        // setFileStates([]);
        setProcessedAttachments([]);
        // setRemoteFileAttachments([]);

        // clear the selected suggestion in the right panel
        dispatch(setSelectedSuggestion(null));

        try {
          const response = await fetch(
            `/api/proxy/chat/conversations/${updatedState.chat.activeConversationId}/completion`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(requestBody),
            }
          );

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          // Start streaming
          setIsStreaming(true);

          const reader = response.body?.getReader();
          if (!reader) throw new Error("No reader available");

          const messageHandler = new MessageStreamHandler(
            dispatch,
            updatedState.chat.activeConversationId,
            assistantMessageId,
            setIsInCodeBlock,
            setCodeBlockLanguage
          );

          // Update message state when streaming starts
          messageHandler.onStreamStart = () => {
            dispatch(
              updateMessage({
                conversationId: updatedState.chat.activeConversationId,
                messageId: assistantMessageId,
                updates: {
                  isThinking: false,
                  isStreaming: true,
                  content: "", // Initialize with empty content
                },
              })
            );
          };

          let buffer = "";
          const decoder = new TextDecoder();

          try {
            while (true) {
              const { done, value } = await reader.read();

              if (done) {
                if (buffer.trim()) {
                  messageHandler.processSSELine(buffer.trim());
                }
                messageHandler.processSSELine("data: [DONE]");
                break;
              }

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split("\n");
              buffer = lines.pop() || "";

              for (const line of lines) {
                if (line.trim()) {
                  messageHandler.processSSELine(line.trim());
                }
              }
            }
          } catch (error) {
            console.error("Error processing stream:", error);
            throw error;
          } finally {
            setIsStreaming(false);
            reader.releaseLock();
          }

          // After streaming completes, refetch the conversation
          try {
            const conversationResponse = await fetch(
              `/api/proxy/chat/conversations/${updatedState.chat.activeConversationId}`
            );

            if (!conversationResponse.ok) {
              throw new Error("Failed to fetch conversation");
            }

            const data = await conversationResponse.json();

            // Process messages to ensure suggestions and attachments are properly structured
            const processedMessages =
              data.chat_messages?.map((msg: Message) => ({
                ...msg,
                suggestions: msg.suggestions || [],
                attachments: msg.attachments || [],
                selected_suggestions: msg.selected_suggestions || [],
              })) || [];

            // Quietly update the conversation in Redux
            dispatch(
              setMessages({
                conversationId: updatedState.chat.activeConversationId,
                messages: processedMessages,
              })
            );

            // Update conversation data
            dispatch(
              addConversation({
                ...data,
                messages: processedMessages,
              })
            );
          } catch (error) {
            console.error("Error refetching conversation:", error);
            // Don't show error toast for refetch failure
          }

          // Clear input state after successful send
          // setFileStates([]);
          setProcessedAttachments([]);
          setSelectedSuggestions([]);
        } catch (error) {
          console.error("Error in handleSendMessage:", error);
          toast({
            variant: "destructive",
            title: "Error",
            description: "Failed to send message",
          });
        } finally {
          // Ensure all states are reset
          setIsStreaming(false);
          // setFileStates([]); // Also clear here to ensure it's always cleared
          setProcessedAttachments([]);
          setSelectedSuggestions([]);
          dispatch(
            setLoading({
              conversationId: updatedState.chat.activeConversationId,
              isLoading: false,
            })
          );
          // Reset the search modal selected files
          // dispatch(resetSelectedFiles());
          // Clear the remote file attachments state
          // setRemoteFileAttachments([]);
        }
      } catch (error) {
        console.error("Error in handleSendMessage:", error);
        toast({
          variant: "destructive",
          title: "Error",
          description: "Failed to send message",
        });
      }
    },
    [
      dispatch,
      selectedSuggestions,
      // selectedFiles,
      webSearchEnabled,
      chatId,
      isSetupComplete,
      selectedDatabase,
      selectedTable,
    ]
  );

  // Add effect to trigger setup
  // useEffect(() => {
  //   if (chatId && !isSetupComplete) {
  //     setupChat();
  //   }
  // }, [chatId, isSetupComplete]);

  // Add an effect to handle initial scroll when messages change
  // useEffect(() => {
  //   if (messages.length > 0 && scrollManagerRef.current) {
  //     scrollManagerRef.current.immediateScrollToBottom();
  //   }
  // }, [messages.length]);

  // Add a ref to track API call
  const apiCallInProgress = useRef(false);

  // Handle fetch errors
  useEffect(() => {
    if (chatId && fetchError && !chatCreationDetails.pendingCreation) {
      console.error("Error fetching conversation:", fetchError);
      // router.push("/home");
    }
  }, [fetchError, chatId, router, chatCreationDetails.pendingCreation]);

  // Add this effect to handle the loading state display
  useEffect(() => {
    if (activeConversation) {
      const isCurrentlyLoading = isLoading || false;
    }
  }, [activeConversation, isLoading]);

  // Update handleFileUpload to process and store attachments
  const [isProcessingFiles, setIsProcessingFiles] = useState(false);

  // Add these new state variables in ChatInterface component
  const [selectedFileState, setSelectedFileState] =
    useState<FileUploadState | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>("");
  const [isFilePreviewOpen, setIsFilePreviewOpen] = useState(false);

  // Update the handleFileClick function
  // const handleFileClick = (file: FileUploadState) => {
  //   setSelectedFileState(file);
  //   // Find the extracted content for this file
  //   const fileAttachment = processedAttachments.find(
  //     (att) => att.file_name === file.file.name
  //   );
  //   setSelectedFileContent(fileAttachment?.extracted_content || "");
  //   setIsFilePreviewOpen(true);
  // };

  // Add a new function to handle message attachment previews
  const handleMessageAttachmentClick = (attachment: Attachment) => {
    // Create a temporary FileUploadState for the preview
    const tempFileState: FileUploadState = {
      id: uuidv4(),
      file: new File([], attachment.file_name, { type: attachment.file_type }),
      status: "complete",
      progress: 100,
    };

    setSelectedFileState(tempFileState);
    setSelectedFileContent(attachment.extracted_content);
    setIsFilePreviewOpen(true);
  };

  // Add these new states inside ChatInterface component
  const [showScrollButton, setShowScrollButton] = useState(false);
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();

  // Add this function inside ChatInterface component
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const div = e.currentTarget;
    const isAtBottom =
      Math.abs(div.scrollHeight - div.clientHeight - div.scrollTop) < 50;

    // Clear existing timeout
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    // Debounce the state update
    scrollTimeoutRef.current = setTimeout(() => {
      setShowScrollButton(!isAtBottom);
    }, 100); // 100ms debounce
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  const scrollToBottom = () => {
    messagesContainerRef.current?.scrollTo({
      top: messagesContainerRef.current.scrollHeight,
      behavior: "smooth",
    });
  };

  useEffect(() => {
    const checkMobile = () => {
      const isMobileView = window.innerWidth < 768;
      setIsMobile(isMobileView);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);

    // Mark the page as ready
    setPageReady(true);

    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Update the chat interface layout
  const renderChatInterface = () => (
    <div className="flex flex-col h-full">
      {chatCreationDetails.chatTitle && (
        <div className="flex-none px-4 py-2 border-b dark:border-zinc-800 bg-white dark:bg-zinc-900">
          <div className="max-w-[800px] mx-auto w-full">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <h1 className="text-xl font-semibold text-foreground dark:text-zinc-100">
                  {chatCreationDetails.chatTitle}
                </h1>
              </div>
              <div className="text-sm text-muted-foreground dark:text-zinc-400">
                {new Date().toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="relative flex-1 overflow-hidden bg-background dark:bg-zinc-900">
        <div
          ref={messagesContainerRef}
          className={cn(
            "absolute inset-0 overflow-y-auto scroll-smooth",
            // Custom scrollbar styles
            // "[&::-webkit-scrollbar]:w-1.5",
            "[&::-webkit-scrollbar-track]:bg-transparent",
            "[&::-webkit-scrollbar-thumb]:bg-muted-foreground/20",
            "[&::-webkit-scrollbar-thumb]:hover:bg-muted-foreground/30",
            "[&::-webkit-scrollbar-thumb]:rounded-full"
          )}
          onScroll={handleScroll}
        >
          <div className="max-w-[800px] mx-auto w-full px-4">
            <div className="py-2 pb-20">
              <AnalyticsMessageList
                messages={messages}
                isLoading={isLoading}
                isStreaming={isStreaming}
                onSuggestionSelect={handleSuggestionSelect}
                selectedSuggestions={selectedSuggestions}
                currentLeafMessageId={
                  conversationData?.current_leaf_message_id || undefined
                }
                onAttachmentClick={handleMessageAttachmentClick}
                isSetupComplete={isSetupComplete}
                isInitialMessageSent={initialMessageSent}
                isLoadingConversation={isLoadingConversation}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="sticky bottom-0 z-10 pb-2 bg-background dark:bg-zinc-900">
        <div className="max-w-[800px] mx-auto px-4 relative">
          <Button
            variant="secondary"
            size="icon"
            className={cn(
              "absolute md:right-8 right-4 z-50 rounded-xl shadow-md md:h-10 md:w-10 h-9 w-9",
              "!bg-background backdrop-blur-sm",
              "transition-opacity duration-200 border border-muted-foreground/50 dark:border-muted-foreground/60 hover:opacity-100 active:opacity-80",
              showScrollButton ? "opacity-80" : "hidden opacity-0",
              "bottom-[calc(100%+1rem)]"
            )}
            onClick={scrollToBottom}
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
          {/* <FileUploadHandler
            onFileUpload={handleFileUpload}
            files={fileStates}
            onRemoveFile={handleRemoveFile}
            processingFiles={processingFiles}
            onFileClick={handleFileClick}
            remoteFiles={remoteFileAttachments}
            selectedFiles={selectedFiles}
            showScrollButton={showScrollButton}
            scrollToBottom={scrollToBottom}
          /> */}
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={isLoading || isProcessingFiles}
            // onAttachmentClick={() => {
            //   const fileInput = document.querySelector(
            //     'input[type="file"]'
            //   ) as HTMLInputElement;
            //   if (fileInput) {
            //     fileInput.click();
            //   }
            // }}
            selectedSuggestions={selectedSuggestions}
            onRemoveSuggestion={(suggestion) =>
              setSelectedSuggestions((prev) =>
                prev.filter(
                  (s) =>
                    JSON.stringify(s.suggestion_content) !==
                    JSON.stringify(suggestion.suggestion_content)
                )
              )
            }
            // hasFiles={fileStates.length > 0}
            // onFilesDrop={handleFilesDrop}
            // isProcessingFiles={isProcessingFiles}
            // setIsSearchOpen={setIsSearchOpen}
            webSearchEnabled={webSearchEnabled}
            setWebSearchEnabled={(value) =>
              dispatch(setWebSearchEnabled(value))
            }
            isAnalytics={true}
          />
        </div>
      </div>
    </div>
  );

  // Remove the loader for new chat creation
  if (chatCreationDetails.pendingCreation) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        {renderChatInterface()}
      </div>
    );
  }

  if (isMobile) {
    return (
      <div className="absolute inset-0 top-0 left-0 flex min-h-screen min-w-screen z-[1000] items-center justify-center p-4 bg-background">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">
            {t("desktopOnlyFeature")}
          </h2>
          <p className="text-muted-foreground">
            {t("desktopOnlyFeatureDescription")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {renderChatInterface()}
      <FilePreviewDialog
        file={selectedFileState}
        isOpen={isFilePreviewOpen}
        onOpenChange={setIsFilePreviewOpen}
        extractedContent={selectedFileContent}
      />
    </div>
  );
};

export default AnalyticsChatInterface;
