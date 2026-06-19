/** Legacy inspector API types (matches fetch_result_dict). */

export interface CommentUser {
  uid: string;
  nickname: string | null;
  unique_id: string | null;
}

export interface ParsedComment {
  comment_id: string;
  post_id: string;
  text: string | null;
  create_time: number | null;
  comment_language: string | null;
  digg_count: number | null;
  is_author_digged: boolean;
  reply_comment_total: number | null;
  is_reply: boolean;
  parent_comment_id: string | null;
  user: CommentUser;
}

export interface CommentStats {
  total: number;
  metric: number | null;
  author_comments: number;
  audience: number;
}

export interface ParsedAuthor {
  tiktok_id: string;
  unique_id: string;
  nickname: string | null;
  avatar_larger: string | null;
  verified: boolean;
  follower_count: number | null;
  following_count: number | null;
  heart: number | null;
  heart_count: number | null;
  video_count: number | null;
}

export interface PostMetrics {
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  saves: number | null;
}

export interface ParsedHashtag {
  name: string;
}

export interface ParsedMusic {
  title: string;
  author_name: string;
  duration: number;
  cover_large: string;
  play_url: string;
  original: boolean;
}

export interface ParsedMedia {
  video_cover: string | null;
  photo_urls: string[];
}

export interface ParsedItem {
  post_id: string;
  content_type: string;
  description_preview: string | null;
  description: string | null;
  description_length: number | null;
  description_keywords: string[] | null;
  location_created: string | null;
  diversification_labels: string[];
  metrics: PostMetrics;
  author: ParsedAuthor;
  hashtags: ParsedHashtag[];
  music: ParsedMusic | null;
  media: ParsedMedia | null;
}

export interface InspectResult {
  platform: string;
  url: string;
  item: ParsedItem;
  comments: ParsedComment[];
  comment_stats: CommentStats;
}

export interface CommentThread extends ParsedComment {
  replies: CommentThread[];
  searchExpand?: boolean;
}

export interface PlatformInfo {
  id: string;
  name: string;
  available: boolean;
}

export const PLATFORM_HOSTS: Record<string, string[]> = {
  tiktok: ["tiktok.com", "vt.tiktok.com", "vm.tiktok.com"],
  threads: ["threads.net", "threads.com"],
};

export const COMMENTS_PREVIEW = 15;
export const COMMENTS_STEP = 20;
export const REPLIES_PREVIEW = 2;
