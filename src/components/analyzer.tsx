"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { detectLink } from "@/lib/detect";
import { clip, formatAbsolute, formatCount, formatDuration, formatRelative } from "@/lib/format";
import { PLATFORM_LABEL, type Analysis, type ParsedPost, type Platform } from "@/lib/types";

type StatusItem = { id: Platform; label: string; via: string; ready: boolean };
type HistoryItem = { url: string; platform: Platform; title: string; author: string; at: string };

const HISTORY_KEY = "jingxi-history";
const STAT_LABELS: Array<{ key: keyof ParsedPost["stats"]; label: string }> = [
  { key: "plays", label: "播放" },
  { key: "likes", label: "赞" },
  { key: "comments", label: "评论" },
  { key: "shares", label: "分享" },
  { key: "collects", label: "收藏" },
  { key: "bookmarks", label: "书签" },
];

export function Analyzer() {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<StatusItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [post, setPost] = useState<ParsedPost | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [raw, setRaw] = useState<unknown>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    void fetch("/api/status")
      .then((response) => response.json())
      .then((body: { platforms?: StatusItem[] }) => setStatus(body.platforms ?? []))
      .catch(() => setStatus([]));
    try {
      const stored = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]") as HistoryItem[];
      if (Array.isArray(stored)) setHistory(stored.slice(0, 8));
    } catch {
      setHistory([]);
    }
  }, []);

  const detected = detectLink(text);

  async function submit(value = text) {
    const next = value.trim();
    if (!next || loading) return;
    setText(next);
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: next }),
      });
      const body = (await response.json()) as {
        error?: string;
        post?: ParsedPost;
        analysis?: Analysis;
        raw?: unknown;
      };
      if (!response.ok || !body.post || !body.analysis) {
        setPost(null);
        setAnalysis(null);
        setRaw(null);
        setError(body.error || "没有拆开。");
        return;
      }
      setPost(body.post);
      setAnalysis(body.analysis);
      setRaw(body.raw ?? null);
      const item: HistoryItem = {
        url: next,
        platform: body.post.platform,
        title: clip(body.post.title || body.post.caption || "无标题", 42),
        author: body.post.author.name,
        at: new Date().toISOString(),
      };
      const nextHistory = [item, ...history.filter((entry) => entry.url !== item.url)].slice(0, 8);
      setHistory(nextHistory);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory));
    } catch {
      setError("网络中断了，再试一次。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-8 px-4 py-8 md:px-8 md:py-12">
      <header className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <span className="inline-block h-8 w-1.5 rounded-full bg-primary" />
          <p className="font-heading text-3xl tracking-tight text-foreground md:text-4xl">镜析</p>
        </div>
        <div className="max-w-2xl space-y-2">
          <h1 className="text-lg font-medium">公开视频拆片台</h1>
          <p className="text-sm leading-6 text-muted-foreground">
            贴一条链接，或整段分享文案。抖音、小红书、TikTok、Instagram 走 TikHub；YouTube 用 YouTube.js；X 用 FxEmbed，不够时改走 syndication。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {status.length === 0
            ? Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-6 w-28" />)
            : status.map((item) => (
                <Badge key={item.id} variant={item.ready ? "secondary" : "outline"}>
                  {item.label} · {item.via}
                </Badge>
              ))}
        </div>
      </header>

      <Card className="gap-4 p-4 md:p-5">
        <Textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              event.preventDefault();
              void submit();
            }
          }}
          placeholder="粘贴 v.douyin.com、xhslink、tiktok.com、instagram.com/reel、youtu.be 或 x.com/status 链接。分享文案里夹着短链也可以。"
          className="min-h-32 bg-background/70 text-base"
        />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted-foreground">
            {detected ? `认出来了：${detected.label}` : "还没认出平台"}
            {loading ? "，正在取这条内容" : ""}
          </p>
          <Button type="button" size="lg" className="h-11 px-5" disabled={loading || !text.trim()} onClick={() => void submit()}>
            {loading ? "正在拆…" : "拆开这条"}
          </Button>
        </div>
      </Card>

      {error ? (
        <Card className="border-destructive/30 p-5">
          <p className="font-medium text-destructive">没拆开</p>
          <p className="mt-2 text-sm leading-6">{error}</p>
        </Card>
      ) : null}

      {loading ? <LoadingDesk /> : null}

      {!loading && !post && !error ? <EmptyDesk /> : null}

      {post && analysis ? <Result post={post} analysis={analysis} raw={raw} /> : null}

      <section className="space-y-3">
        <h2 className="font-heading text-xl">这台浏览器里拆过的</h2>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground">拆过的链接会留在本地，不会上传到别的地方。</p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {history.map((item) => (
              <li key={`${item.at}-${item.url}`}>
                <button
                  type="button"
                  onClick={() => void submit(item.url)}
                  className="flex w-full flex-col items-start gap-1 rounded-xl bg-card px-3 py-3 text-left ring-1 ring-foreground/10 hover:bg-accent"
                >
                  <span className="text-xs text-muted-foreground">
                    {PLATFORM_LABEL[item.platform]} · {item.author}
                  </span>
                  <span className="text-sm">{item.title}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function EmptyDesk() {
  return (
    <Card className="gap-3 p-5">
      <p className="font-heading text-xl">台面是空的</p>
      <p className="max-w-xl text-sm leading-6 text-muted-foreground">
        拆开之后，这里会放下作者、正文、互动，以及一份读片笔记：开头是什么句式、时长够不够、赞和播放是不是配得上。
      </p>
      <ul className="grid gap-2 text-sm text-muted-foreground md:grid-cols-3">
        <li className="rounded-lg bg-background/70 px-3 py-2">分享文案里夹着短链也能认出来。</li>
        <li className="rounded-lg bg-background/70 px-3 py-2">图文和视频分开读，小红书视频会再要一次播放地址。</li>
        <li className="rounded-lg bg-background/70 px-3 py-2">YouTube 会尽量带上字幕，X 会带上浏览和媒体。</li>
      </ul>
    </Card>
  );
}

