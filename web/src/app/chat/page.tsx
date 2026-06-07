import { ChatRecommendScreen } from "@/components/prototype/ChatRecommendScreen";
import { Suspense } from "react";

export default function ChatAliasPage() {
  return (
    <Suspense fallback={null}>
      <ChatRecommendScreen />
    </Suspense>
  );
}
