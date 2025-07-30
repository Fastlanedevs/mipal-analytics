import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { ChatConversation, Message } from "@/app/(protected)/chat/types/chat";

// Add new interface for meta content
interface ThinkingDescription {
  title: string;
  type?: string;
  execution?: string;
  status: "completed" | "inprogress" | "pending" | "error";
}

interface ThinkingStep {
  id: string;
  title: string;
  status: "completed" | "inprogress" | "pending" | "error";
  type?: string;
  description: ThinkingDescription[];
}
export interface ChatState {
  activeConversationId: string | null;
  messages: Record<string, Message[]>;
  isLoading: Record<string, boolean>;
  conversations: ChatConversation[];
  error: Record<string, string | null>;
  editingMessageId: string | null;
  fileContents: Record<string, string>;
  // When a user clicks on an artifact, this message content is stored in the store to show it in the artifact panel data tab.
  selectedArtifactMessageContent?: string;
  selectedArtifactMessageId?: string;
  // Add tracking for meta content during streaming
  metaContent: Record<string, ThinkingStep[]>;
  webSearchEnabled: boolean;
  model?: string;
}

const initialState: ChatState = {
  activeConversationId: null,
  messages: {},
  isLoading: {},
  conversations: [],
  error: {},
  editingMessageId: null,
  fileContents: {},
  selectedArtifactMessageContent: undefined,
  selectedArtifactMessageId: undefined,
  // Initialize meta content storage
  metaContent: {},
  webSearchEnabled: false,
  model: undefined,
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    setActiveConversation: (state, action: PayloadAction<string>) => {
      state.activeConversationId = action.payload;
      if (!state.messages[action.payload]) {
        state.messages[action.payload] = [];
      }
    },
    addConversation: (state, action: PayloadAction<ChatConversation>) => {
      const existingIndex = state.conversations.findIndex(
        (c) => c.id === action.payload.id
      );

      if (existingIndex !== -1) {
        state.conversations[existingIndex] = JSON.parse(
          JSON.stringify(action.payload)
        );
      } else {
        state.conversations.push(JSON.parse(JSON.stringify(action.payload)));
      }

      if (!state.messages[action.payload.id]) {
        state.messages[action.payload.id] = [];
      }
    },
    updateConversation: (
      state,
      action: PayloadAction<{ id: string; updates: Partial<ChatConversation> }>
    ) => {
      const conversation = state.conversations.find(
        (c) => c.id === action.payload.id
      );
      if (conversation) {
        Object.assign(conversation, action.payload.updates);
      }
    },
    setMessages: (
      state,
      action: PayloadAction<{ conversationId: string; messages: Message[] }>
    ) => {
      const { conversationId, messages } = action.payload;
      state.messages[conversationId] = JSON.parse(JSON.stringify(messages));
    },
    addMessage: (
      state,
      action: PayloadAction<{ conversationId: string; message: Message }>
    ) => {
      const { conversationId, message } = action.payload;

      if (!state.messages[conversationId]) {
        state.messages[conversationId] = [];
      }

      const existingIndex = state.messages[conversationId].findIndex(
        (m) => m.id === message.id
      );
      if (existingIndex === -1) {
        state.messages[conversationId].push(
          JSON.parse(JSON.stringify(message))
        );
      }
    },
    updateMessage: (
      state,
      action: PayloadAction<{
        conversationId: string;
        messageId: string;
        updates: Partial<Message>;
      }>
    ) => {
      const { conversationId, messageId, updates } = action.payload;
      const messageIndex = state.messages[conversationId]?.findIndex(
        (msg) => msg.id === messageId
      );

      if (messageIndex !== undefined && messageIndex !== -1) {
        state.messages[conversationId][messageIndex] = {
          ...state.messages[conversationId][messageIndex],
          ...updates,
        };
      }
    },
    setEditingMessageId: (state, action: PayloadAction<string | null>) => {
      state.editingMessageId = action.payload;
    },
    setLoading: (
      state,
      action: PayloadAction<{ conversationId: string; isLoading: boolean }>
    ) => {
      if (!state.isLoading) {
        state.isLoading = {};
      }
      state.isLoading[action.payload.conversationId] = action.payload.isLoading;
    },
    setError: (
      state,
      action: PayloadAction<{ conversationId: string; error: string | null }>
    ) => {
      state.error[action.payload.conversationId] = action.payload.error;
    },
    setFileContent: (
      state,
      action: PayloadAction<{ fileName: string; content: string }>
    ) => {
      state.fileContents[action.payload.fileName] = action.payload.content;
    },
    removeFileContent: (state, action: PayloadAction<string>) => {
      delete state.fileContents[action.payload];
    },
    clearMessages: (state) => {
      state.messages = {};
      state.activeConversationId = null;
      state.isLoading = {};
    },
    setSelectedArtifactMessageContent: (
      state,
      action: PayloadAction<string>
    ) => {
      state.selectedArtifactMessageContent = action.payload;
    },
    setSelectedArtifactMessageId: (state, action: PayloadAction<string>) => {
      state.selectedArtifactMessageId = action.payload;
    },
    resetToInitialChatState: (state) => {
      state.activeConversationId = null;
      state.messages = {};
      state.isLoading = {};
      state.conversations = [];
      state.selectedArtifactMessageContent = undefined;
      state.selectedArtifactMessageId = undefined;
      state.editingMessageId = null;
      state.fileContents = {};
      state.error = {};
    },
    // Add a new action to update meta content specifically
    updateMetaContent: (
      state,
      action: PayloadAction<{
        messageId: string;
        metaContent: ThinkingStep[];
      }>
    ) => {
      const { messageId, metaContent } = action.payload;

      // Find the message across all conversations
      let foundMessage = false;
      Object.keys(state.messages).forEach((convId) => {
        const messageIndex = state.messages[convId]?.findIndex(
          (msg) => msg.id === messageId
        );

        if (messageIndex !== -1 && messageIndex !== undefined) {
          foundMessage = true;
          state.messages[convId][messageIndex].metaContent = metaContent;
        }
      });
    },
    // Add a new action to update meta content specifically
    updateArtifactsContent: (
      state,
      action: PayloadAction<{
        messageId: string;
        artifacts: any[];
      }>
    ) => {
      const { messageId, artifacts } = action.payload;

      // Find the message across all conversations and update its artifacts
      Object.keys(state.messages).forEach((convId) => {
        const messageIndex = state.messages[convId]?.findIndex(
          (msg) => msg.id === messageId
        );

        if (messageIndex !== -1 && messageIndex !== undefined) {
          state.messages[convId][messageIndex].artifacts = artifacts;
        }
      });
    },
    // Add function to clear meta content when conversation is cleared
    clearMetaContent: (state, action: PayloadAction<string>) => {
      const messageId = action.payload;
      delete state.metaContent[messageId];
    },
    setWebSearchEnabled: (state, action: PayloadAction<boolean>) => {
      state.webSearchEnabled = action.payload;
    },
    setModel: (state, action: PayloadAction<string>) => {
      state.model = action.payload;
    },
    clearModel: (state) => {
      state.model = undefined;
    },
  },
});

export const {
  setActiveConversation,
  addConversation,
  updateConversation,
  setMessages,
  addMessage,
  updateMessage,
  setEditingMessageId,
  setLoading,
  setError,
  setFileContent,
  removeFileContent,
  clearMessages,
  setSelectedArtifactMessageContent,
  setSelectedArtifactMessageId,
  resetToInitialChatState,
  updateMetaContent,
  updateArtifactsContent,
  clearMetaContent,
  setWebSearchEnabled,
  setModel,
  clearModel,
} = chatSlice.actions;

export default chatSlice.reducer;
