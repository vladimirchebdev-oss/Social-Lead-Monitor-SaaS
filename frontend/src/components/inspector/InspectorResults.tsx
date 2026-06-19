import { useCallback, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import type { CommentStats, CommentThread, InspectResult, ParsedComment, ParsedItem } from "./types";
import {
  COMMENTS_PREVIEW,
  COMMENTS_STEP,
  REPLIES_PREVIEW,
} from "./types";
import {
  buildCommentTree,
  commentInitials,
  copyToClipboard,
  formatNumber,
  formatRelativeTime,
  pluralReplies,
  prepareThreadsForSearch,
  truncateUrl,
} from "./utils";

function UrlRow({ label, url }: { label: string; url: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    const ok = await copyToClipboard(url);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    }
  };

  return (
    <div className="url-row">
      <span className="url-row__label">{label}</span>
      <a
        className="url-row__link"
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        title={url}
      >
        {truncateUrl(url)}
      </a>
      <button
        type="button"
        className={`url-row__copy${copied ? " url-row__copy--done" : ""}`}
        onClick={onCopy}
        title="Копировать ссылку"
      >
        {copied ? "Скопировано" : "Копировать"}
      </button>
    </div>
  );
}

function MediaSection({ item, postUrl }: { item: ParsedItem; postUrl: string }) {
  const media = item.media;
  const rows: { label: string; url: string }[] = [{ label: "Пост", url: postUrl }];

  if (media?.video_cover) rows.push({ label: "Обложка видео", url: media.video_cover });
  media?.photo_urls?.forEach((url, index) => {
    rows.push({ label: `Фото ${index + 1}`, url });
  });

  const thumbs: { label: string; url: string }[] = [];
  if (media?.video_cover) thumbs.push({ label: "Обложка видео", url: media.video_cover });
  media?.photo_urls?.forEach((url, index) => {
    thumbs.push({ label: `Фото ${index + 1}`, url });
  });

  return (
    <article className="card">
      <h3 className="card__title">Медиа и ссылки</h3>
      {thumbs.length > 0 && (
        <div className="media-thumbs">
          {thumbs.map((t) => (
            <figure key={t.url} className="media-thumb">
              <a href={t.url} target="_blank" rel="noopener noreferrer" className="media-thumb__link">
                <img className="media-thumb__img" src={t.url} alt={t.label} loading="lazy" />
              </a>
              <figcaption className="media-thumb__caption">{t.label}</figcaption>
            </figure>
          ))}
        </div>
      )}
      <div className="url-list">
        {rows.map((r) => (
          <UrlRow key={r.label + r.url} label={r.label} url={r.url} />
        ))}
      </div>
    </article>
  );
}

function AuthorCard({ author }: { author: ParsedItem["author"] }) {
  const initial = (author.nickname || author.unique_id || "?")[0]?.toUpperCase() || "?";

  return (
    <article className="card">
      <h3 className="card__title">Автор</h3>
      <div className="author">
        {author.avatar_larger ? (
          <img className="author__avatar" src={author.avatar_larger} alt="" loading="lazy" />
        ) : (
          <div className="author__avatar author__avatar--placeholder">{initial}</div>
        )}
        <div className="author__info">
          <h4 className="author__name">
            {author.nickname || author.unique_id}
            {author.verified && <span className="badge badge--verified">verified</span>}
            <span className="author__handle">@{author.unique_id}</span>
          </h4>
          <div className="author__stats">
            <span className="stat-pill">
              <strong>{formatNumber(author.follower_count)}</strong> подписчиков
            </span>
            <span className="stat-pill">
              <strong>{formatNumber(author.following_count)}</strong> подписок
            </span>
            <span className="stat-pill">
              <strong>{formatNumber(author.video_count)}</strong> видео
            </span>
            <span className="stat-pill">
              <strong>{formatNumber(author.heart_count ?? author.heart)}</strong> лайков
            </span>
          </div>
        </div>
      </div>
    </article>
  );
}

