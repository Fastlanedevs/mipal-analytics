"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Attachment,
  Message,
  Suggestion,
  PALContent,
  FileUploadState,
} from "../types/chat";
import { MessageList } from "@/app/(protected)/chat/components/MessageList";
import { ChatInput } from "@/app/(protected)/chat/components/ChatInput";
import { FileUploadHandler } from "@/app/(protected)/chat/components/FileUpload/FileUploadHandler";
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
  setModel,
  clearModel,
} from "@/store/slices/chatSlice";
import { clearChatCreationDetails } from "@/store/slices/chatCreationSlice";
import {
  setReferences,
  setIsReferencePanelOpen,
} from "@/store/slices/referencesSlice";
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
import { MessageStreamHandler } from "../services/messageHandler";
import { waitForStateUpdate } from "@/lib/utils/chatValidation";
import { cn } from "@/lib/utils";
import FilePreviewDialog from "./FileUpload/FilePreviewDialog";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SearchModal } from "@/components/search/SearchModal";
import {
  removeSelectedFile,
  resetSelectedFiles,
  SelectedFile,
} from "@/store/slices/fileSearchSlice";
import { v4 as uuidv4 } from "uuid";

interface ChatInterfaceProps {
  chatId: string;
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

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ chatId }) => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileId = searchParams?.get("fileId");
  const webSearch = fileId ? true : false;
  const dispatch = useAppDispatch();

  // Get chat creation details from store
  const chatCreationDetails = useAppSelector((state: RootState) => ({
    initialMessage: state.chatCreation.initialMessage,
    chatTitle: state.chatCreation.chatTitle,
    pendingCreation: state.chatCreation.pendingCreation,
    attachments: state.chatCreation.attachments,
    // model: state.chatCreation.model,
    web_search: state.chatCreation.web_search,
    files: state.chatCreation.files,
  }));

  const chatModel = useAppSelector((state: RootState) => state.chat.model);

  // const [webSearchEnabled, setWebSearchEnabled] = useState(chatCreationDetails.web_search);
  const webSearchEnabled = useAppSelector(
    (state) => state.chat.webSearchEnabled
  );

  const activeConversation = useAppSelector(
    (state: RootState) => state.chat.activeConversationId
  );

  // Move createConversation mutation before isLoading selector
  const [createConversation, { isLoading: isCreating, error: createError }] =
    useCreateConversationMutation();

  const messages = useAppSelector(selectMessages);

  // Update the loading state logic
  const isLoading = useAppSelector((state: RootState) => {
    // Only show loading during completion API call, not during conversation fetch
    return activeConversation && state.chat.isLoading[activeConversation];
  });

  const [initialMessageSent, setInitialMessageSent] = useState(false);
  const [fileStates, setFileStates] = useState<FileUploadState[]>([]);
  // const messagesEndRef = useRef<HTMLDivElement>(null);
  const [currentMessage, setCurrentMessage] = useState<string | null>(null);
  const [processingFiles, setProcessingFiles] = useState<Set<string>>(
    new Set()
  );
  const [isSetupComplete, setIsSetupComplete] = useState(false);
  // Open the search modal
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Add a ref to track streaming state
  // const isStreamingRef = useRef(false);
  const streamAbortController = useRef<AbortController | null>(null);

  // Add a ref to track if we're currently processing a message
  const processingRef = useRef(false);

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
  const [remoteFileAttachments, setRemoteFileAttachments] = useState<
    FileUploadState[]
  >([]);

  // Remote files from the file search modal
  const selectedFiles = useAppSelector(
    (state) => state.fileSearch.selectedFiles
  );

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

  // Update suggestion handler to handle PAL differently
  const handleSuggestionSelect = (suggestion: Suggestion) => {
    if (suggestion.type === "PAL") {
      const content = suggestion.suggestion_content;
      if (isPALContent(content)) {
        // For PAL, immediately send the message with the title
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

  // Update handleSendMessage to correctly manage loading and streaming states
  const handleSendMessage = React.useCallback(
    async (
      content: string,
      initialAttachments?: Attachment[],
      forcedSuggestions?: Suggestion[]
    ) => {
      const currentState = store.getState();
      if (!currentState.chat.activeConversationId || !content.trim()) {
        return;
      }

      try {
        // Get the current conversation's messages to determine parent_message_id
        const conversationMessages =
          currentState.chat.messages[currentState.chat.activeConversationId];
        const parent_message_id =
          conversationMessages?.length > 0
            ? conversationMessages[conversationMessages.length - 1].id
            : DEFAULT_PARENT_MESSAGE_ID;

        // Store the current files and suggestions to show with the user message
        const messageAttachments = initialAttachments || processedAttachments;
        const messageSuggestions = forcedSuggestions || selectedSuggestions;
        const messageFiles = selectedFiles.map((file: SelectedFile) => ({
          id: file.id,
          title: file.title,
          content: "",
          address: file.address,
        }));

        // Create messages first
        const userMessage: Message = {
          id: uuidv4(),
          content,
          role: "user",
          parent_message_id,
          conversation_id: currentState.chat.activeConversationId,
          created_at: new Date().toISOString(),
          attachments: messageAttachments,
          selected_suggestions: messageSuggestions,
          suggestions: [],
          artifacts: [],
          files: messageFiles,
        };

        const assistantMessageId = uuidv4();
        const assistantMessage: Message = {
          id: assistantMessageId,
          content: "",
          role: "assistant",
          parent_message_id: userMessage.id,
          conversation_id: currentState.chat.activeConversationId,
          created_at: new Date().toISOString(),
          suggestions: [],
          artifacts: [],
        };

        // Prepare request body
        const requestBody = {
          prompt: content,
          parent_message_id,
          attachments: messageAttachments,
          files:
            selectedFiles.length > 0
              ? selectedFiles.map((file: SelectedFile) => ({
                  id: file.id,
                  title: file.title,
                  content: "",
                  address: file.address,
                }))
              : chatCreationDetails.files,
          selected_suggestions: messageSuggestions,
          rendering_mode: "messages",
          sync_sources: [],
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          model: chatModel, // || chatCreationDetails.model,
          web_search: webSearchEnabled,
        };

        // Add messages to state
        dispatch(
          addMessage({
            conversationId: currentState.chat.activeConversationId,
            message: userMessage,
          })
        );

        // Add assistant message immediately with thinking state
        dispatch(
          addMessage({
            conversationId: currentState.chat.activeConversationId,
            message: {
              ...assistantMessage,
              isThinking: true,
              content: "",
            },
          })
        );

        // Clear suggestions and files immediately
        setSelectedSuggestions([]);
        setFileStates([]);
        setProcessedAttachments([]);
        setRemoteFileAttachments([]);

        try {
          const response = await fetch(
            `/api/proxy/chat/conversations/${currentState.chat.activeConversationId}/completion`,
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

          // Initialize message handler
          const messageHandler = new MessageStreamHandler(
            dispatch,
            currentState.chat.activeConversationId,
            assistantMessageId,
            setIsInCodeBlock,
            setCodeBlockLanguage
            // scrollManagerRef.current
          );

          // Update message state when streaming starts
          messageHandler.onStreamStart = () => {
            dispatch(
              updateMessage({
                conversationId: currentState.chat.activeConversationId,
                messageId: assistantMessageId,
                updates: {
                  isThinking: false,
                  isStreaming: true,
                  content: "", // Initialize with empty content
                },
              })
            );
          };

          const reader = response.body?.getReader();
          if (!reader) throw new Error("No reader available");

          let buffer = "";
          const decoder = new TextDecoder();

          try {
            while (true) {
              const { done, value } = await reader.read();

              if (done) {
                // Process any remaining buffer
                if (buffer.trim()) {
                  messageHandler.processSSELine(buffer.trim());
                }
                // Send final [DONE] event
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
              `/api/proxy/chat/conversations/${currentState.chat.activeConversationId}`
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
                conversationId: currentState.chat.activeConversationId,
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
          setFileStates([]);
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
          setFileStates([]); // Also clear here to ensure it's always cleared
          setProcessedAttachments([]);
          setSelectedSuggestions([]);
          dispatch(
            setLoading({
              conversationId: currentState.chat.activeConversationId,
              isLoading: false,
            })
          );
          // Reset the search modal selected files
          dispatch(resetSelectedFiles());
          // Clear the remote file attachments state
          setRemoteFileAttachments([]);
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
      processedAttachments,
      selectedSuggestions,
      selectedFiles,
      webSearchEnabled,
      chatModel,
    ]
  );

  // Add an effect to handle initial scroll when messages change
  // useEffect(() => {
  //   if (messages.length > 0 && scrollManagerRef.current) {
  //     scrollManagerRef.current.immediateScrollToBottom();
  //   }
  // }, [messages.length]);

  // Add a ref to track API call
  const apiCallInProgress = useRef(false);

  // Modify the query to skip for both new chat creation and no chatId
  const {
    data: conversationData,
    isLoading: isLoadingConversation,
    error: fetchError,
  } = useGetConversationQuery(chatId ?? "", {
    // Skip GET request if we're creating a new chat or don't have a chatId
    skip: !chatId || chatCreationDetails.pendingCreation,
    refetchOnMountOrArgChange: true,
  });

  useEffect(() => {
    if (conversationData?.model && !chatModel) {
      dispatch(setModel(conversationData.model));
    } else {
      dispatch(clearModel());
    }
  }, [conversationData?.model]);

  // Handle fetch errors
  useEffect(() => {
    if (chatId && fetchError && !chatCreationDetails.pendingCreation) {
      console.error("Error fetching conversation:", fetchError);
      router.push("/home");
    }
  }, [fetchError, chatId, router, chatCreationDetails.pendingCreation]);

  // Update the setupChat function to properly handle messages from the backend
  const setupChat = async () => {
    if (apiCallInProgress.current || isSetupComplete) {
      return;
    }

    try {
      apiCallInProgress.current = true;

      if (!chatId) {
        throw new Error("No chat ID provided");
      }

      let conversation;

      if (chatCreationDetails.pendingCreation) {
        const response = await createConversation({
          id: chatId,
          model: null,
        }).unwrap();

        conversation = response;
      } else {
        // Fetch existing conversation with messages
        const response = await fetch(`/api/proxy/chat/conversations/${chatId}`);
        if (!response.ok) {
          throw new Error("Failed to fetch conversation");
        }

        const data = await response.json();

        // Process messages to ensure suggestions and attachments are properly structured
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

      // Set messages from backend
      dispatch(
        setMessages({
          conversationId: chatId,
          messages: conversation.messages || [],
        })
      );

      // Wait for state updates to be processed
      await waitForStateUpdate();

      // Validate state
      const state = store.getState();
      const isStateValid =
        state.chat.activeConversationId === chatId &&
        Array.isArray(state.chat.messages[chatId]);

      if (!isStateValid) {
        throw new Error("State initialization failed");
      }

      // Handle initial message for new conversations
      if (
        chatCreationDetails.pendingCreation &&
        chatCreationDetails.initialMessage
      ) {
        // Verify active conversation is set before sending
        const currentState = store.getState();
        if (currentState.chat.activeConversationId !== chatId) {
          throw new Error("Active conversation not set properly");
        }

        try {
          await handleSendMessage(
            chatCreationDetails.initialMessage,
            chatCreationDetails.attachments,
            undefined // suggestions
          );
          setInitialMessageSent(true);
        } catch (error) {
          console.error("Failed to send initial message:", error);
          throw error;
        }
      }

      // Clear creation details and mark setup as complete
      if (chatCreationDetails.pendingCreation) {
        dispatch(clearChatCreationDetails());
      }
      setIsSetupComplete(true);
    } catch (error) {
      console.error("🔴 [Setup] Failed:", error);
      toast({
        variant: "destructive",
        title: "Setup Failed",
        description:
          error instanceof Error ? error.message : "Failed to initialize chat",
      });
      router.push("/home");
    } finally {
      apiCallInProgress.current = false;
    }
  };

  // Remove the separate effect for handling initial message since we're handling it in setupChat
  useEffect(() => {
    if (chatId && !isSetupComplete) {
      setupChat();
    }
  }, [chatId, isSetupComplete]); // Minimal dependencies to avoid re-runs

  // Add this effect to handle the loading state display
  useEffect(() => {
    if (activeConversation) {
      const isCurrentlyLoading = isLoading || false;
    }
  }, [activeConversation, isLoading]);

  // useEffect(() => {
  //   messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  // }, [messages]);

  // Update handleFileUpload to process and store attachments
  const [isProcessingFiles, setIsProcessingFiles] = useState(false);

  const handleFileUpload = async (newFiles: File[]) => {
    try {
      setIsProcessingFiles(true);

      const newFileStates: FileUploadState[] = newFiles.map((file) => ({
        id: uuidv4(),
        file,
        status: "pending",
        progress: 0,
        preview: file.type.startsWith("image/")
          ? URL.createObjectURL(file)
          : undefined,
      }));

      setFileStates((prev) => [...prev, ...newFileStates]);

      for (const fileState of newFileStates) {
        try {
          // Update status to uploading first
          setFileStates((states) =>
            states.map((state) =>
              state.id === fileState.id
                ? { ...state, status: "uploading", progress: 0 }
                : state
            )
          );

          if (isComplexFile(fileState.file)) {
            const formData = new FormData();
            formData.append("file", fileState.file);

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

            try {
              const response = await fetch("/api/proxy/chat/extract", {
                method: "POST",
                body: formData,
              });

              clearInterval(progressInterval);

              if (!response.ok) {
                throw new Error(
                  `Failed to process file: ${response.statusText}`
                );
              }

              const processedFile = await response.json();

              setProcessedAttachments((prev) => [
                ...prev,
                {
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
            } catch (error) {
              clearInterval(progressInterval);
              throw error;
            }
          } else {
            // Handle simple text files
            const content = await readTextFile(fileState.file);
            setProcessedAttachments((prev) => [
              ...prev,
              {
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
        } catch (error) {
          console.error(`Error processing file ${fileState.file.name}:`, error);
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
                    progress: 0,
                  }
                : state
            )
          );
        }
      }
    } catch (error) {
      console.error("Error uploading files:", error);
    } finally {
      setIsProcessingFiles(false);
    }
  };

  // Update handleRemoveFile to also remove processed attachments
  const handleRemoveFile = (fileId: string) => {
    setFileStates((prev) => {
      const fileToRemove = prev.find((f) => f.id === fileId);
      if (fileToRemove?.preview) {
        URL.revokeObjectURL(fileToRemove.preview);
      }
      return prev.filter((f) => f.id !== fileId);
    });

    setProcessedAttachments((prev) => {
      const fileState = fileStates.find((f) => f.id === fileId);
      return prev.filter((att) => att.file_name !== fileState?.file.name);
    });
    setRemoteFileAttachments((prev) => prev.filter((f) => f.id !== fileId));
    dispatch(removeSelectedFile(fileId));
  };

  // Add these new state variables in ChatInterface component
  const [selectedFileState, setSelectedFileState] =
    useState<FileUploadState | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>("");
  const [isFilePreviewOpen, setIsFilePreviewOpen] = useState(false);

  // Update the handleFileClick function
  const handleFileClick = (file: FileUploadState) => {
    setSelectedFileState(file);
    // Find the extracted content for this file
    const fileAttachment = processedAttachments.find(
      (att) => att.file_name === file.file.name
    );
    setSelectedFileContent(fileAttachment?.extracted_content || "");
    setIsFilePreviewOpen(true);
  };

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

  // Add the function declaration before the return statement in ChatInterface component
  const handleFilesDrop: FileDropHandler = (files) => {
    if (files.length > 0) {
      handleFileUpload(files);
    }
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

  const maxWidth = 800;

  // Update the chat interface layout
  const renderChatInterface = () => (
    <div className="flex flex-col h-full">
      {chatCreationDetails.chatTitle && (
        <div className="flex-none px-4 py-2 border-b dark:border-zinc-800 bg-background dark:bg-zinc-900">
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

      <div className="relative flex-1 overflow-hidden bg-white dark:bg-zinc-900">
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
          <div className="md:max-w-[1000px] mx-auto w-full px-4">
            <div className="py-2 pb-20">
              <MessageList
                messages={messages}
                isLoading={isLoading}
                isStreaming={isStreaming}
                onSuggestionSelect={handleSuggestionSelect}
                selectedSuggestions={selectedSuggestions}
                currentLeafMessageId={
                  conversationData?.current_leaf_message_id || undefined
                }
                onAttachmentClick={handleMessageAttachmentClick}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="sticky bottom-0 z-10 pb-2 bg-background dark:bg-zinc-900">
        <div className={`max-w-[${maxWidth}px] mx-auto px-4 relative`}>
          <FileUploadHandler
            onFileUpload={handleFileUpload}
            files={fileStates}
            onRemoveFile={handleRemoveFile}
            processingFiles={processingFiles}
            onFileClick={handleFileClick}
            remoteFiles={remoteFileAttachments}
            selectedFiles={selectedFiles}
            showScrollButton={showScrollButton}
            scrollToBottom={scrollToBottom}
          />
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={isLoading || isProcessingFiles}
            onAttachmentClick={() => {
              const fileInput = document.querySelector(
                'input[type="file"]'
              ) as HTMLInputElement;
              if (fileInput) {
                fileInput.click();
              }
            }}
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
            hasFiles={fileStates.length > 0}
            onFilesDrop={handleFilesDrop}
            isProcessingFiles={isProcessingFiles}
            setIsSearchOpen={setIsSearchOpen}
            webSearchEnabled={webSearchEnabled}
            setWebSearchEnabled={(value) =>
              dispatch(setWebSearchEnabled(value))
            }
            maxWidth={maxWidth}
          />
        </div>
      </div>
      <SearchModal
        isSearchOpen={isSearchOpen}
        setIsSearchOpen={setIsSearchOpen}
      />
    </div>
  );

  // Add cleanup effect when chatId changes - MOVED UP before any conditional returns
  useEffect(() => {
    // Clear messages when chatId changes
    dispatch(clearMessages());

    // Reset states
    setIsStreaming(false);
    setIsSetupComplete(false);
    setInitialMessageSent(false);
    setFileStates([]);
    setProcessedAttachments([]);
    setSelectedSuggestions([]);

    // Clear references when component mounts (new chat)
    dispatch(setReferences([]));
    dispatch(setIsReferencePanelOpen(false));

    // Clear any ongoing streams
    if (streamAbortController.current) {
      streamAbortController.current.abort();
      streamAbortController.current = null;
    }
  }, [chatId, dispatch]);

  // Remove the loader for new chat creation
  if (chatCreationDetails.pendingCreation) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        {renderChatInterface()}
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

export default ChatInterface;
