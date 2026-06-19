import { Link } from "react-router-dom";

const PLANS = [
  { name: "TikTok", price: 15, color: "tiktok" },
  { name: "Threads", price: 15, color: "threads" },
];

export function LandingPage() {
  return (
    <div className="landing">
      <header className="landing__hero">
        <div className="logo logo--lg" aria-hidden="true">
          <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="url(#logo-grad-landing)" />
            <path
              d="M10 22V10l6 6 6-6v12"
              stroke="#fff"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <defs>
              <linearGradient id="logo-grad-landing" x1="4" y1="4" x2="28" y2="28">
                <stop stopColor="#6366f1" />
                <stop offset="1" stopColor="#a855f7" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1 className="landing__title">Social Lead Monitor</h1>
        <p className="landing__lead">
          Анализируйте посты из соцсетей, находите лиды в комментариях и отслеживайте метрики —
          безопасно через защищённый облачный сервис.
        </p>
        <div className="landing__actions">
          <Link to="/login" className="btn btn--primary btn--lg">
            Войти
          </Link>
          <a href="#pricing" className="btn btn--ghost btn--lg">
            Тарифы
          </a>
        </div>
      </header>

      <section id="pricing" className="panel landing__pricing">
        <h2>Тарифы</h2>
        <p className="text-muted">Оплата за каждую платформу отдельно</p>
        <div className="pricing-grid">
          {PLANS.map((p) => (
            <article key={p.name} className={`pricing-card pricing-card--${p.color}`}>
              <h3>{p.name}</h3>
              <p className="pricing-card__price">
                <span className="pricing-card__amount">${p.price}</span>
                <span className="pricing-card__period">/ месяц</span>
              </p>
              <p className="pricing-card__year">или $150 / год (−17%)</p>
              <ul className="pricing-card__features">
                <li>Анализ постов и комментариев</li>
                <li>Метрики и автор</li>
                <li>Защищённый API</li>
              </ul>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
