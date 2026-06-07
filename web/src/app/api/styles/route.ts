import { nailStyles } from "@/lib/styles";

export async function GET() {
  const serviceUrl = process.env.AI_SERVICE_URL;
  if (serviceUrl) {
    try {
      const upstream = await fetch(`${serviceUrl}/api/v1/styles`, { cache: "no-store" });
      if (upstream.ok) return Response.json(await upstream.json());
    } catch {
      // Keep local development usable when the Python service is offline.
    }
  }

  return Response.json({ styles: nailStyles });
}
