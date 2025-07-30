import { ChatState } from "./slices/chatSlice";
import { chatCreationSlice } from "./slices/chatCreationSlice";
import { chatApi } from "./services/chatApi";

export interface RootState {
  chat: ChatState;
  chatCreation: typeof chatCreationSlice;
  [chatApi.reducerPath]: ReturnType<typeof chatApi.reducer>;
  // Add other API reducers here if you have any
}

export type PalType = "FREE_PLAN" | "ENTERPRISE_PLAN";

export interface Pal {
  id: string;
  name: string;
  pal_enum: string;
  description: string;
  type: PalType;
  is_active: boolean;
  image: string;
  suggestions: string[];
}
