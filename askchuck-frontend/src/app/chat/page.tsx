"use client";

import { ChatContainer } from "@/components/chat/ChatContainer";

export default function ChatPage() {
  return (
    <div className="h-screen flex">
      {/* Main chat area */}
      <main className="flex-1 flex flex-col">
        <ChatContainer />
      </main>
    </div>
  );
}
