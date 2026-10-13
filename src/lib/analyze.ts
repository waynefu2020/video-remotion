import { clip, formatCount, formatDuration, formatRelative } from "@/lib/format";
import { PLATFORM_LABEL, type Analysis, type ParsedPost } from "@/lib/types";

export function analyzePost(post: ParsedPost): Analysis {
  const bare = post.caption.replace(/#[^\s#]+/g, " ").replace(/\s+/g, " ").trim();
  const hook = (bare.split(/\n|。|！|!|？|\?/)[0] ?? "").trim();
  const hookKind = classifyHook(post.caption, hook);
  const formLabel = describeForm(post);
  const notes = buildNotes(post, hookKind);
  const when = formatRelative(post.publishedAt);
  const stat = leadStat(post);
  const tags = post.hashtags.slice(0, 3).map((tag) => `#${tag}`).join(" ");
  const opening =
    hookKind === "只靠标签"
      ? `正文只挂了话题${tags ? ` ${tags}` : ""}`
      : hook
        ? `开头是「${clip(hook, 32)}」`
        : "没有留下正文";
  const summary = `${post.author.name} 在${PLATFORM_LABEL[post.platform]}发了一条${formLabel}${when ? `，${when}` : ""}，${opening}。${stat}`;

  return {
    summary,
    hook: hook || post.title || "",
    hookKind,
    formLabel,
    captionChars: [...post.caption].length,
    notes,
  };
}

function describeForm(post: ParsedPost): string {
  if (post.form === "video") {
    return post.durationMs ? `${formatDuration(post.durationMs)}视频` : "视频";
  }
  if (post.form === "images") {
    const count = post.imageCount || post.media.length;
    return count > 1 ? `${count} 张图` : "单图";
  }
  return "纯文字";
}

function classifyHook(caption: string, hook: string): string {
  if (!caption.trim()) return "没有正文";
  if (!hook) return "只靠标签";
  if (/[?？]/.test(hook) || /吗$/.test(hook)) return "提问";
  if (/^\d+/.test(hook)) return "数字开头";
  if (/^(你|我|咱|家人们|兄弟|姐妹|宝子|朋友们)/.test(hook)) return "对白";
  if ([...hook].length <= 12) return "短句";
  return "陈述";
}

function buildNotes(post: ParsedPost, hookKind: string): string[] {
  const notes: string[] = [];
  notes.push(hookNote(hookKind, post));
  if (post.transcript) {
    const spoken = post.transcript.split(/(?<=[。！？.!?])/)[0]?.trim();
    if (spoken) notes.push(`口播开头是「${clip(spoken, 42)}」。字幕和文案不是同一件事，画面跟着哪一句走，这里能看出来。`);
  }

  if (post.durationMs) {
    const seconds = Math.round(post.durationMs / 1000);
    if (seconds <= 15) notes.push(`成片 ${seconds} 秒。这个时长容不下铺垫，主题得在开头两秒里出现。`);
    else if (seconds <= 45) notes.push(`成片 ${seconds} 秒，够放一个主张和一段证明，中间再切一次就会散。`);
    else if (seconds <= 180) notes.push(`成片 ${formatDuration(post.durationMs)}，已经要靠段落，而不是靠一句钩子撑完全片。`);
    else notes.push(`成片 ${formatDuration(post.durationMs)}，按中长视频来读：封面和标题负责点开，正文负责留下来。`);
  }

  if (post.form === "images" && post.imageCount > 1) {
    notes.push(`图集共 ${post.imageCount} 张。小红书和 Instagram 上，第一张决定划走还是点开，后面的张数决定有没有被收藏。`);
  }

  if (post.hashtags.length) {
    const shown = post.hashtags.slice(0, 6).map((tag) => `#${tag}`).join(" ");
    const more = post.hashtags.length > 6 ? `，一共 ${post.hashtags.length} 个` : "";
    notes.push(`话题写在正文里：${shown}${more}。`);
  } else if (post.caption.trim()) {
    notes.push("正文没有话题标签，曝光更多靠推荐，而不是靠话题页。");
  }

  const { likes, comments, plays, collects, shares } = post.stats;
  if (plays && likes != null && plays > 0) {
    const rate = (likes / plays) * 100;
    const read =
      rate >= 8 ? "点赞相对密，看完的人愿意动手。" : rate < 2 ? "播放铺得开，但点赞跟得少。" : "赞播比落在常见区间。";
    notes.push(`赞播比 ${rate.toFixed(rate >= 10 ? 1 : 2)}%。${read}`);
  }
  if (likes && comments != null && likes > 0) {
    const rate = (comments / likes) * 100;
    const read = rate >= 5 ? "评论被带起来了，正文里很可能有提问或站队。" : "评论明显少于点赞，观众更多是看过，而不是接话。";
    notes.push(`每 100 个赞大约有 ${rate.toFixed(1)} 条评论。${read}`);
  }
  if (post.platform === "xiaohongshu" && likes && collects != null) {
    const rate = collects / likes;
    notes.push(
      rate >= 0.45
        ? `收藏是点赞的 ${rate.toFixed(2)} 倍关系（${formatCount(collects)} 收藏 / ${formatCount(likes)} 赞）。这条更像会被存下来的攻略。`
        : `收藏 ${formatCount(collects)}，点赞 ${formatCount(likes)}。收藏跟不上点赞时，态度多于可复用的信息。`,
    );
  }
  if (shares != null && likes && likes > 0) {
    const rate = (shares / likes) * 100;
    if (rate >= 8) notes.push(`分享是点赞的 ${rate.toFixed(1)}%。有人愿意把它转出去，而不只是自己点一下。`);
  }

  if (post.music?.title && post.form === "video") {
    const by = post.music.author ? `，${post.music.author}` : "";
    notes.push(`配乐是「${post.music.title}」${by}。声音如果占了前两秒，钩子就不只在字幕里。`);
  }

  return notes.slice(0, 6);
}

function hookNote(kind: string, post: ParsedPost): string {
  const chars = [...post.caption].length;
  switch (kind) {
    case "没有正文":
      return "这条几乎没有文案，封面、字幕和前两秒的画面就是全部信息。";
    case "只靠标签":
      return "正文只剩话题标签，搜索入口有了，句子本身没有主张。";
    case "提问":
      return `开头用提问把人留住，全文 ${chars} 字。问题如果在第一句就闭合，后面要马上给答案。`;
    case "数字开头":
      return `开头用数字立住预期，全文 ${chars} 字。数字后面最好是同一套单位，不然承诺会空。`;
    case "对白":
      return `开头是对着人说话，全文 ${chars} 字。这种句子靠口气，不靠信息量。`;
    case "短句":
      return `开头只有一句短话，全文 ${chars} 字。短句适合当标题，解释得放到画面或后文里。`;
    default:
      return `开头是一句陈述，全文 ${chars} 字。陈述句要自己带结论，不能等观众读完才知道在说什么。`;
  }
}

function leadStat(post: ParsedPost): string {
  const bits: string[] = [];
  const { likes, plays, collects, comments } = post.stats;
  if (plays != null) bits.push(`${formatCount(plays)} 次播放`);
  if (likes != null) bits.push(`${formatCount(likes)} 个赞`);
  if (collects != null && post.platform === "xiaohongshu") bits.push(`${formatCount(collects)} 次收藏`);
  if (!bits.length && comments != null) bits.push(`${formatCount(comments)} 条评论`);
  if (!bits.length) return "互动数字这次没有返回。";
  return `眼下能看到的是${bits.slice(0, 3).join("、")}。`;
}
