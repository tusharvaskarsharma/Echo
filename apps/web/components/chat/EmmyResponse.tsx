"use client";

import { ConversationClient } from "@/components/ConversationClient";

export default function EmmyResponse({ emmyId }: { emmyId: string }) {
  return <ConversationClient emmyId={emmyId} />;
}
