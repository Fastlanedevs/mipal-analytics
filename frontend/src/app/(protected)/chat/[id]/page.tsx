"use client";

import ChatInterface from "@/app/(protected)/chat/components/ChatInterface";

export default function ChatPage({ params }: { params: { id: string } }) {
  return (
    <div className="flex flex-col h-full bg-muted/10">
      <ChatInterface chatId={params.id} />
    </div>
  );
}
