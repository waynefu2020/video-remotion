import { asRecord, textOf } from "@/lib/json";
import { ParseError } from "@/lib/normalize";
import type { Platform } from "@/lib/types";

const BASE = process.env.TIKHUB_BASE_URL || "https://api.tikhub.io";
const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

const SPECIFIC: Record<Platform, string> = {
  douyin: "TIKHUB_TOKEN_DOUYIN",
  xiaohongshu: "TIKHUB_TOKEN_XIAOHONGSHU",
  tiktok: "TIKHUB_TOKEN_TIKTOK",
  instagram: "TIKHUB_TOKEN_INSTAGRAM",
  youtube: "TIKHUB_TOKEN_YOUTUBE",
  x: "TIKHUB_TOKEN_X",
};

export function tokenFor(platform: Platform): string | undefined {
  const specific = process.env[SPECIFIC[platform]]?.trim();
  if (specific) return specific;
  if (platform === "x") return process.env.TIKHUB_TOKEN_TWITTER?.trim() || process.env.TIKHUB_TOKEN?.trim() || undefined;
  return process.env.TIKHUB_TOKEN?.trim() || undefined;
}

export function platformMode(platform: Platform): "tikhub" | "public" | "missing" {
  if (tokenFor(platform)) return "tikhub";
  if (platform === "youtube" || platform === "x") return "public";
  return "missing";
}

export async function tikhubGet(path: string, query: Record<string, string | undefined>, token: string): Promise<unknown> {
  const url = new URL(path, BASE);
  for (const [key, value] of Object.entries(query)) {
    if (value) url.searchParams.set(key, value);
  }
  let response: Response;
  try {
    response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
        "User-Agent": UA,
      },
      cache: "no-store",
      signal: AbortSignal.timeout(35_000),
    });
  } catch {
    throw new ParseError("TikHub 没有在时限内返回，稍后再试一次。", 504);
  }

  const json: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ParseError(readError(json, response.status), response.status === 403 ? 403 : 502);
  }
  const code = asRecord(json)?.code;
  if (typeof code === "number" && code !== 200) {
    throw new ParseError(readError(json, code), 502);
  }
  return json;
}

function readError(json: unknown, status: number): string {
  const record = asRecord(json);
  const detail = asRecord(record?.detail);
  const message =
    textOf(detail?.message_zh) || textOf(record?.message_zh) || textOf(detail?.message) || textOf(record?.message) || "";
  if (status === 403 || message.includes("权限")) {
    return "这枚 TikHub 令牌没有当前平台的接口权限。到用户后台勾上对应平台后再试。";
  }
  if (message.includes("不会被扣费") || message.includes("请求失败")) {
    return "链接没有解析出作品。短链可能过期了，换一条完整链接再试。";
  }
  if (message) return message.slice(0, 180);
  return `TikHub 返回了 ${status}。`;
}
