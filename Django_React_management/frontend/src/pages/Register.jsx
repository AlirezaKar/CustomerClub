import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, Link } from "react-router-dom";
import { register } from "../api";
import PasswordInput from "../components/PasswordInput";
import "./Register.css";

export default function Register() {
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
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
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
      await register(payload);
      setSuccess(true);
    } catch (err) {
      setError(err.message || t("register.failed"));
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="register-page">
        <div className="register-card register-card--success">
          <h1>{t("register.successTitle")}</h1>
          <p className="register-success-msg">{t("register.successMessage")}</p>
          <Link to="/login" className="register-login-btn">{t("register.signIn")}</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="register-page">
      <div className="register-card">
        <h1>{t("register.title")}</h1>
        <p className="register-subtitle">{t("register.subtitle")}</p>
        <form onSubmit={handleSubmit} className="register-form">
          <label>
            {t("register.username")}
            <input
              name="username"
              type="text"
              value={form.username}
              onChange={handleChange}
              required
              maxLength={150}
              autoComplete="username"
              placeholder={t("register.usernamePlaceholder")}
            />
          </label>
          <label>
            {t("register.password")}
            <PasswordInput
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              minLength={8}
              autoComplete="new-password"
              placeholder={t("password.placeholder")}
            />
          </label>
          <label>
            {t("register.phoneNumber")}
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
            {t("register.email")}
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
              placeholder={t("register.emailPlaceholder")}
            />
          </label>
          <label>
            {t("register.firstName")}
            <input
              name="first_name"
              type="text"
              value={form.first_name}
              onChange={handleChange}
              maxLength={150}
              placeholder={t("register.firstNamePlaceholder")}
            />
          </label>
          <label>
            {t("register.lastName")}
            <input
              name="last_name"
              type="text"
              value={form.last_name}
              onChange={handleChange}
              maxLength={150}
              placeholder={t("register.lastNamePlaceholder")}
            />
          </label>
          {error && <p className="register-error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? t("register.submitting") : t("register.submit")}
          </button>
        </form>
        <p className="register-login-link">
          {t("register.hasAccount")} <Link to="/login">{t("register.signIn")}</Link>
        </p>
      </div>
    </div>
  );
}
