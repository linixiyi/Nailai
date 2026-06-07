import { searchStyles } from "@/lib/styles";

export async function POST(request: Request) {
  const body = await request.json();
  const serviceUrl = process.env.AI_SERVICE_URL;

  if (serviceUrl) {
    try {
      const upstream = await fetch(`${serviceUrl}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (upstream.ok) return Response.json(await upstream.json());
    } catch {
      // Local fallback keeps the MVP demo usable when the Python service is offline.
    }
  }

  const message = String(body.message ?? "");
  const recommended = searchStyles(message, 5);
  return Response.json({
    reply: `我先按你的描述推荐 ${recommended.slice(0, 3).map((style) => style.name).join("、")}。选中任一款后可以直接进入试戴。`,
    intent: message.includes("婚礼") ? "occasion_wedding" : "style_explore",
    recommended_styles: recommended,
    follow_up_questions: ["偏短甲还是中长甲？", "更想要低调通勤还是拍照出片？"],
  });
}
