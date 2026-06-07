import { ChatRecommendScreen } from "@/components/prototype/ChatRecommendScreen";
import { Suspense } from "react";

export default function ChatRecommendPage() {
  return (
    <Suspense fallback={null}>
      <ChatRecommendScreen />
    </Suspense>
  );
}
