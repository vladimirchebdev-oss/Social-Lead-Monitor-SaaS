import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";

export function LoginPage() {
  const [providers, setProviders] = useState<{ id: string; name: string }[]>([]);
  const [oauthBase, setOauthBase] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [params] = useSearchParams();

  useEffect(() => {
    if (params.get("error") === "oauth_state") {
      setError("Сессия OAuth истекла. Войдите снова (не обновляйте страницу callback).");
    }
  }, [params]);

  useEffect(() => {
    api
      .getProviders()
      .then((d) => {
        setProviders(d.providers);
        setOauthBase((d as { oauth_base_url?: string }).oauth_base_url ?? "");
      })
      .catch(() => setError("Не удалось загрузить провайдеры авторизации"));
  }, []);

  return (
    <div className="auth-page">
      <Link to="/" className="auth-page__back">
        ← На главную
      </Link>
      <div className="panel auth-card">
        <h1>Вход в кабинет</h1>
        <p className="text-muted">Войдите через Google</p>
        {error && <div className="alert alert--error">{error}</div>}
        <div className="auth-buttons">
          {providers.length === 0 && !error && (
            <p className="text-muted">Загрузка провайдеров…</p>
          )}
          {providers.map((p) => (
            <a
              key={p.id}
              href={`${oauthBase}/api/auth/${p.id}`}
              className={`btn btn--oauth btn--${p.id}`}
            >
              Войти через {p.name}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
