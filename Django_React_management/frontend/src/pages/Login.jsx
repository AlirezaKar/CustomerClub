import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { login, checkShopOwner } from "../api";  // Single import combining both
import PasswordInput from "../components/PasswordInput";
import "./Login.css";

export default function Login() {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = searchParams.get("next") || "/products";

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);

      // Check if user has shops after successful login
      try {
        const { has_shop, owns_shop, default_products_shop_id } = await checkShopOwner();
        if (has_shop && !owns_shop && default_products_shop_id != null) {
          navigate(`/products?shop=${default_products_shop_id}`, { replace: true });
        } else if (!has_shop) {
          navigate("/profile", { replace: true });
        } else {
          navigate(next, { replace: true });
        }
      } catch {
        // If check fails, still navigate
        navigate(next, { replace: true });
      }
    } catch (err) {
      setError(err.message || t("login.failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>{t("login.title")}</h1>
        <p className="login-subtitle">{t("login.subtitle")}</p>
        <form onSubmit={handleSubmit} className="login-form">
          <label>
            {t("login.username")}
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              placeholder={t("login.usernamePlaceholder")}
            />
          </label>
          <label>
            {t("login.password")}
            <PasswordInput
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              placeholder={t("password.placeholder")}
            />
          </label>
          {error && <p className="login-error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? t("login.signingIn") : t("login.signIn")}
          </button>
        </form>
        <p className="login-register">
          {t("login.noAccount")} <Link to="/register">{t("login.register")}</Link>
        </p>
      </div>
    </div>
  );
}