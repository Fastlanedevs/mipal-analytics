import { v4 as uuidv4 } from "uuid";

export const generateChatId = () => {
  return uuidv4();
};

export const DEFAULT_PARENT_MESSAGE_ID = "00000000-0000-0000-0000-000000000000";

export const createSearchParams = (message: string, title: string) => {
  return new URLSearchParams({
    message,
    title,
  }).toString();
};
