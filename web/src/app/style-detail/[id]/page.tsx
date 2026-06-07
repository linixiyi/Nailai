import { StyleDetailScreen } from "@/components/prototype/StyleDetailScreen";

export default async function StyleDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <StyleDetailScreen styleId={id} />;
}
