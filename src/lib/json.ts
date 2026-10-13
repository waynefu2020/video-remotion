export function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function textOf(value: unknown): string | undefined {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || undefined;
  }
  return undefined;
}

export function numberOf(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) {
    return Number(value);
  }
  return undefined;
}

export function firstUrl(value: unknown): string | undefined {
  if (typeof value === "string" && /^https?:\/\//i.test(value)) return value;
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = firstUrl(item);
      if (found) return found;
    }
    return undefined;
  }
  const record = asRecord(value);
  if (!record) return undefined;
  const list = asArray(record.url_list).find((item) => typeof item === "string" && /^https?:\/\//.test(item));
  if (typeof list === "string") return list;
  for (const key of ["url", "url_default", "master_url", "play_url", "download_url", "src", "uri"]) {
    const candidate = record[key];
    if (typeof candidate === "string" && /^https?:\/\//i.test(candidate)) return candidate;
  }
  return undefined;
}

export function unixToIso(value: unknown): string | undefined {
  const n = numberOf(value);
  if (!n || n <= 0) return undefined;
  const ms = n > 10_000_000_000 ? n : n * 1000;
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toISOString();
}

export function hashtagsFrom(text: string, extra: unknown[] = []): string[] {
  const found = new Set<string>();
  for (const item of extra) {
    const name = textOf(asRecord(item)?.hashtag_name) ?? textOf(asRecord(item)?.name);
    if (name) found.add(name.replace(/^#/, ""));
  }
  for (const match of text.matchAll(/#([^\s#@]+)/g)) {
    found.add(match[1]);
  }
  return [...found];
}

export function mentionsFrom(text: string): string[] {
  return [...new Set([...text.matchAll(/@([^\s#@]+)/g)].map((match) => match[1]))];
}

/** A zero next to a lively count is usually a field the API left blank. */
export function countOrMissing(value: unknown, likes: number, threshold = 100): number | undefined {
  const n = numberOf(value);
  if (n == null) return undefined;
  if (n === 0 && likes > threshold) return undefined;
  return n;
}
