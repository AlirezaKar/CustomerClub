import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, Link } from "react-router-dom";
import { isAuthenticated, fetchProfile, updateProfile, changePassword } from "../api";
import PasswordInput from "../components/PasswordInput";
import "./Profile.css";

/** Default avatar when the user has no photo (served from ``frontend/public``). */
const PLACEHOLDER_AVATAR = "/unkown.png";

/** Must match backend ``PROFILE_PICTURE_MAX_UPLOAD_BYTES`` (2MB). */
const PROFILE_PICTURE_MAX_UPLOAD_BYTES = 2 * 1024 * 1024;

function IconTrash() {
  return (
    <svg className="profile-remove-picture-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14zM10 11v6M14 11v6" />
    </svg>
  );
}

function useGenders(t) {
  return [
    { value: "", label: t("profile.selectGender") },
    { value: "male", label: t("profile.male") },
    { value: "female", label: t("profile.female") },
  ];
}

export default function Profile() {
  const { t } = useTranslation();
  const GENDERS = useGenders(t);
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    username: "",
    phone_number: "",
    email: "",
    first_name: "",
    last_name: "",
    age: "",
    gender: "",
    card_uid: "",
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    new_password_confirm: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [removeProfilePicture, setRemoveProfilePicture] = useState(false);
  const [localPicturePreview, setLocalPicturePreview] = useState(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const pictureFileRef = useRef(null);

  useEffect(() => {
    return () => {
      if (localPicturePreview) URL.revokeObjectURL(localPicturePreview);
    };
  }, [localPicturePreview]);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login?next=/profile", { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchProfile();
        if (!cancelled) {
          setProfile(data);
          setRemoveProfilePicture(false);
          setForm({
            username: data.username || "",
            phone_number: data.phone_number || "",
            email: data.email || "",
            first_name: data.first_name || "",
            last_name: data.last_name || "",
            age: data.age != null ? String(data.age) : "",
            gender: data.gender || "",
            card_uid: data.card_uid || "",
          });
        }
      } catch (err) {
        if (!cancelled) setError(err.message || t("profile.loadFailed"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [navigate]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function handlePasswordChange(e) {
    const { name, value } = e.target;
    setPasswordForm((prev) => ({ ...prev, [name]: value }));
  }

  function onPictureFileChange(e) {
    const f = e.target.files && e.target.files[0];
    setError("");
    if (f) {
      if (f.size > PROFILE_PICTURE_MAX_UPLOAD_BYTES) {
        setError(t("profile.profilePictureTooLarge"));
        e.target.value = "";
        setLocalPicturePreview((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return null;
        });
        return;
      }
      const allowed = ["image/jpeg", "image/png", "image/webp", "image/gif"];
      if (f.type && !allowed.includes(f.type)) {
        setError(t("profile.profilePictureInvalidType"));
        e.target.value = "";
        return;
      }
    }
    setRemoveProfilePicture(false);
    setLocalPicturePreview((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return f ? URL.createObjectURL(f) : null;
    });
  }

  function toggleRemovePicture() {
    setRemoveProfilePicture((prev) => {
      const next = !prev;
      if (next) {
        setLocalPicturePreview((p) => {
          if (p) URL.revokeObjectURL(p);
          return null;
        });
        setFileInputKey((k) => k + 1);
      }
      return next;
    });
  }

  const previewSrc =
    localPicturePreview
    || (removeProfilePicture ? PLACEHOLDER_AVATAR : profile?.profile_picture_url)
    || PLACEHOLDER_AVATAR;

  const canToggleRemovePicture =
    Boolean(profile?.profile_picture_url) || Boolean(localPicturePreview) || removeProfilePicture;

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const payload = {
        username: form.username.trim(),
        phone_number: form.phone_number.trim(),
        email: form.email.trim() || undefined,
        first_name: form.first_name.trim() || undefined,
        last_name: form.last_name.trim() || undefined,
        gender: form.gender || undefined,
        card_uid: form.card_uid.trim() || undefined,
      };
      if (form.age !== "") payload.age = parseInt(form.age, 10) || null;

      const file = pictureFileRef.current && pictureFileRef.current.files && pictureFileRef.current.files[0];
      let updated;
      if (file) {
        const fd = new FormData();
        fd.append("username", payload.username);
        fd.append("phone_number", payload.phone_number);
        if (payload.email !== undefined) fd.append("email", payload.email);
        if (payload.first_name !== undefined) fd.append("first_name", payload.first_name);
        if (payload.last_name !== undefined) fd.append("last_name", payload.last_name);
        if (payload.age !== undefined && payload.age !== null) fd.append("age", String(payload.age));
        if (payload.gender !== undefined) fd.append("gender", payload.gender);
        if (payload.card_uid !== undefined) fd.append("card_uid", payload.card_uid);
        fd.append("profile_picture", file);
        updated = await updateProfile(fd);
      } else if (removeProfilePicture) {
        updated = await updateProfile({ ...payload, remove_profile_picture: true });
      } else {
        updated = await updateProfile(payload);
      }

      setProfile(updated);
      setSuccess(t("profile.updateSuccess"));
      setRemoveProfilePicture(false);
      setLocalPicturePreview((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
      setFileInputKey((k) => k + 1);
      if (pictureFileRef.current) pictureFileRef.current.value = "";
      window.dispatchEvent(new CustomEvent("app-profile-updated", { detail: updated }));
    } catch (err) {
      setError(err.message || t("profile.updateFailed"));
    } finally {
      setSaving(false);
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");
    if (passwordForm.new_password !== passwordForm.new_password_confirm) {
      setPasswordError(t("profile.passwordsNoMatch"));
      return;
    }
    setChangingPassword(true);
    try {
      await changePassword(passwordForm.current_password, passwordForm.new_password);
      setPasswordSuccess(t("profile.passwordSuccess"));
      setPasswordForm({ current_password: "", new_password: "", new_password_confirm: "" });
    } catch (err) {
      setPasswordError(err.message || t("profile.passwordFailed"));
    } finally {
      setChangingPassword(false);
    }
  }

  if (loading) {
    return (
      <div className="profile-page">
        <div className="profile-card"><p>{t("common.loading")}</p></div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-card">
        <h1>{t("profile.title")}</h1>
        <p className="profile-subtitle">{t("profile.subtitle")}</p>
        {profile != null && <p className="profile-score">{t("profile.score")}: {profile.score}</p>}

        {profile?.branches?.length > 0 && (
          <section className="profile-branches-section">
            <h2>{t("profile.yourBranches")}</h2>
            <ul className="profile-branches-list">
              {profile.branches.map((b) => (
                <li key={b.id} className="profile-branches-item">
                  <span className="profile-branches-name">{b.name}</span>
                  <span className="profile-branches-shop">{b.shop_name}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <form onSubmit={handleSubmit} className="profile-form">
          <div className="profile-picture-block">
            <img
              src={previewSrc}
              alt=""
              className={
                "profile-picture-preview"
                + (previewSrc === PLACEHOLDER_AVATAR && !localPicturePreview
                  ? " profile-picture-preview--placeholder"
                  : "")
              }
            />
            <div className="profile-picture-row">
              <label htmlFor="profile-picture-input">{t("profile.profilePicture")}</label>
              <input
                id="profile-picture-input"
                key={fileInputKey}
                ref={pictureFileRef}
                name="profile_picture"
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                onChange={onPictureFileChange}
              />
              <span className="profile-subtitle" style={{ margin: 0 }}>{t("profile.profilePictureHint")}</span>
            </div>
            <button
              type="button"
              className={
                "profile-remove-picture-btn"
                + (removeProfilePicture ? " profile-remove-picture-btn--active" : "")
              }
              disabled={!canToggleRemovePicture}
              aria-pressed={removeProfilePicture}
              title={t("profile.removeProfilePicture")}
              onClick={toggleRemovePicture}
            >
              <IconTrash />
              <span>{t("profile.removeProfilePicture")}</span>
            </button>
          </div>

          <label>{t("profile.username")}
            <input name="username" type="text" value={form.username} onChange={handleChange} required maxLength={150} autoComplete="username" placeholder={t("profile.usernamePlaceholder")} />
          </label>
          <label>{t("profile.phoneNumber")}
            <input name="phone_number" type="text" value={form.phone_number} onChange={handleChange} required maxLength={11} placeholder={t("register.phonePlaceholder")} />
          </label>
          <label>{t("profile.email")}
            <input name="email" type="email" value={form.email} onChange={handleChange} autoComplete="email" placeholder={t("profile.emailPlaceholder")} />
          </label>
          <label>{t("profile.firstName")}
            <input name="first_name" type="text" value={form.first_name} onChange={handleChange} maxLength={150} placeholder={t("profile.firstNamePlaceholder")} />
          </label>
          <label>{t("profile.lastName")}
            <input name="last_name" type="text" value={form.last_name} onChange={handleChange} maxLength={150} placeholder={t("profile.lastNamePlaceholder")} />
          </label>
          <label>{t("profile.age")}
            <input name="age" type="number" min="0" value={form.age} onChange={handleChange} placeholder={t("profile.agePlaceholder")} />
          </label>
          <label>{t("profile.gender")}
            <select name="gender" value={form.gender} onChange={handleChange}>
              {GENDERS.map((g) => <option key={g.value || "empty"} value={g.value}>{g.label}</option>)}
            </select>
          </label>
          <label>{t("profile.cardUid")}
            <input name="card_uid" type="text" value={form.card_uid} onChange={handleChange} maxLength={255} placeholder={t("profile.cardUidPlaceholder")} />
          </label>
          {error && <p className="profile-error">{error}</p>}
          {success && <p className="profile-success">{success}</p>}
          <button type="submit" disabled={saving} className="profile-submit">{saving ? t("common.saving") : t("profile.saveProfile")}</button>
        </form>

        <section className="profile-password-section">
          <h2>{t("profile.changePassword")}</h2>
          <form onSubmit={handlePasswordSubmit} className="profile-form">
            <label>{t("profile.currentPassword")}
              <PasswordInput name="current_password" value={passwordForm.current_password} onChange={handlePasswordChange} required autoComplete="current-password" placeholder={t("password.placeholderCurrent")} />
            </label>
            <label>{t("profile.newPassword")}
              <PasswordInput name="new_password" value={passwordForm.new_password} onChange={handlePasswordChange} required minLength={8} autoComplete="new-password" placeholder={t("password.placeholderNew")} />
            </label>
            <label>{t("profile.confirmNewPassword")}
              <PasswordInput name="new_password_confirm" value={passwordForm.new_password_confirm} onChange={handlePasswordChange} required minLength={8} autoComplete="new-password" placeholder={t("password.placeholderConfirm")} />
            </label>
            {passwordError && <p className="profile-error">{passwordError}</p>}
            {passwordSuccess && <p className="profile-success">{passwordSuccess}</p>}
            <button type="submit" disabled={changingPassword} className="profile-submit">{changingPassword ? t("profile.updating") : t("profile.changePassword")}</button>
          </form>
        </section>

        <p className="profile-back"><Link to="/products">{t("profile.backToProducts")}</Link></p>
      </div>
    </div>
  );
}
