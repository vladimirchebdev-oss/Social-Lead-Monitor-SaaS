import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { InspectorResults } from "../components/inspector/InspectorResults";
import { AnalysisToolbar } from "../components/inspector/AnalysisToolbar";
import type { InspectResult } from "../components/inspector/types";
import "../styles/inspector.css";

export function SavedAnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<InspectResult | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [isSaved, setIsSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api
      .getAnalysis(id)
      .then((detail) => {
        setResult(detail.payload);
        setAnalysisId(detail.id);
        setIsSaved(detail.is_saved);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSave = async () => {
    if (!analysisId) return;
    setBusy(true);
    try {
      await api.saveAnalysis(analysisId);
      setIsSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setBusy(false);
    }
  };

  const handleSaveAndClose = async () => {
    if (!analysisId) return;
    setBusy(true);
    try {
      if (!isSaved) await api.saveAnalysis(analysisId);
      navigate("/saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  const handleClose = () => {
    navigate(isSaved ? "/saved" : "/analyze");
  };

  if (loading) return <div className="state state--loading">Загрузка анализа…</div>;
  if (error) return <div className="alert alert--error">{error}</div>;
  if (!result) return null;

  return (
    <div className="analyze-page">
      <div className="page-head">
        <Link to="/saved" className="page-head__back">
          ← Сохранённые
        </Link>
        <h2>Анализ поста</h2>
      </div>

      {analysisId && (
        <AnalysisToolbar
          analysisId={analysisId}
          isSaved={isSaved}
          onClose={handleClose}
          onSave={handleSave}
          onSaveAndClose={handleSaveAndClose}
          busy={busy}
        />
      )}

      <InspectorResults key={result.url} data={result} />
    </div>
  );
}
