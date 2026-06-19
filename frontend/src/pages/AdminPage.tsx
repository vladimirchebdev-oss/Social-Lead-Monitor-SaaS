import { useEffect, useState } from "react";
import { api, type AdminStats } from "../api/client";

function formatMoney(cents: number) {
  return `$${(cents / 100).toLocaleString("en-US", { minimumFractionDigits: 0 })}`;
}

export function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<
    {
      id: string;
      email: string;
      name: string | null;
      role: string;
      created_at: string;
      platforms: string[];
    }[]
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getAdminStats(), api.getAdminUsers()])
      .then(([s, u]) => {
        setStats(s);
        setUsers(u.users);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="state state--loading">Загрузка админки…</div>;
  if (error) return <div className="alert alert--error">{error}</div>;
  if (!stats) return null;

  return (
    <div className="admin">
      <h2>Админка — продажи</h2>

      <div className="stats-grid stats-grid--4">
        <div className="stat-card">
          <span className="stat-card__label">Пользователей</span>
          <span className="stat-card__value">{stats.users.total}</span>
          <span className="text-faint text-sm">+{stats.users.new_7d} за 7д</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">MRR</span>
          <span className="stat-card__value">{formatMoney(stats.subscriptions.mrr_cents)}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">ARR</span>
          <span className="stat-card__value">{formatMoney(stats.subscriptions.arr_cents)}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Выручка 30д</span>
          <span className="stat-card__value">{formatMoney(stats.revenue.last_30d_cents)}</span>
        </div>
      </div>

      <section className="panel">
        <h3>Активные подписки по платформам</h3>
        <div className="stats-grid">
          {Object.entries(stats.subscriptions.by_platform).map(([platform, count]) => (
            <div key={platform} className="stat-card">
              <span className="stat-card__label">{platform}</span>
              <span className="stat-card__value">{count}</span>
            </div>
          ))}
          {Object.keys(stats.subscriptions.by_platform).length === 0 && (
            <p className="text-muted">Нет активных подписок</p>
          )}
        </div>
        <p className="text-muted text-sm">
          Месячных: {stats.subscriptions.monthly_plans} · Годовых:{" "}
          {stats.subscriptions.yearly_plans}
        </p>
      </section>

      <div className="admin-grid">
        <section className="panel">
          <h3>Последние платежи</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Пользователь</th>
                <th>Сумма</th>
                <th>Событие</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_payments.map((p, i) => (
                <tr key={i}>
                  <td>{p.created_at ? new Date(p.created_at).toLocaleString("ru-RU") : "—"}</td>
                  <td>{p.user_email ?? "—"}</td>
                  <td>{p.amount_cents != null ? formatMoney(p.amount_cents) : "—"}</td>
                  <td>{p.event_type}</td>
                </tr>
              ))}
              {stats.recent_payments.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-muted">
                    Нет платежей
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <section className="panel">
          <h3>Последние подписки</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Пользователь</th>
                <th>Платформа</th>
                <th>План</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_subscriptions.map((s, i) => (
                <tr key={i}>
                  <td>{s.created_at ? new Date(s.created_at).toLocaleString("ru-RU") : "—"}</td>
                  <td>{s.user_email}</td>
                  <td>{s.platform}</td>
                  <td>
                    {s.billing_interval} · {s.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <section className="panel">
        <h3>Пользователи ({users.length})</h3>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Имя</th>
                <th>Роль</th>
                <th>Платформы</th>
                <th>Регистрация</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.name ?? "—"}</td>
                  <td>{u.role}</td>
                  <td>{u.platforms.join(", ") || "—"}</td>
                  <td>{new Date(u.created_at).toLocaleDateString("ru-RU")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
