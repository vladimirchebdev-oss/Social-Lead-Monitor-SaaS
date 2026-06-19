import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type AnalysisSummary } from "../api/client";
import { SavedAnalysisCard } from "../components/inspector/AnalysisToolbar";
import "../styles/inspector.css";

export function SavedPage() {
  const [items, setItems] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api
      .listSavedAnalyses()
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить анализ из сохранённых?")) return;
    try {
      await api.deleteSavedAnalysis(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось удалить");
    }
  };

  return (
    <div className="saved-page">
      <div className="page-head">
        <h2>Сохранённые анализы</h2>
        <p className="text-muted">Посты, которые вы сохранили для повторного просмотра</p>
      </div>

      <div className="page-head__actions">
        <Link to="/analyze" className="btn btn--primary btn--sm">
          Новый анализ
        </Link>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      {loading && <div className="state state--loading">Загрузка…</div>}

      {!loading && items.length === 0 && (
        <div className="state state--empty saved-page__empty">
          <p>Пока нет сохранённых анализов.</p>
          <p className="text-muted">
            После анализа поста нажмите «Сохранить» или «Сохранить и закрыть».
          </p>
          <Link to="/analyze" className="btn btn--primary">
            Перейти к анализу
          </Link>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="saved-list">
          {items.map((item) => (
            <SavedAnalysisCard key={item.id} item={item} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
