import { AiTryOnScreen } from "@/components/prototype/AiTryOnScreen";

export default async function AiTryOnPage({ searchParams }: { searchParams: Promise<{ styleId?: string }> }) {
  const params = await searchParams;
  return <AiTryOnScreen initialStyleId={params.styleId} />;
}
