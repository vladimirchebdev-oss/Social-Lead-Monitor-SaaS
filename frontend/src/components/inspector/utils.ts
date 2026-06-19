import type { CommentThread, ParsedComment } from "./types";

export function formatNumber(value: number | string | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 10_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString("ru-RU");
}

export function formatDate(unixSeconds: number | null): string {
  if (!unixSeconds) return "";
  return new Date(unixSeconds * 1000).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatRelativeTime(unixSeconds: number | null): string {
  if (!unixSeconds) return "";
  const diff = Date.now() / 1000 - unixSeconds;
  if (diff < 45) return "только что";
  if (diff < 3600) return `${Math.floor(diff / 60)} мин`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} д`;
  if (diff < 2592000) return `${Math.floor(diff / 604800)} нед`;
  return formatDate(unixSeconds);
}

export function commentInitials(c: ParsedComment): string {
  const name = c.user.nickname || c.user.unique_id || "?";
  return name.trim()[0]?.toUpperCase() || "?";
}

export function buildCommentTree(comments: ParsedComment[]): CommentThread[] {
  const nodes = new Map<string, CommentThread>();
  for (const c of comments) {
    nodes.set(c.comment_id, { ...c, replies: [] });
  }

  const childIds = new Set<string>();
  for (const c of comments) {
    const parentId = c.parent_comment_id;
    if (c.is_reply && parentId && parentId !== "0" && nodes.has(parentId)) {
      nodes.get(parentId)!.replies.push(nodes.get(c.comment_id)!);
      childIds.add(c.comment_id);
    }
  }

  const roots: CommentThread[] = [];
  for (const c of comments) {
    if (!childIds.has(c.comment_id)) {
      roots.push(nodes.get(c.comment_id)!);
    }
  }
  return roots;
}

function normalizeSearchText(value: string | null | undefined): string {
  return String(value ?? "")
    .normalize("NFC")
    .toLocaleLowerCase("ru");
}

function commentMatchesSearch(comment: ParsedComment, query: string): boolean {
  const q = normalizeSearchText(query.trim());
  if (!q) return true;
  return [comment.text, comment.user?.nickname, comment.user?.unique_id].some((part) =>
    normalizeSearchText(part).includes(q),
  );
}

export function prepareThreadsForSearch(
  threads: CommentThread[],
  query: string,
): { threads: CommentThread[]; searching: boolean } {
  const q = query.trim();
  if (!q) return { threads, searching: false };

  const filtered: CommentThread[] = [];
  for (const thread of threads) {
    const parentMatch = commentMatchesSearch(thread, q);
    const matchingReplies = (thread.replies || []).filter((reply) =>
      commentMatchesSearch(reply, q),
    );

    if (parentMatch) {
      filtered.push({ ...thread, replies: thread.replies || [], searchExpand: true });
    } else if (matchingReplies.length) {
      filtered.push({ ...thread, replies: matchingReplies, searchExpand: true });
    }
  }
  return { threads: filtered, searching: true };
}

export function pluralReplies(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "ответ";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "ответа";
  return "ответов";
}

export function truncateUrl(url: string, maxLen = 52): string {
  if (url.length <= maxLen) return url;
  return `${url.slice(0, maxLen - 1)}…`;
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function detectPlatformFromUrl(
  url: string,
  platforms: { id: string; name: string; available: boolean }[],
  hosts: Record<string, string[]>,
): { id: string; name: string; available: boolean } | null {
  const trimmed = url.trim();
  if (!trimmed) return null;
  try {
    const host = new URL(trimmed).hostname.toLowerCase().replace(/^www\./, "");
    return (
      platforms.find((p) =>
        (hosts[p.id] || []).some((pattern) => host === pattern || host.endsWith(`.${pattern}`)),
      ) ?? null
    );
  } catch {
    return null;
  }
}
