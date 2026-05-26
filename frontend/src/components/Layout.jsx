import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useState } from "react";
import {
  LayoutDashboard, FolderOpen, LogOut,
  ChevronLeft, ChevronRight, Zap,
} from "lucide-react";
import "./Layout.css";

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  return (
    <div className="layout">
      <aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
        {/* Logo */}
        <div className="sidebar__logo">
          <div className="sidebar__logo-icon">
            <Zap size={18} />
          </div>
          {!collapsed && <span className="sidebar__logo-text">TestGen AI</span>}
        </div>

        {/* Nav */}
        <nav className="sidebar__nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `sidebar__link ${isActive ? "sidebar__link--active" : ""}`}
          >
            <LayoutDashboard size={18} />
            {!collapsed && <span>Дашборд</span>}
          </NavLink>

          {/* ИСПРАВЛЕНО: Ссылка ведет на главную (где список проектов), 
            но активна также, если мы находимся внутри любого проекта (/projects/...)
          */}
          <NavLink
            to="/"
            className={() => {
              const isProjectActive = location.pathname.startsWith("/projects");
              return `sidebar__link ${isProjectActive ? "sidebar__link--active" : ""}`;
            }}
          >
            <FolderOpen size={18} />
            {!collapsed && <span>Проекты</span>}
          </NavLink>
        </nav>

        {/* Bottom */}
        <div className="sidebar__bottom">
          <button
            className="sidebar__link sidebar__link--ghost"
            onClick={handleLogout}
          >
            <LogOut size={18} />
            {!collapsed && <span>Выйти</span>}
          </button>
          <button
            className="sidebar__collapse-btn"
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? "Развернуть" : "Свернуть"}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
      </aside>

      <main className="layout__main">
        <Outlet />
      </main>
    </div>
  );
}