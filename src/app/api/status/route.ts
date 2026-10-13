import { PLATFORM_LABEL, PLATFORMS, type Platform } from "@/lib/types";
import { tokenFor } from "@/lib/tikhub";

export const dynamic = "force-dynamic";

const GITHUB: Partial<Record<Platform, string>> = {
  youtube: "YouTube.js",
  x: "FxEmbed",
};

export async function GET() {
  const platforms = PLATFORMS.map((id) => {
    const token = Boolean(tokenFor(id));
    const github = GITHUB[id];
    const via = github ?? (token ? "TikHub" : "未配置");
    return {
      id,
      label: PLATFORM_LABEL[id],
      via,
      ready: Boolean(github) || token,
    };
  });
  return Response.json({ platforms });
}
