import { mentionsFrom, hashtagsFrom, asArray, asRecord, countOrMissing, firstUrl, numberOf, textOf, unixToIso } from "@/lib/json";
import type { MediaItem, ParsedPost, Platform } from "@/lib/types";

export class ParseError extends Error {
  status: number;

  constructor(message: string, status = 400) {
    super(message);
    this.name = "ParseError";
    this.status = status;
  }
}

export function normalizeAweme(payload: unknown, platform: Extract<Platform, "douyin" | "tiktok">, pageUrl: string): ParsedPost {
  const data = asRecord(asRecord(payload)?.data);
  const aweme = asRecord(data?.aweme_detail) ?? asRecord(asArray(data?.aweme_details)[0]);
  if (!aweme) throw new ParseError("接口没有返回作品，链接可能失效了。");

  const caption = textOf(aweme.desc) ?? textOf(aweme.title) ?? "";
  const author = asRecord(aweme.author) ?? {};
  const stats = asRecord(aweme.statistics) ?? {};
  const likes = numberOf(stats.digg_count) ?? 0;
  const video = asRecord(aweme.video) ?? {};
  const slides = [
    ...asArray(aweme.images),
    ...asArray(asRecord(aweme.image_post_info)?.images),
  ];
  const cover = firstUrl(video.cover) ?? firstUrl(video.origin_cover) ?? firstUrl(video.dynamic_cover);
  const play = firstUrl(video.play_addr) ?? firstUrl(video.download_addr) ?? firstUrl(asArray(video.bit_rate)[0] && asRecord(asArray(video.bit_rate)[0])?.play_addr);
  const media: MediaItem[] = [];
  if (play) media.push({ kind: "video", url: play, cover, width: numberOf(video.width), height: numberOf(video.height) });
  for (const slide of slides) {
    const url = firstUrl(slide) ?? firstUrl(asRecord(slide)?.display_image);
    if (url) media.push({ kind: "image", url, cover: url });
  }
  if (!media.length && cover) media.push({ kind: "image", url: cover, cover });

  const music = asRecord(aweme.music);
  const duration = numberOf(video.duration);
  const followers = numberOf(author.follower_count);

  return {
    platform,
    source: "tikhub",
    via: "TikHub",
    url: textOf(aweme.share_url) ?? pageUrl,
    id: textOf(aweme.aweme_id),
    caption,
    author: {
      name: textOf(author.nickname) ?? "未知作者",
      handle: textOf(author.unique_id) || textOf(author.short_id),
      avatar: firstUrl(author.avatar_thumb) ?? firstUrl(author.avatar_medium),
      followers: followers && followers > 0 ? followers : undefined,
      bio: textOf(author.signature),
      url: authorUrl(platform, textOf(author.unique_id) || textOf(author.sec_uid)),
    },
    stats: {
      likes,
      comments: countOrMissing(stats.comment_count, likes),
      shares: countOrMissing(stats.share_count, likes),
      plays: countOrMissing(stats.play_count, likes, 1),
      collects: numberOf(stats.collect_count),
    },
    publishedAt: unixToIso(aweme.create_time),
    durationMs: duration && duration > 0 ? duration : undefined,
    hashtags: hashtagsFrom(caption, asArray(aweme.text_extra)),
    mentions: mentionsFrom(caption),
    media,
    music: music
      ? { title: textOf(music.title), author: textOf(music.author) || textOf(music.owner_nickname) }
      : undefined,
    form: play ? "video" : media.some((item) => item.kind === "image") ? "images" : "text",
    imageCount: media.filter((item) => item.kind === "image").length,
  };
}

function authorUrl(platform: Platform, handle?: string): string | undefined {
  if (!handle) return undefined;
  if (platform === "tiktok") return `https://www.tiktok.com/@${handle}`;
  if (platform === "douyin") return `https://www.douyin.com/user/${handle}`;
  return undefined;
}

