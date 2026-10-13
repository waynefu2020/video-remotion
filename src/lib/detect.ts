import { PLATFORM_LABEL, type Platform } from "@/lib/types";

const HOSTS: Array<{ platform: Platform; test: RegExp }> = [
  { platform: "douyin", test: /(^|\.)douyin\.com$|(^|\.)iesdouyin\.com$/i },
  {
    platform: "xiaohongshu",
    test: /(^|\.)xiaohongshu\.com$|(^|\.)xhslink\.com$|(^|\.)xhslink\.cn$/i,
  },
  { platform: "tiktok", test: /(^|\.)tiktok\.com$/i },
  { platform: "instagram", test: /(^|\.)instagram\.com$|(^|\.)instagr\.am$/i },
  {
    platform: "youtube",
    test: /(^|\.)youtube\.com$|(^|\.)youtube-nocookie\.com$|^youtu\.be$/i,
  },
  { platform: "x", test: /(^|\.)x\.com$|(^|\.)twitter\.com$/i },
];

export type DetectedLink = {
  platform: Platform;
  label: string;
  url: string;
};

export function detectLink(input: string): DetectedLink | null {
  const url = extractUrl(input);
  if (!url) return null;
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  const host = parsed.hostname.replace(/^www\./i, "");
  const match = HOSTS.find((item) => item.test.test(host) || item.test.test(parsed.hostname));
  if (!match) return null;
  return { platform: match.platform, label: PLATFORM_LABEL[match.platform], url };
}

function extractUrl(input: string): string | null {
  const text = input.trim();
  if (!text) return null;
  const explicit = text.match(/https?:\/\/[^\s<>"'“”]+/i);
  if (explicit) return tidy(explicit[0]);
  const bare = text.match(
    /(?:v\.douyin\.com|www\.douyin\.com|douyin\.com|xhslink\.com|xhslink\.cn|www\.xiaohongshu\.com|xiaohongshu\.com|vm\.tiktok\.com|vt\.tiktok\.com|www\.tiktok\.com|tiktok\.com|www\.instagram\.com|instagram\.com|youtu\.be|www\.youtube\.com|youtube\.com|x\.com|twitter\.com)\/[^\s<>"'“”]+/i,
  );
  if (bare) return tidy(`https://${bare[0]}`);
  return null;
}

function tidy(url: string): string {
  return url.replace(/[)）】\]>,，。、；;!！?？]+$/g, "");
}

export function douyinAwemeId(url: string): string | undefined {
  return url.match(/(?:video|note|slides)\/(\d{8,})/)?.[1] ?? url.match(/[?&]modal_id=(\d{8,})/)?.[1];
}

export function tiktokAwemeId(url: string): string | undefined {
  return url.match(/\/video\/(\d{8,})/)?.[1];
}

export function youtubeId(url: string): string | undefined {
  try {
    const parsed = new URL(url);
    if (parsed.hostname === "youtu.be") {
      const id = parsed.pathname.split("/").filter(Boolean)[0];
      return id || undefined;
    }
    const watch = parsed.searchParams.get("v");
    if (watch) return watch;
    const parts = parsed.pathname.split("/").filter(Boolean);
    const marker = parts.findIndex((part) => ["shorts", "embed", "live", "v"].includes(part));
    if (marker >= 0 && parts[marker + 1]) return parts[marker + 1];
  } catch {
    return undefined;
  }
  return undefined;
}

export function tweetId(url: string): string | undefined {
  return url.match(/status(?:es)?\/(\d{6,})/)?.[1];
}

export function instagramCode(url: string): string | undefined {
  return url.match(/\/(?:p|reel|reels|tv)\/([A-Za-z0-9_-]+)/)?.[1];
}
