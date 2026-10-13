import { hashtagsFrom, mentionsFrom } from "@/lib/json";
import { ParseError } from "@/lib/normalize";
import type { ParsedPost } from "@/lib/types";

type Thumb = { url?: string; width?: number; height?: number };
type CaptionTrack = { base_url?: string; language_code?: string };

let session: Promise<import("youtubei.js").Innertube> | undefined;

async function client() {
  const { Innertube } = await import("youtubei.js");
  session ??= Innertube.create({
    generate_session_locally: true,
    lang: "zh-CN",
    location: "US",
  });
  return session;
}

export async function loadYoutube(pageUrl: string, videoId: string): Promise<{ post: ParsedPost; raw: unknown }> {
  let info: Awaited<ReturnType<import("youtubei.js").Innertube["getInfo"]>>;
  try {
    const yt = await client();
    info = await yt.getInfo(videoId);
  } catch {
    throw new ParseError("YouTube.js 没有读到这个视频，可能已删除或有地区限制。", 502);
  }

  const basic = info.basic_info;
  if (!basic.title) {
    const reason = info.playability_status?.reason || "这个视频暂时不能读，可能是会员片或地区限制。";
    throw new ParseError(reason);
  }

  const description = basic.short_description ?? "";
  const thumbs = (basic.thumbnail ?? []) as Thumb[];
  const cover =
    [...thumbs].sort((a, b) => (b.width ?? 0) - (a.width ?? 0))[0]?.url ??
    `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
  const publishedText = info.primary_info?.published?.text;
  const publishedAt = publishIso(info.page, publishedText);
  const subscribers = info.secondary_info?.owner?.subscriber_count?.text;
  const transcript = await loadTranscript(info.captions?.caption_tracks as CaptionTrack[] | undefined);
  const channelUrl = basic.channel?.url;

  const post: ParsedPost = {
    platform: "youtube",
    source: "public",
    via: "YouTube.js",
    url: basic.url_canonical || pageUrl,
    id: videoId,
    title: basic.title,
    caption: description,
    author: {
      name: basic.author || "未知频道",
      handle: basic.channel_id ?? undefined,
      url: channelUrl || (basic.channel_id ? `https://www.youtube.com/channel/${basic.channel_id}` : undefined),
      bio: subscribers ? `${subscribers}` : undefined,
    },
    stats: {
      likes: typeof basic.like_count === "number" ? basic.like_count : undefined,
      plays: typeof basic.view_count === "number" ? basic.view_count : undefined,
    },
    publishedAt,
    durationMs: basic.duration ? basic.duration * 1000 : undefined,
    hashtags: hashtagsFrom(`${basic.title}\n${description}`),
    mentions: mentionsFrom(description),
    media: [{ kind: "embed", url: `https://www.youtube.com/embed/${videoId}`, cover }],
    form: "video",
    imageCount: 0,
    transcript,
  };

  return {
    post,
    raw: {
      library: "youtubei.js",
      repository: "https://github.com/LuanRT/YouTube.js",
      id: basic.id,
      title: basic.title,
      author: basic.author,
      channel: basic.channel,
      category: basic.category,
      view_count: basic.view_count,
      like_count: basic.like_count,
      duration: basic.duration,
      keywords: basic.keywords,
      published: publishedText,
      subscribers,
      transcript_chars: transcript?.length ?? 0,
    },
  };
}

function publishIso(page: unknown, publishedText?: string): string | undefined {
  const first = Array.isArray(page) ? page[0] : undefined;
  const micro =
    first && typeof first === "object"
      ? (first as { microformat?: { publish_date?: string } }).microformat
      : undefined;
  const iso = micro?.publish_date;
  if (iso && !Number.isNaN(Date.parse(iso))) return new Date(iso).toISOString();
  if (publishedText && !Number.isNaN(Date.parse(publishedText))) return new Date(publishedText).toISOString();
  return undefined;
}

async function loadTranscript(tracks: CaptionTrack[] | undefined): Promise<string | undefined> {
  if (!tracks?.length) return undefined;
  const preferred =
    tracks.find((track) => track.language_code === "zh-Hans") ??
    tracks.find((track) => track.language_code?.startsWith("zh")) ??
    tracks.find((track) => track.language_code === "en") ??
    tracks[0];
  if (!preferred?.base_url) return undefined;
  try {
    const response = await fetch(`${preferred.base_url}&fmt=json3`, {
      signal: AbortSignal.timeout(8_000),
      cache: "no-store",
    });
    if (!response.ok) return undefined;
    const payload = (await response.json()) as { events?: Array<{ segs?: Array<{ utf8?: string }> }> };
    const text = (payload.events ?? [])
      .map((event) => (event.segs ?? []).map((seg) => seg.utf8 ?? "").join(""))
      .join("")
      .replace(/\s+/g, " ")
      .trim();
    return text ? text.slice(0, 4000) : undefined;
  } catch {
    return undefined;
  }
}
