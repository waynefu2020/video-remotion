export function formatCount(value: number): string {
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 100_000_000) {
    const n = abs / 100_000_000;
    return `${sign}${trimNumber(n, n >= 10 ? 0 : 1)}亿`;
  }
  if (abs >= 10_000) {
    const n = abs / 10_000;
    return `${sign}${trimNumber(n, n >= 100 ? 0 : 1)}万`;
  }
  return `${sign}${new Intl.NumberFormat("zh-CN").format(abs)}`;
}

function trimNumber(value: number, digits: number): string {
  return value.toFixed(digits).replace(/\.0$/, "");
}

export function formatDuration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (hours > 0) return `${hours}小时${minutes}分`;
  if (minutes === 0) return `${seconds}秒`;
  return `${minutes}分${seconds.toString().padStart(2, "0")}秒`;
}

export function formatAbsolute(iso?: string): string | undefined {
  if (!iso) return undefined;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return undefined;
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatRelative(iso?: string): string | undefined {
  if (!iso) return undefined;
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return undefined;
  const minutes = Math.round((Date.now() - time) / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} 天前`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months} 个月前`;
  return `${Math.round(days / 365)} 年前`;
}

export function clip(text: string, max: number): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max).trim()}…`;
}
