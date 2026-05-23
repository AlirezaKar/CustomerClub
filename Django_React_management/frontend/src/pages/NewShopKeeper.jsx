import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, Link } from "react-router-dom";
import { isAuthenticated, createShopKeeper, fetchProfile, fetchShops } from "../api";
import "./NewShopKeeper.css";

export default function NewShopKeeper() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    password: "",
    phone_number: "",
    email: "",
    first_name: "",
    last_name: "",
  });
  const [shops, setShops] = useState([]);
  const [shopId, setShopId] = useState("");
  const [shopsLoading, setShopsLoading] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [accessResolved, setAccessResolved] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login?next=/shop-keepers/new", { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const p = await fetchProfile();
        if (cancelled) return;
        if (!p.can_create_shop_keepers) {
          navigate("/products", { replace: true });
          return;
        }
        try {
          const list = await fetchShops();
          if (cancelled) return;
          setShops(list);
          const owned = list.filter((s) => s.is_owner);
          const pickFrom = owned.length > 0 ? owned : list;
          if (pickFrom.length >= 1) {
            setShopId(String(pickFrom[0].id));
          }
        } catch {
          if (!cancelled) setShops([]);
        } finally {
          if (!cancelled) setShopsLoading(false);
        }
        setAccessResolved(true);
      } catch {
        if (!cancelled) navigate("/products", { replace: true });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  if (!isAuthenticated()) {
    return null;
  }

  if (!accessResolved || shopsLoading) {
    return (
      <div className="new-shop-keeper-page">
        <p className="new-shop-keeper-intro">{t("common.loading")}</p>
      </div>
    );
  }

  const ownedShops = shops.filter((s) => s.is_owner);
  const selectableShops = ownedShops.length > 0 ? ownedShops : shops;

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const payload = {
        username: form.username.trim(),
        password: form.password,
        phone_number: form.phone_number.trim(),
      };
      if (form.email.trim()) payload.email = form.email.trim();
      if (form.first_name.trim()) payload.first_name = form.first_name.trim();
      if (form.last_name.trim()) payload.last_name = form.last_name.trim();
      if (shopId) payload.shop = Number(shopId);
      await createShopKeeper(payload);
      setSuccess(t("shopKeeper.success"));
      setForm({
        username: "",
        password: "",
        phone_number: "",
        email: "",
        first_name: "",
        last_name: "",
      });
    } catch (err) {
      setError(err.message || t("shopKeeper.failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="new-shop-keeper-page">
      <header className="new-shop-keeper-header">
        <h1>{t("shopKeeper.title")}</h1>
        <Link to="/products" className="btn-secondary">{t("common.back")}</Link>
      </header>

      <p className="new-shop-keeper-intro">
        {t("shopKeeper.intro")}
      </p>

      {selectableShops.length > 1 ? (
        <label className="new-shop-keeper-shop-select">
          {t("shopKeeper.targetShop")}
          <select
            value={shopId}
            onChange={(e) => setShopId(e.target.value)}
            required
          >
            {selectableShops.map((s) => (
              <option key={s.id} value={String(s.id)}>{s.name}</option>
            ))}
          </select>
        </label>
      ) : null}

      <form onSubmit={handleSubmit} className="new-shop-keeper-form">
        <label>
          {t("shopKeeper.username")}
          <input
            name="username"
            type="text"
            value={form.username}
            onChange={handleChange}
            required
            maxLength={150}
            autoComplete="username"
            placeholder={t("shopKeeper.usernamePlaceholder")}
          />
        </label>
        <label>
          {t("shopKeeper.password")}
          <input
            name="password"
            type="password"
            value={form.password}
            onChange={handleChange}
            required
            minLength={8}
            autoComplete="new-password"
            placeholder={t("shopKeeper.passwordPlaceholder")}
          />
        </label>
        <label>
          {t("shopKeeper.phoneNumber")}
          <input
            name="phone_number"
            type="text"
            value={form.phone_number}
            onChange={handleChange}
            required
            maxLength={11}
            placeholder={t("register.phonePlaceholder")}
          />
        </label>
        <label>
          {t("shopKeeper.email")}
          <input
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
            placeholder={t("shopKeeper.emailPlaceholder")}
          />
        </label>
        <label>
          {t("shopKeeper.firstName")}
          <input
            name="first_name"
            type="text"
            value={form.first_name}
            onChange={handleChange}
            maxLength={150}
            placeholder={t("shopKeeper.firstNamePlaceholder")}
          />
        </label>
        <label>
          {t("shopKeeper.lastName")}
          <input
            name="last_name"
            type="text"
            value={form.last_name}
            onChange={handleChange}
            maxLength={150}
            placeholder={t("shopKeeper.lastNamePlaceholder")}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        {success && <p className="form-success">{success}</p>}
        <div className="form-actions">
          <button type="submit" disabled={loading} className="btn-submit">
            {loading ? t("shopKeeper.submitting") : t("shopKeeper.submit")}
          </button>
        </div>
      </form>
    </div>
  );
}
