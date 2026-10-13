export const PLATFORMS = [
  "douyin",
  "xiaohongshu",
  "tiktok",
  "instagram",
  "youtube",
  "x",
] as const;

export type Platform = (typeof PLATFORMS)[number];

export const PLATFORM_LABEL: Record<Platform, string> = {
  douyin: "抖音",
  xiaohongshu: "小红书",
  tiktok: "TikTok",
  instagram: "Instagram",
  youtube: "YouTube",
  x: "X",
};

export type MediaKind = "video" | "image" | "embed";

export type MediaItem = {
  kind: MediaKind;
  url: string;
  cover?: string;
  width?: number;
  height?: number;
};

export type PostStats = {
  likes?: number;
  comments?: number;
  shares?: number;
  plays?: number;
  collects?: number;
  bookmarks?: number;
};

export type ParsedPost = {
  platform: Platform;
  source: "tikhub" | "public";
  via: string;
  url: string;
  id?: string;
  title?: string;
  caption: string;
  author: {
    name: string;
    handle?: string;
    avatar?: string;
    followers?: number;
    bio?: string;
    url?: string;
  };
  stats: PostStats;
  publishedAt?: string;
  durationMs?: number;
  hashtags: string[];
  mentions: string[];
  media: MediaItem[];
  music?: { title?: string; author?: string };
  form: "video" | "images" | "text";
  imageCount: number;
  transcript?: string;
};

export type Analysis = {
  summary: string;
  hook: string;
  hookKind: string;
  formLabel: string;
  captionChars: number;
  notes: string[];
};

export type ParsePayload = {
  post: ParsedPost;
  analysis: Analysis;
  warning?: string;
  raw: unknown;
};
