import { RootState } from "@/store/store";
import { ChatConversation } from "@/app/(protected)/chat/types/chat";

export const validateConversationSetup = (
  conversation: ChatConversation | undefined,
  chatId: string,
  state: RootState
): boolean => {
  if (!conversation) {
    console.error("No conversation found");
    return false;
  }

  if (conversation.id !== chatId) {
    console.error("Conversation ID mismatch:", {
      conversationId: conversation.id,
      expectedId: chatId,
    });
    return false;
  }

  const hasMessages = !!state.chat.messages[conversation.id];
  const isActiveConversation =
    state.chat.activeConversationId === conversation.id;
  const hasValidState = hasMessages && isActiveConversation;

  if (!hasValidState) {
    console.error("Invalid Redux state:", {
      hasMessages,
      isActiveConversation,
      conversationId: conversation.id,
    });
    return false;
  }

  return true;
};

export const waitForStateUpdate = () =>
  new Promise((resolve) => setTimeout(resolve, 0));
