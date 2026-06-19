import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const NAV = [
  { to: "/dashboard", label: "Кабинет" },
  { to: "/analyze", label: "Анализ" },
  { to: "/saved", label: "Сохранённые" },
  { to: "/billing", label: "Подписки" },
];

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header__row">
          <div className="header__brand">
            <div className="logo" aria-hidden="true">
              <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="32" height="32" rx="8" fill="url(#logo-grad)" />
                <path
                  d="M10 22V10l6 6 6-6v12"
                  stroke="#fff"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <defs>
                  <linearGradient id="logo-grad" x1="4" y1="4" x2="28" y2="28">
                    <stop stopColor="#6366f1" />
                    <stop offset="1" stopColor="#a855f7" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div>
              <h1 className="header__title">Social Lead Monitor</h1>
              <p className="header__subtitle">SaaS для анализа соцсетей</p>
            </div>
          </div>
          {user && (
            <div className="header__user">
              {user.avatar_url && (
                <img src={user.avatar_url} alt="" className="avatar avatar--sm" />
              )}
              <span className="header__email">{user.name ?? user.email}</span>
              <button type="button" className="btn btn--ghost btn--sm" onClick={handleLogout}>
                Выйти
              </button>
            </div>
          )}
        </div>
        <nav className="nav" aria-label="Основная навигация">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav__link${
                  isActive ||
                  (item.to === "/saved" && location.pathname.startsWith("/saved/"))
                    ? " nav__link--active"
                    : ""
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) => `nav__link${isActive ? " nav__link--active" : ""}`}
            >
              Админка
            </NavLink>
          )}
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

export function PublicLayout() {
  return (
    <div className="app app--public">
      <Outlet />
    </div>
  );
}