export function extractXiaohongshuNote(payload: unknown): Record<string, unknown> | null {
  const data = asRecord(asRecord(payload)?.data) ?? asRecord(payload);
  const buckets = [
    ...asArray(data?.data),
    ...asArray(data?.note_list).map((note) => ({ note_list: [note] })),
  ];
  for (const bucket of buckets) {
    const record = asRecord(bucket);
    const note = asRecord(asArray(record?.note_list)[0]);
    if (note) return note;
  }
  if (data && (data.title || data.desc || data.text || data.id)) return data;
  return null;
}

export function xiaohongshuVideoId(payload: unknown): string | null {
  const note = extractXiaohongshuNote(payload);
  if (!note || note.model_type === "error") return null;
  const type = textOf(note.type) ?? textOf(note.note_type) ?? "";
  const play = xhsVideoUrl(note);
  if ((type === "video" || note.video) && !play) {
    return textOf(note.id) ?? textOf(note.note_id) ?? null;
  }
  return null;
}

export function normalizeXiaohongshu(payload: unknown, pageUrl: string): ParsedPost {
  const note = extractXiaohongshuNote(payload);
  if (!note) throw new ParseError("小红书没有返回笔记。");
  if (note.model_type === "error" || textOf(note.text) === "Note is not available") {
    throw new ParseError("这条小红书笔记不存在、已删除，或分享口令失效了。");
  }

  const caption = [textOf(note.title), textOf(note.desc) ?? textOf(note.text)].filter(Boolean).join("\n");
  const user = asRecord(note.user) ?? asRecord(note.user_info) ?? {};
  const likes = numberOf(note.liked_count) ?? numberOf(note.likes) ?? 0;
  const images = [...asArray(note.images_list), ...asArray(note.image_list)];
  const media: MediaItem[] = [];
  const videoUrl = xhsVideoUrl(note);
  const cover = firstUrl(note.cover) ?? firstUrl(images[0]) ?? (typeof note.image === "string" ? note.image : undefined);
  if (videoUrl) media.push({ kind: "video", url: videoUrl, cover });
  for (const image of images) {
    const url = firstUrl(image) ?? textOf(asRecord(image)?.url_size_large) ?? textOf(asRecord(image)?.original);
    if (url) media.push({ kind: "image", url, cover: url, width: numberOf(asRecord(image)?.width), height: numberOf(asRecord(image)?.height) });
  }
  if (!media.length && cover && /^https?:\/\//.test(cover)) media.push({ kind: "image", url: cover, cover });

  const type = textOf(note.type) ?? "";
  return {
    platform: "xiaohongshu",
    source: "tikhub",
    via: "TikHub",
    url: pageUrl,
    id: textOf(note.id) ?? textOf(note.note_id),
    title: textOf(note.title),
    caption,
    author: {
      name: textOf(user.nickname) ?? textOf(user.nick_name) ?? textOf(user.name) ?? "未知作者",
      handle: textOf(user.red_id) ?? textOf(user.userid) ?? textOf(user.user_id),
      avatar: firstUrl(user.image) ?? firstUrl(user.images) ?? firstUrl(user.avatar),
      bio: textOf(user.desc) ?? textOf(user.signature),
    },
    stats: {
      likes,
      comments: countOrMissing(note.comments_count ?? note.comment_count, likes),
      shares: countOrMissing(note.shared_count ?? note.share_count, likes),
      collects: numberOf(note.collected_count) ?? numberOf(note.collect_count),
      plays: countOrMissing(note.view_count, likes, 1),
    },
    publishedAt: unixToIso(note.time) ?? unixToIso(note.timestamp) ?? unixToIso(note.create_time),
    durationMs: xhsDuration(note),
    hashtags: hashtagsFrom(caption, asArray(note.hash_tag)),
    mentions: mentionsFrom(caption),
    media,
    form: videoUrl || type === "video" ? "video" : media.length ? "images" : "text",
    imageCount: media.filter((item) => item.kind === "image").length,
  };
}

function xhsVideoUrl(note: Record<string, unknown>): string | undefined {
  const video = asRecord(note.video) ?? asRecord(note.video_info);
  if (!video) return undefined;
  const stream = asRecord(asRecord(video.media)?.stream);
  const h264 = asArray(stream?.h264)[0] ?? asArray(stream?.h265)[0];
  return firstUrl(h264) ?? firstUrl(video.url) ?? firstUrl(video.play_addr) ?? firstUrl(video);
}

function xhsDuration(note: Record<string, unknown>): number | undefined {
  const video = asRecord(note.video) ?? {};
  const raw = numberOf(video.duration) ?? numberOf(note.duration);
  if (!raw || raw <= 0) return undefined;
  return raw > 1000 ? raw : raw * 1000;
}

export function normalizeInstagram(payload: unknown, pageUrl: string): ParsedPost {
  const data = asRecord(asRecord(payload)?.data) ?? asRecord(payload);
  const post =
    asRecord(asArray(data?.items)[0]) ??
    (data && (data.shortcode || data.edge_media_to_caption || data.like_count != null) ? data : null) ??
    asRecord(data?.data);
  if (!post) throw new ParseError("Instagram 没有返回帖子。");
  if (post.shortcode || post.edge_media_to_caption || post.__typename) return fromInstagramGraph(post, pageUrl);
  return fromInstagramModern(post, pageUrl);
}

function fromInstagramGraph(post: Record<string, unknown>, pageUrl: string): ParsedPost {
  const edges = asArray(asRecord(post.edge_media_to_caption)?.edges);
  const caption = textOf(asRecord(asRecord(edges[0])?.node)?.text) ?? "";
  const owner = asRecord(post.owner) ?? {};
  const likes = numberOf(asRecord(post.edge_media_preview_like)?.count) ?? numberOf(asRecord(post.edge_liked_by)?.count) ?? 0;
  const comments =
    numberOf(asRecord(post.edge_media_to_parent_comment)?.count) ??
    numberOf(asRecord(post.edge_media_to_comment)?.count);
  const sidecar = asArray(asRecord(post.edge_sidecar_to_children)?.edges);
  const media: MediaItem[] = [];
  const cover = textOf(post.display_url) ?? textOf(post.thumbnail_src);
  const videoUrl = textOf(post.video_url);
  if (post.is_video && videoUrl) media.push({ kind: "video", url: videoUrl, cover });
  for (const edge of sidecar) {
    const node = asRecord(asRecord(edge)?.node) ?? {};
    const url = textOf(node.display_url) ?? textOf(node.video_url);
    if (!url) continue;
    media.push(node.is_video ? { kind: "video", url: textOf(node.video_url) ?? url, cover: textOf(node.display_url) } : { kind: "image", url, cover: url });
  }
  if (!media.length && cover) media.push({ kind: post.is_video ? "video" : "image", url: videoUrl ?? cover, cover });
  const code = textOf(post.shortcode);
  const duration = numberOf(post.video_duration);
  return {
    platform: "instagram",
    source: "tikhub",
    via: "TikHub",
    url: code ? `https://www.instagram.com/p/${code}/` : pageUrl,
    id: textOf(post.id) ?? code,
    caption,
    author: {
      name: textOf(owner.full_name) || textOf(owner.username) || "未知作者",
      handle: textOf(owner.username),
      avatar: textOf(owner.profile_pic_url),
      followers: numberOf(asRecord(owner.edge_followed_by)?.count) || undefined,
      url: textOf(owner.username) ? `https://www.instagram.com/${textOf(owner.username)}/` : undefined,
    },
    stats: {
      likes,
      comments: countOrMissing(comments, likes),
      plays: countOrMissing(post.video_play_count ?? post.video_view_count, likes, 1),
    },
    publishedAt: unixToIso(post.taken_at_timestamp),
    durationMs: duration && duration > 0 ? duration * 1000 : undefined,
    hashtags: hashtagsFrom(caption),
    mentions: mentionsFrom(caption),
    media,
    form: post.is_video || media.some((item) => item.kind === "video") ? "video" : media.length ? "images" : "text",
    imageCount: Math.max(sidecar.length, media.filter((item) => item.kind === "image").length),
  };
}

function fromInstagramModern(post: Record<string, unknown>, pageUrl: string): ParsedPost {
  const captionRecord = asRecord(post.caption);
  const caption = textOf(captionRecord?.text) ?? textOf(post.caption_text) ?? textOf(post.caption) ?? "";
  const user = asRecord(post.user) ?? asRecord(post.owner) ?? {};
  const likes = numberOf(post.like_count) ?? 0;
  const versions = asArray(asRecord(post.image_versions2)?.candidates).concat(asArray(asRecord(post.image_versions)?.items));
  const videos = asArray(post.video_versions);
  const carousel = asArray(post.carousel_media);
  const media: MediaItem[] = [];
  const cover = firstUrl(versions[0]);
  const videoUrl = firstUrl(videos[0]);
  if (videoUrl) media.push({ kind: "video", url: videoUrl, cover });
  for (const item of carousel) {
    const record = asRecord(item) ?? {};
    const url = firstUrl(asArray(record.video_versions)[0]) ?? firstUrl(asArray(asRecord(record.image_versions2)?.candidates)[0]);
    if (url) media.push({ kind: asArray(record.video_versions).length ? "video" : "image", url, cover: url });
  }
  if (!media.length && cover) media.push({ kind: "image", url: cover, cover });
  const code = textOf(post.code) ?? textOf(post.shortcode);
  return {
    platform: "instagram",
    source: "tikhub",
    via: "TikHub",
    url: code ? `https://www.instagram.com/p/${code}/` : pageUrl,
    id: textOf(post.id) ?? code,
    caption,
    author: {
      name: textOf(user.full_name) || textOf(user.username) || "未知作者",
      handle: textOf(user.username),
      avatar: textOf(user.profile_pic_url) ?? firstUrl(user.profile_pic_url),
      url: textOf(user.username) ? `https://www.instagram.com/${textOf(user.username)}/` : undefined,
    },
    stats: {
      likes,
      comments: countOrMissing(post.comment_count, likes),
      plays: countOrMissing(post.play_count ?? post.view_count, likes, 1),
    },
    publishedAt: unixToIso(post.taken_at),
    hashtags: hashtagsFrom(caption),
    mentions: mentionsFrom(caption),
    media,
    form: media.some((item) => item.kind === "video") ? "video" : media.length ? "images" : "text",
    imageCount: media.filter((item) => item.kind === "image").length,
  };
}

export function normalizeYoutube(player: unknown, pageUrl: string, videoId: string): ParsedPost {
  const root = asRecord(player) ?? {};
  const details = asRecord(root.videoDetails);
  const micro = asRecord(asRecord(root.microformat)?.playerMicroformatRenderer) ?? {};
  const title = textOf(details?.title) ?? textOf(micro.title);
  if (!title) {
    const status = textOf(asRecord(root.playabilityStatus)?.reason) ?? "这个 YouTube 视频暂时读不到。";
    throw new ParseError(status);
  }
  const description = textOf(details?.shortDescription) ?? textOf(micro.description) ?? "";
  const thumbs = asArray(asRecord(micro.thumbnail)?.thumbnails);
  const cover = textOf(asRecord(thumbs.at(-1))?.url) ?? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
  const seconds = numberOf(details?.lengthSeconds) ?? numberOf(micro.lengthSeconds);
  const likes = numberOf(micro.likeCount);
  const views = numberOf(details?.viewCount) ?? numberOf(micro.viewCount);
  const channel = textOf(details?.author) ?? textOf(micro.ownerChannelName) ?? "未知频道";
  const channelUrl = textOf(micro.ownerProfileUrl);
  return {
    platform: "youtube",
    source: "public",
    via: "YouTube.js",
    url: textOf(micro.canonicalUrl) ?? pageUrl,
    id: videoId,
    title,
    caption: description,
    author: { name: channel, url: channelUrl },
    stats: { likes, plays: views },
    publishedAt: textOf(micro.publishDate) ?? textOf(micro.uploadDate),
    durationMs: seconds ? seconds * 1000 : undefined,
    hashtags: hashtagsFrom(`${title}\n${description}`),
    mentions: mentionsFrom(description),
    media: [{ kind: "embed", url: `https://www.youtube.com/embed/${videoId}`, cover }],
    form: "video",
    imageCount: 0,
  };
}

export function normalizeTweet(payload: unknown, pageUrl: string): ParsedPost {
  const root = asRecord(payload) ?? {};
  const tweet = asRecord(root.tweet) ?? asRecord(root.data) ?? root;
  const text = textOf(tweet.raw_text) ?? textOf(tweet.text) ?? textOf(tweet.full_text);
  if (!text && !tweet.id) throw new ParseError("这条帖子读不到，可能已删除或账号受限。");
  const author = asRecord(tweet.author) ?? asRecord(tweet.user) ?? {};
  const legacy = asRecord(tweet.legacy);
  const caption = text ?? textOf(legacy?.full_text) ?? "";
  const handle = textOf(author.screen_name) ?? textOf(author.username);
  const media = tweetMedia(tweet);
  const likes = numberOf(tweet.likes) ?? numberOf(tweet.favorite_count) ?? numberOf(legacy?.favorite_count);
  return {
    platform: "x",
    source: "public",
    via: "FxEmbed",
    url: textOf(tweet.url) ?? pageUrl,
    id: textOf(tweet.id) ?? textOf(tweet.id_str),
    caption,
    author: {
      name: textOf(author.name) ?? handle ?? "未知作者",
      handle,
      avatar: textOf(author.avatar_url) ?? textOf(author.profile_image_url_https),
      followers: numberOf(author.followers) ?? numberOf(author.followers_count),
      bio: textOf(author.description) ?? textOf(author.raw_description),
      url: handle ? `https://x.com/${handle}` : undefined,
    },
    stats: {
      likes,
      comments: numberOf(tweet.replies) ?? numberOf(legacy?.reply_count),
      shares: numberOf(tweet.retweets) ?? numberOf(legacy?.retweet_count),
      plays: numberOf(tweet.views) && numberOf(tweet.views)! > 0 ? numberOf(tweet.views) : undefined,
      bookmarks: numberOf(tweet.bookmarks) ?? numberOf(legacy?.bookmark_count),
    },
    publishedAt: unixToIso(tweet.created_timestamp) ?? (textOf(tweet.created_at) ? safeDate(textOf(tweet.created_at)!) : undefined),
    durationMs: tweetDurationMs(tweet),
    hashtags: hashtagsFrom(caption),
    mentions: mentionsFrom(caption),
    media,
    form: media.some((item) => item.kind === "video") ? "video" : media.length ? "images" : "text",
    imageCount: media.filter((item) => item.kind === "image").length,
  };
}

function tweetDurationMs(tweet: Record<string, unknown>): number | undefined {
  const video = asRecord(asArray(asRecord(tweet.media)?.videos)[0]);
  const seconds = numberOf(video?.duration);
  if (!seconds || seconds <= 0) return undefined;
  return Math.round(seconds * 1000);
}

function safeDate(value: string): string | undefined {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

function tweetMedia(tweet: Record<string, unknown>): MediaItem[] {
  const media = asRecord(tweet.media);
  const items: MediaItem[] = [];
  for (const video of asArray(media?.videos)) {
    const record = asRecord(video) ?? {};
    const url = textOf(record.url);
    if (url) items.push({ kind: "video", url, cover: textOf(record.thumbnail_url) });
  }
  for (const photo of asArray(media?.photos)) {
    const record = asRecord(photo) ?? {};
    const url = textOf(record.url);
    if (url) items.push({ kind: "image", url, cover: url });
  }
  return items;
}
