import { findStyle } from "@/lib/styles";

function mockResult(styleId: string | null) {
  const style = findStyle(styleId);
  const [a, b, c] = style.palette;
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="960" height="720" viewBox="0 0 960 720">
      <rect width="960" height="720" fill="#f7f3ee"/>
      <path d="M222 561c-27-88-13-176 29-238 38-57 86-91 145-98 67-8 153 10 222 45 72 36 116 92 122 157 7 73-29 130-95 153-112 39-346 42-423-19z" fill="#e8c7b4"/>
      <g transform="translate(260 245)">
        ${[0, 1, 2, 3, 4].map((i) => `<rect x="${i * 88}" y="${i % 2 ? 18 : 0}" width="48" height="130" rx="24" fill="${[a, b, c][i % 3]}" stroke="#fff" stroke-width="8"/>`).join("")}
      </g>
      <text x="480" y="650" text-anchor="middle" font-family="Arial" font-size="32" fill="#171717">${style.name}</text>
    </svg>
  `;
  return {
    job_id: `local-${Date.now()}`,
    status: "succeeded",
    channel: "local-mock",
    style,
    hand_confidence: 0.86,
    quality_score: 0.82,
    result_image_url: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`,
  };
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const styleId = formData.get("style_id")?.toString() ?? null;
  const stylePayload = formData.get("style_payload")?.toString() ?? null;
  const serviceUrl = process.env.AI_SERVICE_URL;
  const handImage = formData.get("image");
  const styleImage = formData.get("style_image");

  if (serviceUrl) {
    const upstreamForm = new FormData();
    if (handImage instanceof File) upstreamForm.append("image", handImage);
    if (styleImage instanceof File) upstreamForm.append("style_image", styleImage);
    if (styleId) upstreamForm.append("style_id", styleId);
    if (stylePayload) upstreamForm.append("style_payload", stylePayload);

    try {
      const upstream = await fetch(`${serviceUrl}/api/v1/nail/try-on`, {
        method: "POST",
        body: upstreamForm,
      });

      if (upstream.ok) {
        return Response.json(await upstream.json());
      }

      return new Response(await upstream.text(), {
        status: upstream.status,
        headers: { "content-type": upstream.headers.get("content-type") ?? "text/plain; charset=utf-8" },
      });
    } catch (error) {
      return Response.json(
        {
          detail: "AI service unavailable",
          error: error instanceof Error ? error.message : "unknown upstream error",
        },
        { status: 502 },
      );
    }
  }

  return Response.json(mockResult(styleId));
}
