import { ParseError } from "@/lib/normalize";
import { parseLink } from "@/lib/parse-link";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "请求不是 JSON。" }, { status: 400 });
  }
  const text = typeof body === "object" && body && "text" in body ? (body as { text?: unknown }).text : undefined;
  if (typeof text !== "string") {
    return Response.json({ error: "把链接放在 text 里。" }, { status: 400 });
  }
  try {
    const result = await parseLink(text);
    return Response.json(result);
  } catch (error) {
    if (error instanceof ParseError) {
      return Response.json({ error: error.message }, { status: error.status });
    }
    return Response.json({ error: "拆片时出了意外，再试一次。" }, { status: 500 });
  }
}
