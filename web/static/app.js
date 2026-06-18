const PLATFORM_COLORS = {
  tiktok: "tiktok",
  instagram: "instagram",
  youtube: "youtube",
};

const COMMENTS_PREVIEW = 15;
const COMMENTS_STEP = 20;
const REPLIES_PREVIEW = 2;

const $ = (sel) => document.querySelector(sel);

const form = $("#fetch-form");
const urlInput = $("#url-input");
const showBrowser = $("#show-browser");
const submitBtn = $("#submit-btn");
const btnText = submitBtn.querySelector(".btn__text");
const btnSpinner = submitBtn.querySelector(".btn__spinner");
const platformTabs = $("#platform-tabs");
const platformHint = $("#platform-hint");
const statusEl = $("#status");
const resultsEl = $("#results");
const emptyState = $("#empty-state");
const platformCount = $("#platform-count");

let platforms = [];
let lastComments = [];
let lastCommentStats = null;
let lastAuthorUid = null;
let commentsVisibleCount = COMMENTS_PREVIEW;
let expandedReplyThreads = new Set();
let commentSearchQuery = "";
let commentsSearchFocused = false;

function formatNumber(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 10_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString("ru-RU");
}

function formatDate(unixSeconds) {
  if (!unixSeconds) return "";
  return new Date(unixSeconds * 1000).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatRelativeTime(unixSeconds) {
  if (!unixSeconds) return "";
  const diff = Date.now() / 1000 - unixSeconds;
  if (diff < 45) return "только что";
  if (diff < 3600) return `${Math.floor(diff / 60)} мин`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} д`;
  if (diff < 2592000) return `${Math.floor(diff / 604800)} нед`;
  return formatDate(unixSeconds);
}

function commentInitials(c) {
  const name = c.user.nickname || c.user.unique_id || "?";
  return name.trim()[0]?.toUpperCase() || "?";
}

function buildCommentTree(comments) {
  const nodes = new Map();
  for (const c of comments) {
    nodes.set(c.comment_id, { ...c, replies: [] });
  }

  const childIds = new Set();
  for (const c of comments) {
    const parentId = c.parent_comment_id;
    if (c.is_reply && parentId && parentId !== "0" && nodes.has(parentId)) {
      nodes.get(parentId).replies.push(nodes.get(c.comment_id));
      childIds.add(c.comment_id);
    }
  }

  const roots = [];
  for (const c of comments) {
    if (!childIds.has(c.comment_id)) {
      roots.push(nodes.get(c.comment_id));
    }
  }
  return roots;
}

function countVisibleComments(threads) {
  let n = 0;
  for (const thread of threads) {
    n += 1;
    const replies = thread.replies || [];
    const expanded = expandedReplyThreads.has(thread.comment_id);
    const shown = expanded ? replies.length : Math.min(replies.length, REPLIES_PREVIEW);
    n += shown;
  }
  return n;
}

function normalizeSearchText(value) {
  return String(value ?? "").normalize("NFC").toLocaleLowerCase("ru");
}

function commentMatchesSearch(comment, query) {
  const q = normalizeSearchText(query.trim());
  if (!q) return true;
  const parts = [
    comment.text,
    comment.user?.nickname,
    comment.user?.unique_id,
  ];
  return parts.some((part) => normalizeSearchText(part).includes(q));
}

function prepareThreadsForSearch(threads, query) {
  const q = query.trim();
  if (!q) return { threads, searching: false };

  const filtered = [];
  for (const thread of threads) {
    const parentMatch = commentMatchesSearch(thread, q);
    const matchingReplies = (thread.replies || []).filter((reply) => commentMatchesSearch(reply, q));

    if (parentMatch) {
      filtered.push({ ...thread, replies: thread.replies || [], searchExpand: true });
    } else if (matchingReplies.length) {
      filtered.push({ ...thread, replies: matchingReplies, searchExpand: true });
    }
  }
  return { threads: filtered, searching: true };
}

function renderCommentsSearchInput() {
  return `
    <div class="comments-search">
      <span class="comments-search__icon" aria-hidden="true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="7"/>
          <path d="M20 20l-3-3"/>
        </svg>
      </span>
      <input
        type="search"
        class="comments-search__input"
        id="comments-search-input"
        placeholder="Поиск по тексту, нику, смайликам…"
        value="${escapeHtml(commentSearchQuery)}"
        autocomplete="off"
        spellcheck="false"
      />
      ${
        commentSearchQuery
          ? `<button type="button" class="comments-search__clear" data-action="clear-search" aria-label="Очистить поиск">×</button>`
          : ""
      }
    </div>
  `;
}

function restoreCommentsSearchFocus() {
  if (!commentsSearchFocused) return;
  requestAnimationFrame(() => {
    const input = resultsEl.querySelector("#comments-search-input");
    if (!input) return;
    input.focus();
    const pos = commentSearchQuery.length;
    input.setSelectionRange(pos, pos);
  });
}

function detectPlatformFromUrl(url) {
  const trimmed = url.trim();
  if (!trimmed) return null;
  try {
    const host = new URL(trimmed).hostname.toLowerCase().replace(/^www\./, "");
    return platforms.find((p) =>
      p.host_patterns.some((pattern) => host === pattern || host.endsWith(`.${pattern}`))
    ) ?? null;
  } catch {
    return null;
  }
}

function renderPlatformTabs(detectedId = null) {
  platformTabs.innerHTML = platforms
    .map((p) => {
      const classes = ["platform-tab"];
      if (!p.available) classes.push("platform-tab--disabled");
      if (detectedId === p.id) classes.push("platform-tab--detected");
      if (p.available && detectedId === p.id) classes.push("platform-tab--active");

      const badge = p.available ? "" : `<span class="platform-tab__badge">скоро</span>`;
      const dotClass = PLATFORM_COLORS[p.id] ? `platform-tab__dot--${PLATFORM_COLORS[p.id]}` : "";

      return `
        <span class="${classes.join(" ")}" data-platform="${p.id}">
          <span class="platform-tab__dot ${dotClass}"></span>
          ${escapeHtml(p.name)}
          ${badge}
        </span>
      `;
    })
    .join("");
}

function updatePlatformHint(detected) {
  if (!urlInput.value.trim()) {
    platformHint.textContent = "Вставьте ссылку — платформа определится автоматически";
    platformHint.classList.remove("field__hint--error");
    return;
  }
  if (!detected) {
    platformHint.textContent = "Платформа не распознана — пока поддерживается только TikTok";
    platformHint.classList.add("field__hint--error");
    return;
  }
  platformHint.classList.remove("field__hint--error");
  if (detected.available) {
    platformHint.textContent = `Распознано: ${detected.name}`;
  } else {
    platformHint.textContent = `${detected.name} — в разработке, скоро будет доступен`;
    platformHint.classList.add("field__hint--error");
  }
}

function setLoading(loading) {
  submitBtn.disabled = loading;
  urlInput.disabled = loading;
  showBrowser.disabled = loading;
  btnText.hidden = loading;
  btnSpinner.hidden = !loading;

  if (loading) {
    statusEl.hidden = false;
    statusEl.className = "status status--loading";
    statusEl.textContent = showBrowser.checked
      ? "Загрузка… Откроется окно браузера, дождитесь завершения"
      : "Загрузка данных… Это может занять до минуты";
    resultsEl.hidden = true;
    emptyState.hidden = true;
  }
}

function showError(message) {
  statusEl.hidden = false;
  statusEl.className = "status status--error";
  statusEl.textContent = message;
  resultsEl.hidden = true;
  emptyState.hidden = false;
}

function clearStatus() {
  statusEl.hidden = true;
  statusEl.textContent = "";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function truncateUrl(url, maxLen = 52) {
  const text = String(url);
  if (text.length <= maxLen) return text;
  return `${text.slice(0, maxLen - 1)}…`;
}

function renderUrlRow(label, url) {
  if (!url) return "";
  return `
    <div class="url-row">
      <span class="url-row__label">${escapeHtml(label)}</span>
      <a
        class="url-row__link"
        href="${escapeHtml(url)}"
        target="_blank"
        rel="noopener noreferrer"
        title="${escapeHtml(url)}"
      >${escapeHtml(truncateUrl(url))}</a>
      <button
        type="button"
        class="url-row__copy"
        data-copy-url="${escapeHtml(url)}"
        title="Копировать ссылку"
      >Копировать</button>
    </div>
  `;
}

function renderMediaThumb(label, imageUrl, linkUrl = null) {
  const href = linkUrl || imageUrl;
  return `
    <figure class="media-thumb">
      <a
        href="${escapeHtml(href)}"
        target="_blank"
        rel="noopener noreferrer"
        class="media-thumb__link"
      >
        <img class="media-thumb__img" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(label)}" loading="lazy" />
      </a>
      <figcaption class="media-thumb__caption">${escapeHtml(label)}</figcaption>
    </figure>
  `;
}

function renderMediaSection(item, postUrl) {
  const media = item.media;
  const rows = [renderUrlRow("Пост", postUrl)];

  if (media) {
    if (media.video_cover) rows.push(renderUrlRow("Обложка видео", media.video_cover));
    if (media.photo_urls?.length) {
      media.photo_urls.forEach((url, index) => {
        rows.push(renderUrlRow(`Фото ${index + 1}`, url));
      });
    }
  }

  const thumbs = [];
  if (media?.video_cover) {
    thumbs.push(renderMediaThumb("Обложка видео", media.video_cover));
  }
  if (media?.photo_urls?.length) {
    media.photo_urls.forEach((url, index) => {
      thumbs.push(renderMediaThumb(`Фото ${index + 1}`, url));
    });
  }

  return `
    <article class="card">
      <h3 class="card__title">Медиа и ссылки</h3>
      ${thumbs.length ? `<div class="media-thumbs">${thumbs.join("")}</div>` : ""}
      <div class="url-list">${rows.filter(Boolean).join("")}</div>
    </article>
  `;
}

async function copyToClipboard(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    const prev = btn.textContent;
    btn.textContent = "Скопировано";
    btn.classList.add("url-row__copy--done");
    setTimeout(() => {
      btn.textContent = prev;
      btn.classList.remove("url-row__copy--done");
    }, 1600);
  } catch {
    btn.textContent = "Ошибка";
    setTimeout(() => {
      btn.textContent = "Копировать";
    }, 1600);
  }
}

function renderAuthor(author) {
  const initial = (author.nickname || author.unique_id || "?")[0].toUpperCase();
  const avatar = author.avatar_larger
    ? `<img class="author__avatar" src="${escapeHtml(author.avatar_larger)}" alt="" loading="lazy" />`
    : `<div class="author__avatar author__avatar--placeholder">${escapeHtml(initial)}</div>`;

  const verified = author.verified
    ? `<span class="badge badge--verified">verified</span>`
    : "";

  return `
    <article class="card">
      <h3 class="card__title">Автор</h3>
      <div class="author">
        ${avatar}
        <div class="author__info">
          <h4 class="author__name">
            ${escapeHtml(author.nickname || author.unique_id)}
            ${verified}
            <span class="author__handle">@${escapeHtml(author.unique_id)}</span>
          </h4>
          <div class="author__stats">
            <span class="stat-pill"><strong>${formatNumber(author.follower_count)}</strong> подписчиков</span>
            <span class="stat-pill"><strong>${formatNumber(author.following_count)}</strong> подписок</span>
            <span class="stat-pill"><strong>${formatNumber(author.video_count)}</strong> видео</span>
            <span class="stat-pill"><strong>${formatNumber(author.heart_count)}</strong> лайков</span>
          </div>
        </div>
      </div>
    </article>
  `;
}

function getCommentsDisplayInfo() {
  if (!lastCommentStats) {
    return { collected: 0, displayed: 0 };
  }
  const allThreads = buildCommentTree(lastComments);
  const { threads: displayThreads, searching } = prepareThreadsForSearch(allThreads, commentSearchQuery);
  const visibleThreads = searching ? displayThreads : displayThreads.slice(0, commentsVisibleCount);
  return {
    collected: lastCommentStats.total,
    displayed: countVisibleComments(visibleThreads),
  };
}

function renderCollectedMetric(displayInfo) {
  const { collected, displayed } = displayInfo;
  return `
    <div class="metric metric--collected" id="metric-collected">
      <span class="metric__value metric__value--dual">
        <span title="Собрано парсером">${formatNumber(collected)}</span>
        <span class="metric__slash" aria-hidden="true">/</span>
        <span class="metric__value-secondary" title="Показано в списке">${formatNumber(displayed)}</span>
      </span>
      <span class="metric__label">Собрано / на экране</span>
    </div>
  `;
}

function updateMetricsDisplayCell() {
  const cell = resultsEl.querySelector("#metric-collected");
  if (!cell) return;
  cell.outerHTML = renderCollectedMetric(getCommentsDisplayInfo());
}

function renderMetrics(item, stats) {
  const m = item.metrics;
  const displayInfo = getCommentsDisplayInfo();
  return `
    <article class="card">
      <h3 class="card__title">Метрики</h3>
      <div class="metrics">
        <div class="metric">
          <span class="metric__value">${formatNumber(m.views)}</span>
          <span class="metric__label">Просмотры</span>
        </div>
        <div class="metric">
          <span class="metric__value">${formatNumber(m.likes)}</span>
          <span class="metric__label">Лайки</span>
        </div>
        <div class="metric">
          <span class="metric__value">${formatNumber(m.comments)}</span>
          <span class="metric__label">Комментарии</span>
        </div>
        <div class="metric">
          <span class="metric__value">${formatNumber(m.shares)}</span>
          <span class="metric__label">Репосты</span>
        </div>
        <div class="metric">
          <span class="metric__value">${formatNumber(m.saves)}</span>
          <span class="metric__label">Сохранения</span>
        </div>
        ${renderCollectedMetric(displayInfo)}
      </div>
    </article>
  `;
}

function renderDescription(item) {
  const preview = item.description_preview?.trim() || null;
  const full = item.description?.trim() || null;
  const keywords = item.description_keywords || [];

  if (!preview && !full && !keywords.length) return "";

  let body = "";
  const showBoth = Boolean(preview && full && preview !== full);

  if (showBoth) {
    body += `<p class="description description--preview">${escapeHtml(preview)}</p>`;
    body += `<div class="description">${escapeHtml(full)}</div>`;
    if (item.description_length) {
      body += `<p class="description__meta">${formatNumber(item.description_length)} символов</p>`;
    }
  } else {
    const text = full || preview;
    if (text) {
      body += `<div class="description">${escapeHtml(text)}</div>`;
      if (item.description_length && full) {
        body += `<p class="description__meta">${formatNumber(item.description_length)} символов</p>`;
      }
    }
  }

  let keywordsHtml = "";
  if (keywords.length) {
    keywordsHtml = `
      <div style="margin-top: 16px">
        <h3 class="card__title">Ключевые слова</h3>
        <div class="tags">
          ${keywords.map((k) => `<span class="tag tag--keyword">${escapeHtml(k)}</span>`).join("")}
        </div>
      </div>
    `;
  }

  return `
    <article class="card">
      <h3 class="card__title">Описание</h3>
      ${body}
      ${keywordsHtml}
    </article>
  `;
}

function renderHashtags(hashtags) {
  if (!hashtags?.length) return "";
  return `
    <article class="card">
      <h3 class="card__title">Хештеги</h3>
      <div class="tags">
        ${hashtags.map((h) => `<span class="tag">#${escapeHtml(h.name)}</span>`).join("")}
      </div>
    </article>
  `;
}

function renderMusic(music) {
  if (!music) return "";
  return `
    <article class="card">
      <h3 class="card__title">Музыка</h3>
      <div class="music">
        <a
          href="${escapeHtml(music.cover_large)}"
          target="_blank"
          rel="noopener noreferrer"
          class="music__cover-link"
          title="Открыть обложку"
        >
          <img class="music__cover" src="${escapeHtml(music.cover_large)}" alt="" loading="lazy" />
        </a>
        <div class="music__info">
          <p class="music__title">
            <a href="${escapeHtml(music.play_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(music.title)}</a>
          </p>
          <p class="music__artist">${escapeHtml(music.author_name)} · ${music.duration}с${music.original ? " · оригинал" : ""}</p>
        </div>
      </div>
      <div class="url-list url-list--compact">
        ${renderUrlRow("Трек", music.play_url)}
        ${renderUrlRow("Обложка", music.cover_large)}
      </div>
    </article>
  `;
}

function renderCommentRow(c, { isReply = false, authorUid = null } = {}) {
  const isAuthor = authorUid && c.user.uid === authorUid;
  const authorBadge = isAuthor ? `<span class="comment-author-badge">Автор</span>` : "";
  const liked = c.is_author_digged
    ? `<span class="comment-liked" title="Автор видео лайкнул">♥</span>`
    : "";

  return `
    <div class="comment-row ${isReply ? "comment-row--reply" : ""}">
      <div class="comment-avatar ${isReply ? "comment-avatar--sm" : ""}" aria-hidden="true">
        ${escapeHtml(commentInitials(c))}
      </div>
      <div class="comment-content">
        <div class="comment-topline">
          <span class="comment-username">${escapeHtml(c.user.nickname || c.user.unique_id || "Аноним")}</span>
          ${authorBadge}
          ${c.create_time ? `<span class="comment-time">${formatRelativeTime(c.create_time)}</span>` : ""}
        </div>
        <p class="comment-text">${escapeHtml(c.text || "")}</p>
      </div>
      <div class="comment-like" aria-label="Лайки">
        ${liked}
        <span class="comment-like__count">${c.digg_count != null ? formatNumber(c.digg_count) : ""}</span>
      </div>
    </div>
  `;
}

function renderRepliesToggle(parentId, repliesLength, expanded) {
  if (repliesLength <= REPLIES_PREVIEW) return "";
  if (expanded) {
    return `
      <button type="button" class="comment-replies-toggle" data-action="replies-less" data-parent-id="${escapeHtml(parentId)}">
        Скрыть ответы
      </button>
    `;
  }
  const hidden = repliesLength - REPLIES_PREVIEW;
  return `
    <button type="button" class="comment-replies-toggle" data-action="replies-more" data-parent-id="${escapeHtml(parentId)}">
      Показать ещё ${formatNumber(hidden)} ${pluralReplies(hidden)}
    </button>
  `;
}

function pluralReplies(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "ответ";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "ответа";
  return "ответов";
}

function renderCommentThread(thread, authorUid, { searching = false } = {}) {
  const replies = thread.replies || [];
  const forceExpand = searching || thread.searchExpand;
  const expanded = forceExpand || expandedReplyThreads.has(thread.comment_id);
  const visibleReplies = expanded ? replies : replies.slice(0, REPLIES_PREVIEW);
  const replyTotal = thread.reply_comment_total;

  const repliesHtml =
    replies.length > 0
      ? `
        <div class="comment-replies">
          ${visibleReplies.map((r) => renderCommentRow(r, { isReply: true, authorUid })).join("")}
          ${searching ? "" : renderRepliesToggle(thread.comment_id, replies.length, expanded)}
          ${
            !searching && replies.length > 0 && replyTotal != null && replyTotal > replies.length && !expanded
              ? `<span class="comment-replies-hint">Загружено ${formatNumber(replies.length)} из ${formatNumber(replyTotal)}</span>`
              : ""
          }
        </div>
      `
      : !searching && replyTotal != null && replyTotal > 0
        ? `<div class="comment-replies"><span class="comment-replies-hint">${formatNumber(replyTotal)} ${pluralReplies(replyTotal)} (не загружены)</span></div>`
        : "";

  return `
    <li class="comment-thread">
      ${renderCommentRow(thread, { authorUid })}
      ${repliesHtml}
    </li>
  `;
}

function renderCommentsPanel(comments, stats, visibleCount) {
  if (!comments?.length) {
    return `
      <aside class="results-comments" aria-label="Комментарии">
        <div class="comments-panel">
          <div class="comments-panel__header">
            <h3 class="comments-panel__title">Комментарии</h3>
          </div>
          <div class="comments-panel__body">
            <p class="comments-empty">Комментарии не собраны</p>
          </div>
        </div>
      </aside>
    `;
  }

  const allThreads = buildCommentTree(comments);
  const { threads: displayThreads, searching } = prepareThreadsForSearch(allThreads, commentSearchQuery);
  const visibleThreads = searching ? displayThreads : displayThreads.slice(0, visibleCount);
  const remaining = searching ? 0 : displayThreads.length - visibleThreads.length;

  const expandButtons =
    !searching && remaining > 0
      ? `
        <div class="comments-expand">
          <button type="button" class="btn-expand" data-action="more">
            Показать ещё ${formatNumber(Math.min(remaining, COMMENTS_STEP))}
          </button>
          ${
            remaining > COMMENTS_STEP
              ? `<button type="button" class="btn-expand btn-expand--ghost" data-action="all">
                  Показать все (${formatNumber(displayThreads.length)})
                </button>`
              : ""
          }
        </div>
      `
      : "";

  const shownLine = searching
    ? `Найдено ${formatNumber(visibleThreads.length)} из ${formatNumber(allThreads.length)} веток`
    : `${formatNumber(visibleThreads.length)} из ${formatNumber(displayThreads.length)} веток`;

  return `
    <aside class="results-comments" aria-label="Комментарии">
      <div class="comments-panel">
        <div class="comments-panel__header">
          <h3 class="comments-panel__title">Комментарии</h3>
          ${renderCommentsSearchInput()}
          <p class="comments-panel__summary">
            ${formatNumber(stats.total)} всего · ${formatNumber(stats.author_comments)} от автора · ${formatNumber(stats.audience)} аудитория
          </p>
          <p class="comments-panel__shown">${shownLine}</p>
        </div>
        <div class="comments-panel__body">
          ${
            searching && visibleThreads.length === 0
              ? `<p class="comments-empty">Ничего не найдено</p>`
              : `<ul class="comment-list">
                  ${visibleThreads.map((t) => renderCommentThread(t, lastAuthorUid, { searching })).join("")}
                </ul>`
          }
          ${expandButtons}
        </div>
      </div>
    </aside>
  `;
}

function updateCommentsPanel() {
  const panel = resultsEl.querySelector(".results-comments");
  if (!panel) return;
  const next = renderCommentsPanel(lastComments, lastCommentStats, commentsVisibleCount);
  panel.outerHTML = next;
  updateMetricsDisplayCell();
  restoreCommentsSearchFocus();
}

function handleResultsClick(event) {
  const copyBtn = event.target.closest("[data-copy-url]");
  if (copyBtn && resultsEl.contains(copyBtn)) {
    event.preventDefault();
    copyToClipboard(copyBtn.dataset.copyUrl, copyBtn);
    return;
  }
  handleCommentsAction(event);
}

function handleCommentsAction(event) {
  const btn = event.target.closest("[data-action]");
  if (!btn || !resultsEl.contains(btn)) return;

  const action = btn.dataset.action;
  if (action === "more") {
    const threads = buildCommentTree(lastComments);
    commentsVisibleCount = Math.min(
      threads.length,
      commentsVisibleCount + COMMENTS_STEP
    );
    updateCommentsPanel();
  } else if (action === "all") {
    commentsVisibleCount = buildCommentTree(lastComments).length;
    updateCommentsPanel();
  } else if (action === "replies-more") {
    expandedReplyThreads.add(btn.dataset.parentId);
    updateCommentsPanel();
  } else if (action === "replies-less") {
    expandedReplyThreads.delete(btn.dataset.parentId);
    updateCommentsPanel();
  } else if (action === "clear-search") {
    commentSearchQuery = "";
    commentsSearchFocused = true;
    updateCommentsPanel();
  }
}

function handleCommentsSearchInput(event) {
  const input = event.target;
  if (input.id !== "comments-search-input" || !resultsEl.contains(input)) return;
  commentSearchQuery = input.value;
  commentsSearchFocused = true;
  updateCommentsPanel();
}

function handleCommentsSearchFocus(event) {
  if (event.target.id === "comments-search-input") {
    commentsSearchFocused = true;
  }
}

function handleCommentsSearchBlur(event) {
  if (event.target.id === "comments-search-input") {
    commentsSearchFocused = false;
  }
}

function renderResults(data) {
  const { item, comments, comment_stats: stats, url: postUrl } = data;
  const typeBadge = `<span class="badge badge--type">${escapeHtml(item.content_type)}</span>`;

  lastComments = comments || [];
  lastCommentStats = stats;
  lastAuthorUid = item.author?.tiktok_id ?? null;
  expandedReplyThreads = new Set();
  commentSearchQuery = "";
  commentsSearchFocused = false;
  const threadCount = buildCommentTree(lastComments).length;
  commentsVisibleCount = Math.min(COMMENTS_PREVIEW, threadCount);

  resultsEl.innerHTML = `
    <div class="results-layout">
      <div class="results-main">
        <article class="card">
          <h3 class="card__title">Пост ${typeBadge}</h3>
          <p class="description__meta">ID: ${escapeHtml(item.post_id)}${item.location_created ? ` · ${escapeHtml(item.location_created)}` : ""}</p>
        </article>
        ${renderMediaSection(item, postUrl)}
        ${renderAuthor(item.author)}
        ${renderMetrics(item, stats)}
        ${renderDescription(item)}
        ${renderHashtags(item.hashtags)}
        ${renderMusic(item.music)}
      </div>
      ${renderCommentsPanel(lastComments, lastCommentStats, commentsVisibleCount)}
    </div>
  `;

  resultsEl.hidden = false;
  emptyState.hidden = true;
  clearStatus();
}

async function loadPlatforms() {
  const res = await fetch("/api/platforms");
  const data = await res.json();
  platforms = data.platforms;
  const available = platforms.filter((p) => p.available).length;
  platformCount.textContent = `${available} из ${platforms.length} платформ доступно`;
  renderPlatformTabs();
}

urlInput.addEventListener("input", () => {
  const detected = detectPlatformFromUrl(urlInput.value);
  renderPlatformTabs(detected?.id ?? null);
  updatePlatformHint(detected);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;

  const detected = detectPlatformFromUrl(url);
  if (detected && !detected.available) {
    showError(`${detected.name} пока недоступен`);
    return;
  }

  setLoading(true);

  try {
    const res = await fetch("/api/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        show_browser: showBrowser.checked,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || "Не удалось загрузить данные");
      return;
    }

    renderResults(data);
  } catch (err) {
    showError("Сетевая ошибка — проверьте, что сервер запущен");
    console.error(err);
  } finally {
    setLoading(false);
  }
});

loadPlatforms().catch((err) => {
  console.error(err);
  platformHint.textContent = "Не удалось загрузить список платформ";
  platformHint.classList.add("field__hint--error");
});

resultsEl.addEventListener("click", handleResultsClick);
resultsEl.addEventListener("input", handleCommentsSearchInput);
resultsEl.addEventListener("focusin", handleCommentsSearchFocus);
resultsEl.addEventListener("focusout", handleCommentsSearchBlur);
