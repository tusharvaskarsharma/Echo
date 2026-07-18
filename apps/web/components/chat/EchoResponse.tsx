"use client";

import { ConversationClient } from "@/components/ConversationClient";

export default function EchoResponse({ echoId }: { echoId: string }) {
  return <ConversationClient echoId={echoId} />;
}
