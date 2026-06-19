import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type PlatformPlan } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function formatPrice(cents: number) {
  return `$${(cents / 100).toFixed(0)}`;
}

export function BillingPage() {
  const { subscriptions, refresh } = useAuth();
  const [plans, setPlans] = useState<PlatformPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [params] = useSearchParams();

  useEffect(() => {
    api
      .getPlans()
      .then((d) => setPlans(d.plans))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (params.get("success")) {
      refresh();
    }
  }, [params, refresh]);

  const isActive = (platform: string) =>
    subscriptions.some((s) => s.platform === platform && s.status === "active");

  const handleCheckout = async (platform: string, interval: "month" | "year") => {
    setBusy(`${platform}-${interval}`);
    setError(null);
    try {
      const { checkout_url } = await api.checkout(platform, interval);
      window.location.href = checkout_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка оплаты");
      setBusy(null);
    }
  };

  const handlePortal = async () => {
    setBusy("portal");
    try {
      const { portal_url } = await api.portal();
      window.location.href = portal_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Портал недоступен");
      setBusy(null);
    }
  };

  if (loading) return <div className="state state--loading">Загрузка тарифов…</div>;

  return (
    <div className="billing">
      <h2>Подписки</h2>
      <p className="text-muted">$15/мес или $150/год за каждую платформу</p>

      {params.get("success") && (
        <div className="alert alert--success">Оплата прошла успешно. Подписка активируется в течение минуты.</div>
      )}
      {params.get("canceled") && (
        <div className="alert alert--warning">Оплата отменена.</div>
      )}
      {error && <div className="alert alert--error">{error}</div>}

      <div className="pricing-grid">
        {plans.map((plan) => {
          const active = isActive(plan.platform);
          return (
            <article key={plan.platform} className={`pricing-card pricing-card--${plan.platform}`}>
              <div className="pricing-card__header">
                <h3>{plan.name}</h3>
                {!plan.available && <span className="badge badge--muted">Скоро</span>}
                {active && <span className="badge badge--success">Активна</span>}
              </div>
              <p className="pricing-card__price">
                <span className="pricing-card__amount">{formatPrice(plan.prices.month.amount_cents)}</span>
                <span className="pricing-card__period">/ мес</span>
              </p>
              <p className="pricing-card__year">
                {formatPrice(plan.prices.year.amount_cents)} / год
              </p>
              {!active && (
                <div className="pricing-card__actions">
                  <button
                    type="button"
                    className="btn btn--primary btn--block"
                    disabled={!!busy || !plan.prices.month.stripe_price_id}
                    onClick={() => handleCheckout(plan.platform, "month")}
                  >
                    {busy === `${plan.platform}-month` ? "…" : "Месяц"}
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--block"
                    disabled={!!busy || !plan.prices.year.stripe_price_id}
                    onClick={() => handleCheckout(plan.platform, "year")}
                  >
                    {busy === `${plan.platform}-year` ? "…" : "Год −17%"}
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>

      {subscriptions.length > 0 && (
        <button
          type="button"
          className="btn btn--ghost"
          disabled={!!busy}
          onClick={handlePortal}
        >
          {busy === "portal" ? "…" : "Управление оплатой в Stripe"}
        </button>
      )}
    </div>
  );
}