function MetricsCard({ item }: { item: ParsedItem }) {
  const m = item.metrics;
  return (
    <article className="card">
      <h3 className="card__title">Метрики</h3>
      <div className="metrics">
        <div className="metric">
          <span className="metric__value">{formatNumber(m.views)}</span>
          <span className="metric__label">Просмотры</span>
        </div>
        <div className="metric">
          <span className="metric__value">{formatNumber(m.likes)}</span>
          <span className="metric__label">Лайки</span>
        </div>
        <div className="metric">
          <span className="metric__value">{formatNumber(m.comments)}</span>
          <span className="metric__label">Комментарии</span>
        </div>
        <div className="metric">
          <span className="metric__value">{formatNumber(m.shares)}</span>
          <span className="metric__label">Репосты</span>
        </div>
        <div className="metric">
          <span className="metric__value">{formatNumber(m.saves)}</span>
          <span className="metric__label">Сохранения</span>
        </div>
      </div>
    </article>
  );
}

function DescriptionCard({ item }: { item: ParsedItem }) {
  const preview = item.description_preview?.trim() || null;
  const full = item.description?.trim() || null;
  const keywords = item.description_keywords || [];

  if (!preview && !full && !keywords.length) return null;

  const showBoth = Boolean(preview && full && preview !== full);

  return (
    <article className="card">
      <h3 className="card__title">Описание</h3>
      {showBoth ? (
        <>
          <p className="description description--preview">{preview}</p>
          <div className="description">{full}</div>
          {item.description_length != null && (
            <p className="description__meta">{formatNumber(item.description_length)} символов</p>
          )}
        </>
      ) : (
        <>
          {(full || preview) && <div className="description">{full || preview}</div>}
          {item.description_length != null && full && (
            <p className="description__meta">{formatNumber(item.description_length)} символов</p>
          )}
        </>
      )}
      {keywords.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h3 className="card__title">Ключевые слова</h3>
          <div className="tags">
            {keywords.map((k) => (
              <span key={k} className="tag tag--keyword">
                {k}
              </span>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}

function HashtagsCard({ hashtags }: { hashtags: ParsedItem["hashtags"] }) {
  if (!hashtags?.length) return null;
  return (
    <article className="card">
      <h3 className="card__title">Хештеги</h3>
      <div className="tags">
        {hashtags.map((h) => (
          <span key={h.name} className="tag">
            #{h.name}
          </span>
        ))}
      </div>
    </article>
  );
}

function MusicCard({ music }: { music: NonNullable<ParsedItem["music"]> }) {
  return (
    <article className="card">
      <h3 className="card__title">Музыка</h3>
      <div className="music">
        <a
          href={music.cover_large}
          target="_blank"
          rel="noopener noreferrer"
          className="music__cover-link"
          title="Открыть обложку"
        >
          <img className="music__cover" src={music.cover_large} alt="" loading="lazy" />
        </a>
        <div className="music__info">
          <p className="music__title">
            <a href={music.play_url} target="_blank" rel="noopener noreferrer">
              {music.title}
            </a>
          </p>
          <p className="music__artist">
            {music.author_name} · {music.duration}с{music.original ? " · оригинал" : ""}
          </p>
        </div>
      </div>
      <div className="url-list url-list--compact">
        <UrlRow label="Трек" url={music.play_url} />
        <UrlRow label="Обложка" url={music.cover_large} />
      </div>
    </article>
  );
}

function CommentRow({
  comment,
  isReply,
  authorUid,
}: {
  comment: ParsedComment;
  isReply?: boolean;
  authorUid: string | null;
}) {
  const isAuthor = authorUid && comment.user.uid === authorUid;
  return (
    <div className={`comment-row${isReply ? " comment-row--reply" : ""}`}>
      <div className={`comment-avatar${isReply ? " comment-avatar--sm" : ""}`} aria-hidden="true">
        {commentInitials(comment)}
      </div>
      <div className="comment-content">
        <div className="comment-topline">
          <span className="comment-username">
            {comment.user.nickname || comment.user.unique_id || "Аноним"}
          </span>
          {isAuthor && <span className="comment-author-badge">Автор</span>}
          {comment.create_time != null && (
            <span className="comment-time">{formatRelativeTime(comment.create_time)}</span>
          )}
        </div>
        <p className="comment-text">{comment.text || ""}</p>
      </div>
      <div className="comment-like" aria-label="Лайки">
        {comment.is_author_digged && (
          <span className="comment-liked" title="Автор видео лайкнул">
            ♥
          </span>
        )}
        <span className="comment-like__count">
          {comment.digg_count != null ? formatNumber(comment.digg_count) : ""}
        </span>
      </div>
    </div>
  );
}

function CommentThreadView({
  thread,
  authorUid,
  searching,
  expandedReplyThreads,
  onToggleReplies,
}: {
  thread: CommentThread;
  authorUid: string | null;
  searching: boolean;
  expandedReplyThreads: Set<string>;
  onToggleReplies: (parentId: string, expand: boolean) => void;
}) {
  const replies = thread.replies || [];
  const forceExpand = searching || thread.searchExpand;
  const expanded = forceExpand || expandedReplyThreads.has(thread.comment_id);
  const visibleReplies = expanded ? replies : replies.slice(0, REPLIES_PREVIEW);
  const replyTotal = thread.reply_comment_total;

  return (
    <li className="comment-thread">
      <CommentRow comment={thread} authorUid={authorUid} />
      {replies.length > 0 ? (
        <div className="comment-replies">
          {visibleReplies.map((r) => (
            <CommentRow key={r.comment_id} comment={r} isReply authorUid={authorUid} />
          ))}
          {!searching && replies.length > REPLIES_PREVIEW && (
            <button
              type="button"
              className="comment-replies-toggle"
              onClick={() => onToggleReplies(thread.comment_id, !expanded)}
            >
              {expanded
                ? "Скрыть ответы"
                : `Показать ещё ${formatNumber(replies.length - REPLIES_PREVIEW)} ${pluralReplies(replies.length - REPLIES_PREVIEW)}`}
            </button>
          )}
          {!searching &&
            replies.length > 0 &&
            replyTotal != null &&
            replyTotal > replies.length &&
            !expanded && (
              <span className="comment-replies-hint">
                Загружено {formatNumber(replies.length)} из {formatNumber(replyTotal)}
              </span>
            )}
        </div>
      ) : (
        !searching &&
        replyTotal != null &&
        replyTotal > 0 && (
          <div className="comment-replies">
            <span className="comment-replies-hint">
              {formatNumber(replyTotal)} {pluralReplies(replyTotal)} (не загружены)
            </span>
          </div>
        )
      )}
    </li>
  );
}

function CommentsPanel({
  comments,
  stats,
  authorUid,
  visibleCount,
  setVisibleCount,
  expandedReplyThreads,
  setExpandedReplyThreads,
  searchQuery,
  setSearchQuery,
}: {
  comments: ParsedComment[];
  stats: CommentStats;
  authorUid: string | null;
  visibleCount: number;
  setVisibleCount: (n: number | ((c: number) => number)) => void;
  expandedReplyThreads: Set<string>;
  setExpandedReplyThreads: Dispatch<SetStateAction<Set<string>>>;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
}) {
  const searchRef = useRef<HTMLInputElement>(null);

  const allThreads = useMemo(() => buildCommentTree(comments), [comments]);
  const { threads: displayThreads, searching } = useMemo(
    () => prepareThreadsForSearch(allThreads, searchQuery),
    [allThreads, searchQuery],
  );
  const visibleThreads = searching ? displayThreads : displayThreads.slice(0, visibleCount);
  const remaining = searching ? 0 : displayThreads.length - visibleThreads.length;

  const onToggleReplies = useCallback(
    (parentId: string, expand: boolean) => {
      setExpandedReplyThreads((prev) => {
        const next = new Set(prev);
        if (expand) next.add(parentId);
        else next.delete(parentId);
        return next;
      });
    },
    [setExpandedReplyThreads],
  );

  if (!comments.length) {
    return (
      <aside className="results-comments" aria-label="Комментарии">
        <div className="comments-panel">
          <div className="comments-panel__header">
            <h3 className="comments-panel__title">Комментарии</h3>
          </div>
          <div className="comments-panel__body">
            <p className="comments-empty">Комментарии не собраны</p>
          </div>
        </div>
      </aside>
    );
  }

  const shownLine = searching
    ? `Найдено ${formatNumber(visibleThreads.length)} из ${formatNumber(allThreads.length)} веток`
    : `${formatNumber(visibleThreads.length)} из ${formatNumber(displayThreads.length)} веток`;

  return (
    <aside className="results-comments" aria-label="Комментарии">
      <div className="comments-panel">
        <div className="comments-panel__header">
          <h3 className="comments-panel__title">Комментарии</h3>
          <div className="comments-search">
            <span className="comments-search__icon" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3-3" />
              </svg>
            </span>
            <input
              ref={searchRef}
              type="search"
              className="comments-search__input"
              id="comments-search-input"
              placeholder="Поиск по тексту, нику, смайликам…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
            {searchQuery && (
              <button
                type="button"
                className="comments-search__clear"
                aria-label="Очистить поиск"
                onClick={() => {
                  setSearchQuery("");
                  searchRef.current?.focus();
                }}
              >
                ×
              </button>
            )}
          </div>
          <p className="comments-panel__summary">
            {formatNumber(stats.total)} всего · {formatNumber(stats.author_comments)} от автора ·{" "}
            {formatNumber(stats.audience)} аудитория
          </p>
          <p className="comments-panel__shown">{shownLine}</p>
        </div>
        <div className="comments-panel__body">
          {searching && visibleThreads.length === 0 ? (
            <p className="comments-empty">Ничего не найдено</p>
          ) : (
            <ul className="comment-list">
              {visibleThreads.map((t) => (
                <CommentThreadView
                  key={t.comment_id}
                  thread={t}
                  authorUid={authorUid}
                  searching={searching}
                  expandedReplyThreads={expandedReplyThreads}
                  onToggleReplies={onToggleReplies}
                />
              ))}
            </ul>
          )}
          {!searching && remaining > 0 && (
            <div className="comments-expand">
              <button
                type="button"
                className="btn-expand"
                onClick={() =>
                  setVisibleCount((c) => Math.min(displayThreads.length, c + COMMENTS_STEP))
                }
              >
                Показать ещё {formatNumber(Math.min(remaining, COMMENTS_STEP))}
              </button>
              {remaining > COMMENTS_STEP && (
                <button
                  type="button"
                  className="btn-expand btn-expand--ghost"
                  onClick={() => setVisibleCount(displayThreads.length)}
                >
                  Показать все ({formatNumber(displayThreads.length)})
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

export function InspectorResults({ data }: { data: InspectResult }) {
  const { item, comments, comment_stats: stats, url: postUrl } = data;
  const authorUid = item.author?.tiktok_id ?? null;

  const allThreads = useMemo(() => buildCommentTree(comments), [comments]);
  const [visibleCount, setVisibleCount] = useState(() =>
    Math.min(COMMENTS_PREVIEW, allThreads.length),
  );
  const [expandedReplyThreads, setExpandedReplyThreads] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <section className="results" aria-label="Результаты анализа">
      <div className="results-layout">
        <div className="results-main">
          <article className="card">
            <h3 className="card__title">
              Пост <span className="badge badge--type">{item.content_type}</span>
            </h3>
            <p className="description__meta">
              ID: {item.post_id}
              {item.location_created ? ` · ${item.location_created}` : ""}
            </p>
          </article>
          <MediaSection item={item} postUrl={postUrl} />
          <AuthorCard author={item.author} />
          <MetricsCard item={item} />
          <DescriptionCard item={item} />
          <HashtagsCard hashtags={item.hashtags} />
          {item.music && <MusicCard music={item.music} />}
        </div>
        <CommentsPanel
          comments={comments}
          stats={stats}
          authorUid={authorUid}
          visibleCount={visibleCount}
          setVisibleCount={setVisibleCount}
          expandedReplyThreads={expandedReplyThreads}
          setExpandedReplyThreads={setExpandedReplyThreads}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
        />
      </div>
    </section>
  );
}
