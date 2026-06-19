import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AnalysisToolbar } from "../components/inspector/AnalysisToolbar";
import { InspectorResults } from "../components/inspector/InspectorResults";
import type { InspectResult, PlatformInfo } from "../components/inspector/types";
import { PLATFORM_HOSTS } from "../components/inspector/types";
import { detectPlatformFromUrl } from "../components/inspector/utils";
import "../styles/inspector.css";

const PLATFORM_COLORS: Record<string, string> = {
  tiktok: "tiktok",
  threads: "threads",
};

export function AnalyzePage() {
  const { hasPlatform, user } = useAuth();
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [url, setUrl] = useState("");
  const [showBrowser, setShowBrowser] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InspectResult | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [isSaved, setIsSaved] = useState(false);
  const [toolbarBusy, setToolbarBusy] = useState(false);

  useEffect(() => {
    api.getPlatforms().then((d) => setPlatforms(d.platforms));
  }, []);

  useEffect(() => {
    api
      .getAnalysisSession()
      .then((session) => {
        if (session.analysis) {
          setResult(session.analysis.payload);
          setAnalysisId(session.analysis.id);
          setIsSaved(session.analysis.is_saved);
          setUrl(session.analysis.post_url);
        }
      })
      .catch(() => {})
      .finally(() => setSessionLoading(false));
  }, []);

  const detected = useMemo(
    () => detectPlatformFromUrl(url, platforms, PLATFORM_HOSTS),
    [url, platforms],
  );

  const availableCount = platforms.filter((p) => p.available).length;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;

    if (detected && !detected.available) {
      setError(`${detected.name} пока недоступен`);
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const data = await api.analyze(trimmed, user?.role === "admin" && showBrowser);
      const { analysis_id, ...payload } = data;
      setResult(payload);
      setAnalysisId(analysis_id);
      setIsSaved(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка анализа");
    } finally {
      setLoading(false);
    }
  };

  const clearResult = () => {
    setResult(null);
    setAnalysisId(null);
    setIsSaved(false);
  };

  const handleClose = async () => {
    setToolbarBusy(true);
    try {
      await api.dismissAnalysisSession();
      clearResult();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setToolbarBusy(false);
    }
  };

  const handleSave = async () => {
    if (!analysisId) return;
    setToolbarBusy(true);
    try {
      await api.saveAnalysis(analysisId);
      setIsSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setToolbarBusy(false);
    }
  };

  const handleSaveAndClose = async () => {
    if (!analysisId) return;
    setToolbarBusy(true);
    try {
      if (!isSaved) await api.saveAnalysis(analysisId);
      else await api.dismissAnalysisSession();
      clearResult();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setToolbarBusy(false);
    }
  };

  const needsSub =
    user?.role !== "admin" &&
    platforms.some((p) => p.available && !hasPlatform(p.id));

  let hint = "Вставьте ссылку — платформа определится автоматически";
  let hintError = false;
  if (url.trim()) {
    if (!detected) {
      hint = "Платформа не распознана — пока поддерживается только TikTok";
      hintError = true;
    } else if (detected.available) {
      hint = `Распознано: ${detected.name}`;
    } else {
      hint = `${detected.name} — в разработке, скоро будет доступен`;
      hintError = true;
    }
  }

  if (sessionLoading) {
    return <div className="state state--loading">Загрузка…</div>;
  }

  return (
    <div className="analyze-page">
      {needsSub && (
        <div className="alert alert--warning" style={{ marginBottom: 16 }}>
          Для анализа нужна активная подписка.{" "}
          <Link to="/billing">Подключить платформу</Link>
        </div>
      )}

      <section className="panel panel--input" aria-labelledby="fetch-heading">
        <h2 id="fetch-heading" className="visually-hidden">
          Загрузка видео
        </h2>

        <nav className="platforms" aria-label="Платформы">
          {platforms.map((p) => {
            const classes = ["platform-tab"];
            if (!p.available) classes.push("platform-tab--disabled");
            if (detected?.id === p.id) classes.push("platform-tab--detected");
            if (p.available && detected?.id === p.id) classes.push("platform-tab--active");
            const dotClass = PLATFORM_COLORS[p.id]
              ? `platform-tab__dot--${PLATFORM_COLORS[p.id]}`
              : "";
            return (
              <span key={p.id} className={classes.join(" ")} data-platform={p.id}>
                <span className={`platform-tab__dot ${dotClass}`} />
                {p.name}
                {!p.available && <span className="platform-tab__badge">скоро</span>}
              </span>
            );
          })}
        </nav>

        <form className="fetch-form" onSubmit={onSubmit} noValidate>
          <label className="field">
            <span className="field__label">Ссылка на пост</span>
            <div className="field__row">
              <input
                className="field__input"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.tiktok.com/@user/video/... или https://vt.tiktok.com/..."
                autoComplete="off"
                spellCheck={false}
                required
                disabled={loading}
              />
              <button type="submit" className="btn btn--primary" disabled={loading || !url.trim()}>
                <span className="btn__text" hidden={loading}>
                  Получить данные
                </span>
                <span className="btn__spinner" hidden={!loading} aria-hidden="true" />
              </button>
            </div>
            <span className={`field__hint${hintError ? " field__hint--error" : ""}`}>{hint}</span>
          </label>

          {user?.role === "admin" && (
            <div className="options">
              <label className="toggle">
                <input
                  type="checkbox"
                  className="toggle__input"
                  checked={showBrowser}
                  onChange={(e) => setShowBrowser(e.target.checked)}
                  disabled={loading}
                />
                <span className="toggle__track" aria-hidden="true">
                  <span className="toggle__thumb" />
                </span>
                <span className="toggle__label">
                  <strong>Показывать браузер</strong>
                  <small>Открыть окно Chromium при загрузке (удобно для капчи)</small>
                </span>
              </label>
            </div>
          )}
        </form>
      </section>

      {loading && (
        <div className="status status--loading" role="status" aria-live="polite">
          {showBrowser
            ? "Загрузка… Откроется окно браузера, дождитесь завершения"
            : "Загрузка данных… Это может занять до минуты"}
        </div>
      )}

      {error && !loading && (
        <div className="status status--error" role="status" aria-live="polite">
          {error}
        </div>
      )}

      {result && !loading && analysisId && (
        <AnalysisToolbar
          analysisId={analysisId}
          isSaved={isSaved}
          onClose={handleClose}
          onSave={handleSave}
          onSaveAndClose={handleSaveAndClose}
          busy={toolbarBusy}
        />
      )}

      {result && !loading && <InspectorResults key={result.url} data={result} />}

      {!result && !loading && !error && (
        <section className="empty-state">
          <div className="empty-state__icon" aria-hidden="true">
            <svg viewBox="0 0 64 64" fill="none">
              <rect x="8" y="12" width="48" height="40" rx="6" stroke="currentColor" strokeWidth="2" />
              <path
                d="M26 28l6 6 12-12"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h2 className="empty-state__title">Вставьте ссылку на пост</h2>
          <p className="empty-state__text">
            Данные по видео, автору, метрикам и комментариям появятся здесь
          </p>
        </section>
      )}

      <footer className="footer">
        <span>Social Lead Monitor</span>
        <span className="footer__dot" aria-hidden="true">
          ·
        </span>
        <span>
          {availableCount} из {platforms.length} платформ доступно
        </span>
      </footer>
    </div>
  );
}
