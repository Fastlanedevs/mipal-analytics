import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { Attachment } from "@/app/(protected)/chat/types/chat";
import { SelectedFile } from "./fileSearchSlice";

interface ChatCreationState {
  initialMessage: string;
  chatTitle: string;
  pendingCreation: boolean;
  attachments: Attachment[];
  model?: string;
  web_search?: boolean;
  files?: SelectedFile[];
}

const initialState: ChatCreationState = {
  initialMessage: "",
  chatTitle: "",
  pendingCreation: false,
  attachments: [],
  model: undefined,
  web_search: false,
  files: [],
};

export const chatCreationSlice = createSlice({
  name: "chatCreation",
  initialState,
  reducers: {
    setChatCreationDetails: (
      state,
      action: PayloadAction<{
        initialMessage: string;
        chatTitle: string;
        attachments?: Attachment[];
        model?: string;
        web_search?: boolean;
        files?: SelectedFile[];
      }>
    ) => {
      state.initialMessage = action.payload.initialMessage;
      state.chatTitle = action.payload.chatTitle;
      state.pendingCreation = true;
      state.attachments = action.payload.attachments || [];
      state.model = action.payload.model;
      state.web_search = action.payload.web_search || false;
      state.files = action.payload.files || [];
    },
    clearChatCreationDetails: (state) => {
      state.initialMessage = "";
      state.chatTitle = "";
      state.pendingCreation = false;
      state.attachments = [];
      state.model = undefined;
      state.web_search = false;
      state.files = [];
    },
  },
});

export const { setChatCreationDetails, clearChatCreationDetails } =
  chatCreationSlice.actions;

export default chatCreationSlice.reducer;
