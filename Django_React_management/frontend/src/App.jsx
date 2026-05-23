import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Routes, Route, Navigate, NavLink } from "react-router-dom";
import { isAuthenticated, logout, fetchProfile } from "./api";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ProductList from "./pages/ProductList";
import NewProduct from "./pages/NewProduct";
import ProductDetail from "./pages/ProductDetail";
import NewShopKeeper from "./pages/NewShopKeeper";
import Profile from "./pages/Profile";
import BranchPermissions from "./pages/BranchPermissions";
import "./App.css";

function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function sidebarNavClass({ isActive }) {
  return "app-sidebar-link" + (isActive ? " app-sidebar-link--active" : "");
}

function IconMoon() {
  return (
    <svg className="nav-theme-icon-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function IconSun() {
  return (
    <svg className="nav-theme-icon-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function IconSidebarSwap() {
  return (
    <svg className="app-sidebar-swap-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="4" width="7" height="16" rx="1" />
      <rect x="14" y="4" width="7" height="16" rx="1" />
      <path d="M10 9H8a2 2 0 0 0-2 2v2M14 15h2a2 2 0 0 0 2-2v-2" />
      <path d="M10 12h4" />
    </svg>
  );
}

function Layout({ children }) {
  const { t, i18n } = useTranslation();
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "light");
  const [sidebarEdge, setSidebarEdge] = useState(() => localStorage.getItem("sidebarEdge") || "left");
  const [sidebarProfileImage, setSidebarProfileImage] = useState(null);
  const [canCreateShopKeepers, setCanCreateShopKeepers] = useState(false);
  const isDark = theme === "dark";

  useEffect(() => {
    document.documentElement.lang = i18n.language;
    document.documentElement.dir = i18n.language === "fa" ? "rtl" : "ltr";
    document.title = "مدیریت باشگاه";
  }, [i18n.language]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("sidebarEdge", sidebarEdge);
  }, [sidebarEdge]);

  useEffect(() => {
    if (!isAuthenticated()) {
      setSidebarProfileImage(null);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const p = await fetchProfile();
        if (!cancelled) {
          setSidebarProfileImage(p.profile_picture_url || null);
          setCanCreateShopKeepers(!!p.can_create_shop_keepers);
        }
      } catch (_err) {
        if (!cancelled) setSidebarProfileImage(null);
      }
    })();
    function onProfileUpdated(ev) {
      const url = ev.detail && ev.detail.profile_picture_url;
      setSidebarProfileImage(url || null);
    }
    window.addEventListener("app-profile-updated", onProfileUpdated);
    return () => {
      cancelled = true;
      window.removeEventListener("app-profile-updated", onProfileUpdated);
    };
  }, []);

  return (
    <div className="app-layout" data-sidebar-edge={sidebarEdge}>
      <aside className="app-sidebar">
        <div className="app-sidebar__top">
          <button
            type="button"
            className="app-sidebar-dock-toggle"
            onClick={() => setSidebarEdge((e) => (e === "left" ? "right" : "left"))}
            title={t("nav.moveSidebar")}
            aria-label={t("nav.moveSidebar")}
          >
            <IconSidebarSwap />
          </button>
        </div>

        <nav className="app-sidebar__nav" aria-label={t("nav.mainNav")}>
          <NavLink
            to="/profile"
            end
            title={t("nav.profile")}
            aria-label={t("nav.profile")}
            className={(nav) => `${sidebarNavClass(nav)} app-sidebar-link--profile`}
          >
            {sidebarProfileImage ? (
              <img src={sidebarProfileImage} alt="" className="app-sidebar-profile-img" width={44} height={44} decoding="async" />
            ) : (
              <span className="app-sidebar-profile-placeholder" aria-hidden />
            )}
          </NavLink>
          {canCreateShopKeepers && (
            <NavLink to="/shop-keepers/new" end className={sidebarNavClass}>
              {t("nav.newShopKeeper")}
            </NavLink>
          )}
          <NavLink to="/products" className={sidebarNavClass}>
            {t("nav.products")}
          </NavLink>
          <NavLink to="/branch-permissions" end className={sidebarNavClass}>
            {t("nav.branchPermissions")}
          </NavLink>
        </nav>

        <div className="app-sidebar__spacer" />

        <div className="app-sidebar__bottom">
          <button
            type="button"
            className="nav-theme-circle"
            onClick={() => setTheme(isDark ? "light" : "dark")}
            title={isDark ? t("nav.lightMode") : t("nav.darkMode")}
            aria-label={isDark ? t("nav.lightMode") : t("nav.darkMode")}
          >
            {isDark ? <IconSun /> : <IconMoon />}
          </button>
          {isAuthenticated() && (
            <button
              type="button"
              className="nav-logout"
              onClick={() => {
                logout();
                window.location.href = "/login";
              }}
            >
              {t("nav.logout")}
            </button>
          )}
        </div>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/products"
          element={
            <ProtectedRoute>
              <Layout>
                <ProductList />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/products/:id"
          element={
            <ProtectedRoute>
              <Layout>
                <ProductDetail />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/products/new"
          element={
            <ProtectedRoute>
              <Layout>
                <NewProduct />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/branch-permissions"
          element={
            <ProtectedRoute>
              <Layout>
                <BranchPermissions />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/shop-keepers/new"
          element={
            <ProtectedRoute>
              <Layout>
                <NewShopKeeper />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Layout>
                <Profile />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/products" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
