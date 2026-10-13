import { analyzePost } from "@/lib/analyze";
import { detectLink, douyinAwemeId, instagramCode, tiktokAwemeId, tweetId, youtubeId } from "@/lib/detect";
import { normalizeAweme, normalizeInstagram, normalizeXiaohongshu, ParseError, xiaohongshuVideoId } from "@/lib/normalize";
import { tikhubGet, tokenFor } from "@/lib/tikhub";
import type { ParsePayload, Platform } from "@/lib/types";
import { loadX } from "@/lib/x-post";
import { loadYoutube } from "@/lib/youtube";

export async function parseLink(input: string): Promise<ParsePayload> {
  const text = input.trim();
  if (!text) throw new ParseError("先贴一条链接。");
  if (text.length > 4000) throw new ParseError("这段文字太长了，只留链接或分享文案再试。");
  const detected = detectLink(text);
  if (!detected) {
    throw new ParseError("认不出平台。目前能读抖音、小红书、TikTok、Instagram、YouTube 和 X 的公开链接。");
  }

  if (detected.platform === "youtube") {
    const id = youtubeId(detected.url);
    if (!id) throw new ParseError("这条 YouTube 链接里没有视频编号。");
    return pack(await loadYoutube(detected.url, id));
  }
  if (detected.platform === "x") {
    const id = tweetId(detected.url);
    if (!id) throw new ParseError("这条 X 链接里没有帖子编号。主页链接读不了，需要 status 后面那串数字。");
    return pack(await loadX(detected.url, id));
  }

  const token = tokenFor(detected.platform);
  if (!token) throw new ParseError(`${detected.label} 的 TikHub 令牌还没配上。`, 503);

  const loaded =
    detected.platform === "douyin"
      ? await loadDouyin(detected.url, token)
      : detected.platform === "tiktok"
        ? await loadTiktok(detected.url, token)
        : detected.platform === "xiaohongshu"
          ? await loadXiaohongshu(detected.url, token)
          : await loadInstagram(detected.url, token);
  return pack(loaded);
}

function pack(loaded: { post: ParsePayload["post"]; raw: unknown }): ParsePayload {
  return finish(loaded.post, undefined, loaded.raw);
}

function finish(post: ParsePayload["post"], warning?: string, raw: unknown = post): ParsePayload {
  return { post, analysis: analyzePost(post), warning, raw };
}

async function loadDouyin(url: string, token: string) {
  try {
    const raw = await tikhubGet("/api/v1/douyin/app/v3/fetch_one_video_by_share_url", { share_url: url }, token);
    return { post: normalizeAweme(raw, "douyin", url), raw };
  } catch (error) {
    const id = douyinAwemeId(url);
    if (!id) throw error;
    const raw = await tikhubGet("/api/v1/douyin/app/v3/fetch_one_video", { aweme_id: id }, token);
    return { post: normalizeAweme(raw, "douyin", url), raw };
  }
}

async function loadTiktok(url: string, token: string) {
  try {
    const raw = await tikhubGet("/api/v1/tiktok/app/v3/fetch_one_video_by_share_url", { share_url: url }, token);
    return { post: normalizeAweme(raw, "tiktok", url), raw };
  } catch (error) {
    const id = tiktokAwemeId(url);
    if (!id) throw error;
    const raw = await tikhubGet("/api/v1/tiktok/app/v3/fetch_one_video", { aweme_id: id }, token);
    return { post: normalizeAweme(raw, "tiktok", url), raw };
  }
}

async function loadXiaohongshu(url: string, token: string) {
  const imageRaw = await tikhubGet(
    "/api/v1/xiaohongshu/app_v2/get_image_note_detail",
    { share_text: url },
    token,
  );
  const videoId = xiaohongshuVideoId(imageRaw);
  let raw = imageRaw;
  if (videoId) {
    try {
      raw = await tikhubGet(
        "/api/v1/xiaohongshu/app_v2/get_video_note_detail",
        { note_id: videoId },
        token,
      );
    } catch {
      raw = imageRaw;
    }
  }
  return { post: normalizeXiaohongshu(raw, url), raw };
}

async function loadInstagram(url: string, token: string) {
  const code = instagramCode(url);
  const postUrl = code ? url : url;
  try {
    const raw = await tikhubGet("/api/v1/instagram/v1/fetch_post_by_url", { post_url: postUrl }, token);
    return { post: normalizeInstagram(raw, url), raw };
  } catch (error) {
    try {
      const raw = await tikhubGet(
        "/api/v1/instagram/v2/fetch_post_info",
        { code_or_url: code ?? url },
        token,
      );
      return { post: normalizeInstagram(raw, url), raw };
    } catch {
      throw error;
    }
  }
}

export function isKnownPlatform(value: string): value is Platform {
  return ["douyin", "xiaohongshu", "tiktok", "instagram", "youtube", "x"].includes(value);
}