function LoadingDesk() {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <Skeleton className="h-80 rounded-xl" />
      <div className="space-y-3">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-24" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}

function Result({ post, analysis, raw }: { post: ParsedPost; analysis: Analysis; raw: unknown }) {
  const when = [formatRelative(post.publishedAt), formatAbsolute(post.publishedAt)].filter(Boolean).join(" · ");
  const stats = STAT_LABELS.flatMap((item) => {
    const value = post.stats[item.key];
    return value == null ? [] : [{ label: item.label, value }];
  });

  async function copyCaption() {
    const payload = [post.title, post.caption].filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(payload);
      toast.success("正文已复制");
    } catch {
      toast.error("这台浏览器没有给剪贴板权限");
    }
  }

  return (
    <section className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <Card className="gap-0 overflow-hidden p-0">
        <Media post={post} />
        <div className="space-y-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{PLATFORM_LABEL[post.platform]}</Badge>
            <Badge variant="outline">{post.via}</Badge>
            <Badge variant="secondary">{analysis.formLabel}</Badge>
          </div>
          <p className="font-heading text-2xl leading-snug">{post.title || clip(post.caption, 48) || "这条没有标题"}</p>
          <div className="flex items-center gap-3">
            {post.author.avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={post.author.avatar} alt="" className="size-10 rounded-full object-cover" />
            ) : (
              <span className="flex size-10 items-center justify-center rounded-full bg-accent text-sm">{post.author.name.slice(0, 1)}</span>
            )}
            <div>
              <p className="font-medium">{post.author.name}</p>
              <p className="text-xs text-muted-foreground">
                {post.author.handle ? `@${post.author.handle}` : "没有账号名"}
                {post.author.followers ? ` · ${formatCount(post.author.followers)} 关注者` : ""}
                {post.author.bio && !post.author.followers ? ` · ${post.author.bio}` : ""}
              </p>
            </div>
          </div>
          {when ? <p className="text-xs text-muted-foreground">{when}</p> : null}
        </div>
      </Card>

      <Card className="p-4 md:p-5">
        <Tabs defaultValue="read">
          <TabsList>
            <TabsTrigger value="read">读片</TabsTrigger>
            <TabsTrigger value="copy">正文</TabsTrigger>
            <TabsTrigger value="spoken">口播</TabsTrigger>
            <TabsTrigger value="raw">原始</TabsTrigger>
          </TabsList>
          <TabsContent value="read" className="space-y-4 pt-4">
            <p className="text-base leading-7">{analysis.summary}</p>
            {stats.length ? (
              <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {stats.map((item) => (
                  <div key={item.label} className="rounded-lg bg-background/80 px-3 py-2">
                    <dt className="text-xs text-muted-foreground">{item.label}</dt>
                    <dd className="font-heading text-2xl">{formatCount(item.value)}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">这次没有返回互动数字。</p>
            )}
            <Separator />
            <ul className="space-y-3 text-sm leading-6">
              {analysis.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">
              开头句式：{analysis.hookKind}
              {post.durationMs ? ` · 时长 ${formatDuration(post.durationMs)}` : ""}
              {` · 正文 ${analysis.captionChars} 字`}
            </p>
          </TabsContent>
          <TabsContent value="copy" className="space-y-3 pt-4">
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={() => void copyCaption()}>
                复制正文
              </Button>
              <a className={buttonVariants({ variant: "outline" })} href={post.url} target="_blank" rel="noreferrer">
                打开原链接
              </a>
            </div>
            {post.author.bio ? <p className="text-sm text-muted-foreground">{post.author.bio}</p> : null}
            <p className="whitespace-pre-wrap text-sm leading-7">{post.caption || "这条没有正文。"}</p>
            {post.music?.title ? (
              <p className="text-sm text-muted-foreground">
                配乐：{post.music.title}
                {post.music.author ? ` · ${post.music.author}` : ""}
              </p>
            ) : null}
            {post.hashtags.length ? (
              <p className="text-sm text-muted-foreground">{post.hashtags.map((tag) => `#${tag}`).join(" ")}</p>
            ) : null}
          </TabsContent>
          <TabsContent value="spoken" className="pt-4">
            {post.transcript ? (
              <p className="whitespace-pre-wrap text-sm leading-7">{post.transcript}</p>
            ) : (
              <p className="text-sm leading-6 text-muted-foreground">这条没有拿到字幕。短视频平台通常不给口播文本，YouTube 有字幕时会显示在这里。</p>
            )}
          </TabsContent>
          <TabsContent value="raw" className="pt-4">
            <pre className="max-h-[28rem] overflow-auto rounded-lg bg-background/80 p-3 text-xs leading-5">{JSON.stringify(raw, null, 2)}</pre>
          </TabsContent>
        </Tabs>
      </Card>
    </section>
  );
}

function Media({ post }: { post: ParsedPost }) {
  const first = post.media[0];
  if (!first) {
    return <div className="flex h-56 items-center justify-center bg-accent text-sm text-muted-foreground">没有封面</div>;
  }
  if (first.kind === "embed") {
    return (
      <div className="aspect-video bg-black">
        <iframe title={post.title || "视频"} src={first.url} className="h-full w-full" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
      </div>
    );
  }
  if (first.kind === "video") {
    return (
      <video className="aspect-video w-full bg-black" controls poster={first.cover} playsInline preload="metadata">
        <source src={first.url} />
      </video>
    );
  }
  const images = post.media.filter((item) => item.kind === "image");
  return (
    <div className={images.length > 1 ? "grid grid-cols-2" : ""}>
      {images.slice(0, 4).map((item) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={item.url} src={item.url} alt="" className="aspect-square w-full object-cover" />
      ))}
    </div>
  );
}
