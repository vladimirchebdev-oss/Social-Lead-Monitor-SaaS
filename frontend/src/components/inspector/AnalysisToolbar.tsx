import { Link } from "react-router-dom";
import type { AnalysisSummary } from "../../api/client";
import { formatNumber } from "./utils";

export function AnalysisToolbar({
  analysisId,
  isSaved,
  onClose,
  onSave,
  onSaveAndClose,
  busy,
}: {
  analysisId: string;
  isSaved: boolean;
  onClose: () => void;
  onSave: () => void;
  onSaveAndClose: () => void;
  busy: boolean;
}) {
  return (
    <div className="analysis-toolbar">
      <p className="analysis-toolbar__hint">
        {isSaved ? "Анализ в сохранённых" : "Последний анализ — можно сохранить в библиотеку"}
      </p>
      <div className="analysis-toolbar__actions">
        <button type="button" className="btn btn--ghost btn--sm" onClick={onClose} disabled={busy}>
          Закрыть
        </button>
        {!isSaved && (
          <button type="button" className="btn btn--ghost btn--sm" onClick={onSave} disabled={busy}>
            Сохранить
          </button>
        )}
        <button
          type="button"
          className="btn btn--primary btn--sm"
          onClick={onSaveAndClose}
          disabled={busy}
        >
          {isSaved ? "Закрыть" : "Сохранить и закрыть"}
        </button>
        {isSaved && (
          <Link to={`/saved/${analysisId}`} className="btn btn--ghost btn--sm">
            Открыть отдельно
          </Link>
        )}
      </div>
    </div>
  );
}

export function SavedAnalysisCard({
  item,
  onDelete,
}: {
  item: AnalysisSummary;
  onDelete?: (id: string) => void;
}) {
  const date = item.saved_at || item.analyzed_at;
  return (
    <article className="saved-card">
      <Link to={`/saved/${item.id}`} className="saved-card__link">
        <div className="saved-card__head">
          {item.author_avatar_url ? (
            <img src={item.author_avatar_url} alt="" className="saved-card__avatar" />
          ) : (
            <div className="saved-card__avatar saved-card__avatar--placeholder">
              {(item.author_name || item.author_username || "?")[0]?.toUpperCase()}
            </div>
          )}
          <div className="saved-card__meta">
            <h3 className="saved-card__author">
              {item.author_name || item.author_username || "Без автора"}
            </h3>
            {item.author_username && (
              <p className="saved-card__username">@{item.author_username}</p>
            )}
            <p className="saved-card__date">
              {new Date(date).toLocaleString("ru-RU", {
                day: "numeric",
                month: "short",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          </div>
          <span className={`saved-card__platform saved-card__platform--${item.platform}`}>
            {item.platform}
          </span>
        </div>
        {item.description_preview && (
          <p className="saved-card__desc">{item.description_preview}</p>
        )}
        <div className="saved-card__metrics">
          <span>{formatNumber(item.views)} просм.</span>
          <span>{formatNumber(item.likes)} лайков</span>
          <span>{formatNumber(item.comments_count)} комм.</span>
        </div>
      </Link>
      {onDelete && (
        <button
          type="button"
          className="saved-card__delete btn btn--ghost btn--sm"
          onClick={(e) => {
            e.preventDefault();
            onDelete(item.id);
          }}
          aria-label="Удалить из сохранённых"
        >
          Удалить
        </button>
      )}
    </article>
  );
}
