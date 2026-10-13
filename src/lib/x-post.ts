import { asArray, asRecord, mentionsFrom, hashtagsFrom, textOf } from "@/lib/json";
import { normalizeTweet, ParseError } from "@/lib/normalize";
import type { MediaItem, ParsedPost } from "@/lib/types";

const UA = "jingxi/0.1 (social video desk; +https://github.com/FxEmbed/FxEmbed)";

/**
 * Public X readers, both from GitHub:
 * - FxEmbed status API: https://github.com/FxEmbed/FxEmbed
 * - Syndication token from vercel/react-tweet:
 *   https://github.com/vercel/react-tweet/blob/main/packages/react-tweet/src/api/fetch-tweet.ts
 */
export async function loadX(pageUrl: string, id: string): Promise<{ post: ParsedPost; raw: unknown }> {
  const fx = await tryFx(pageUrl, id);
  if (fx.post) return fx.post;
  const syndicated = await trySyndication(pageUrl, id);
  if (syndicated?.post) return syndicated.post;
  if (syndicated?.gone) throw new ParseError(syndicated.gone);
  throw new ParseError(fx.reason || "这条帖子读不到，可能已删除、受限，或两个公开接口都没有返回。", 502);
}

async function tryFx(pageUrl: string, id: string): Promise<{ post?: { post: ParsedPost; raw: unknown }; reason?: string }> {
  const endpoints = [`https://api.fxtwitter.com/status/${id}`, `https://api.vxtwitter.com/Twitter/status/${id}`];
  let reason = "FxEmbed 没有返回这条帖子。";
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, {
        headers: { "User-Agent": UA, Accept: "application/json" },
        signal: AbortSignal.timeout(20_000),
        cache: "no-store",
      });
      const json: unknown = await response.json().catch(() => null);
      const record = asRecord(json);
      if (!response.ok || !record || record.code !== 200 || !record.tweet) {
        const message = textOf(record?.message);
        reason =
          message === "NOT_FOUND"
            ? "这条帖子不存在或已被删除。"
            : message === "PRIVATE_TWEET"
              ? "这条帖子是私密的，公开接口读不到。"
              : message || `FxEmbed 返回了 ${response.status}。`;
        continue;
      }
      const post = normalizeTweet(json, pageUrl);
      post.via = endpoint.includes("vxtwitter") ? "vxTwitter" : "FxEmbed";
      post.source = "public";
      return { post: { post, raw: json } };
    } catch {
      reason = "FxEmbed 超时了。";
    }
  }
  return { reason };
}

async function trySyndication(
  pageUrl: string,
  id: string,
): Promise<{ post?: { post: ParsedPost; raw: unknown }; gone?: string } | null> {
  if (!/^\d{6,40}$/.test(id)) return null;
  const url = new URL("https://cdn.syndication.twimg.com/tweet-result");
  url.searchParams.set("id", id);
  url.searchParams.set("lang", "zh");
  url.searchParams.set("token", syndicationToken(id));
  try {
    const response = await fetch(url, {
      headers: { "User-Agent": UA, Accept: "application/json" },
      signal: AbortSignal.timeout(20_000),
      cache: "no-store",
    });
    if (!response.ok) return null;
    const json: unknown = await response.json().catch(() => null);
    const tweet = asRecord(json);
    if (!tweet || Object.keys(tweet).length === 0) return null;
    if (tweet.__typename === "TweetTombstone") {
      const tombstone = asRecord(tweet.tombstone);
      const text = asRecord(tombstone?.text);
      return { gone: textOf(text?.text) || "这条帖子已被作者删除。" };
    }
    return { post: { post: fromSyndication(tweet, pageUrl, id), raw: json } };
  } catch {
    return null;
  }
}

function syndicationToken(id: string): string {
  return ((Number(id) / 1e15) * Math.PI).toString(36).replace(/(0+|\.)/g, "");
}

function fromSyndication(tweet: Record<string, unknown>, pageUrl: string, id: string): ParsedPost {
  const user = asRecord(tweet.user) ?? {};
  const caption = textOf(tweet.text) ?? "";
  const handle = textOf(user.screen_name);
  const video = asRecord(tweet.video);
  const variants = asArray(video?.variants).map((item) => asRecord(item)).filter((item): item is Record<string, unknown> => Boolean(item));
  const mp4s = variants.filter((item) => (textOf(item.type) ?? "").includes("mp4") || (textOf(item.src) ?? "").includes(".mp4"));
  const mp4 = mp4s.at(-1);
  const media: MediaItem[] = [];
  const poster = textOf(video?.poster);
  const videoUrl = textOf(mp4?.src) ?? textOf(variants[0]?.src);
  if (videoUrl) media.push({ kind: "video", url: videoUrl, cover: poster });
  for (const photo of asArray(tweet.photos)) {
    const record = asRecord(photo);
    const url = textOf(record?.url) ?? textOf(record?.media_url_https);
    if (url) media.push({ kind: "image", url, cover: url, width: numberOf(record?.width), height: numberOf(record?.height) });
  }
  for (const item of asArray(tweet.mediaDetails)) {
    const record = asRecord(item);
    const url = textOf(record?.media_url_https);
    if (url && !media.some((entry) => entry.url === url)) media.push({ kind: "image", url, cover: url });
  }
  const likes = numberOf(tweet.favorite_count);
  return {
    platform: "x",
    source: "public",
    via: "Syndication",
    url: handle ? `https://x.com/${handle}/status/${id}` : pageUrl,
    id,
    caption,
    author: {
      name: textOf(user.name) ?? handle ?? "未知作者",
      handle,
      avatar: textOf(user.profile_image_url_https),
      url: handle ? `https://x.com/${handle}` : undefined,
    },
    stats: {
      likes,
      comments: numberOf(tweet.conversation_count),
    },
    publishedAt: textOf(tweet.created_at),
    durationMs: numberOf(video?.durationMs),
    hashtags: hashtagsFrom(caption),
    mentions: mentionsFrom(caption),
    media,
    form: media.some((item) => item.kind === "video") ? "video" : media.length ? "images" : "text",
    imageCount: media.filter((item) => item.kind === "image").length,
  };
}

function numberOf(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}
