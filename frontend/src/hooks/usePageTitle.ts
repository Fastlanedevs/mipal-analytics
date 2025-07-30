import { usePathname } from "next/navigation";
import { useDocumentTitle } from "./useDocumentTitle";
import { useAppSelector } from "@/store/hooks";
import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "@/store/store";

const DEFAULT_TITLE = "MI PAL";

const PAGE_TITLES: Record<string, string> = {
  "/": "Home | MI PAL",
  "/home": "Home | MI PAL",
  "/chat": "Chat | MI PAL",
  "/chat/analytics": "Analytics Chat | MI PAL",
  "/dashboard": "Dashboard | MI PAL",
  "/search": "Search | MI PAL",
  "/integration": "Integrations | MI PAL",
  "/history": "History | MI PAL",
  "/meet-assistant": "Meet Assistant | MI PAL",
  "/pals": "Pals | MI PAL",
  "/production-dashboard": "Production Dashboard | MI PAL",
  "/privacy-policy": "Privacy Policy | MI PAL",
  "/terms-of-service": "Terms of Service | MI PAL",
  "/settings/profile": "Profile | MI PAL",
  "/settings/plans": "Plans | MI PAL",
  // "/settings/organization": "Organization | MI PAL",
};

// Create memoized selector for messages
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

export function usePageTitle() {
  const pathname = usePathname();
  const messages = useAppSelector(selectMessages);

  let title =
    PAGE_TITLES[pathname as keyof typeof PAGE_TITLES] || DEFAULT_TITLE;

  // Special handling for chat pages
  if (pathname?.includes("/chat") || pathname?.includes("/chat/analytics")) {
    const chatTitle = messages[0]?.content.slice(0, 20);
    title = `${
      chatTitle
        ? chatTitle
        : pathname?.includes("/chat/analytics")
          ? "Analytics Chat"
          : "Chat"
    } | MI PAL`;
  }

  // Default page titles
  useDocumentTitle(title);
}
