import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const PLATFORM_LABELS: Record<string, string> = {
  tiktok: "TikTok",
  threads: "Threads",
};

export function DashboardPage() {
  const { user, subscriptions, hasPlatform } = useAuth();

  return (
    <div className="dashboard">
      <h2>Добро пожаловать{user?.name ? `, ${user.name}` : ""}</h2>
      <p className="text-muted">Управляйте подписками и анализируйте посты из соцсетей.</p>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-card__label">Активных подписок</span>
          <span className="stat-card__value">{subscriptions.length}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Email</span>
          <span className="stat-card__value stat-card__value--sm">{user?.email}</span>
        </div>
      </div>

      <section className="panel">
        <h3>Ваши платформы</h3>
        <div className="platform-status-grid">
          {(["tiktok", "threads"] as const).map((id) => {
            const active = user?.role === "admin" || hasPlatform(id);
            const sub = subscriptions.find((s) => s.platform === id);
            return (
              <div key={id} className={`platform-status platform-status--${id}`}>
                <span className="platform-status__name">{PLATFORM_LABELS[id]}</span>
                <span className={`badge ${active ? "badge--success" : "badge--muted"}`}>
                  {active ? "Активна" : "Не подключена"}
                </span>
                {sub?.current_period_end && (
                  <span className="text-faint text-sm">
                    до {new Date(sub.current_period_end).toLocaleDateString("ru-RU")}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        <div className="dashboard__actions">
          <Link to="/billing" className="btn btn--primary">
            Управлять подписками
          </Link>
          <Link to="/analyze" className="btn btn--ghost">
            Анализ поста
          </Link>
        </div>
      </section>
    </div>
  );
}
