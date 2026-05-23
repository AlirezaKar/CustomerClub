import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import {
  isAuthenticated,
  fetchProduct,
  fetchBranches,
  fetchCategories,
  updateProduct,
  updateProductOfferable,
  deleteProduct,
  resolveMediaUrl,
} from "../api";
import "./NewProduct.css";
import "./ProductList.css";

export default function ProductDetail() {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [branches, setBranches] = useState([]);
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    title: "",
    second_id: "",
    price: "",
    score: "",
    category: "",
    branch: "",
    is_active: true,
    is_offerable: false,
    image: null,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [canEdit, setCanEdit] = useState(false);
  const [canToggleOfferable, setCanToggleOfferable] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login", { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const prod = await fetchProduct(id);
        if (cancelled) return;
        setProduct(prod);
        setCanEdit(!!prod.can_edit);
        setCanToggleOfferable(!!prod.can_toggle_offerable);
        setForm({
          title: prod.title || "",
          second_id: String(prod.second_id ?? ""),
          price: String(prod.price ?? ""),
          score: String(prod.score ?? ""),
          category: prod.category ? String(prod.category) : "",
          branch: prod.branch ? String(prod.branch) : "",
          is_active: !!prod.is_active,
          is_offerable: !!prod.is_offerable,
          image: null,
        });
        const [branchPayload, catData] = await Promise.all([
          fetchBranches(prod.shop),
          fetchCategories(prod.shop),
        ]);
        if (cancelled) return;
        setBranches(branchPayload.branches);
        setCategories(catData);
      } catch (e) {
        if (!cancelled) {
          setError(e.message || t("products.loadFailed"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, navigate, t]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function handleImageChange(e) {
    const file = e.target.files?.[0];
    setForm((prev) => ({ ...prev, image: file || null }));
  }

  async function handleSaveOfferable() {
    if (!product) return;
    setError("");
    setSaving(true);
    try {
      const updated = await updateProductOfferable(id, form.is_offerable);
      setProduct(updated);
      setForm((prev) => ({ ...prev, is_offerable: !!updated.is_offerable }));
    } catch (e) {
      setError(e.message || t("products.saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!product || !canEdit) return;
    setError("");
    setSaving(true);
    try {
      const fd = new FormData();
      fd.append("title", form.title);
      fd.append("second_id", form.second_id);
      fd.append("price", form.price);
      fd.append("score", form.score);
      fd.append("is_active", form.is_active);
      fd.append("is_offerable", form.is_offerable);
      if (form.category) fd.append("category", form.category);
      if (form.branch) fd.append("branch", form.branch);
      if (form.image) fd.append("image", form.image);

      const updated = await updateProduct(id, fd);
      setProduct(updated);
      setForm((prev) => ({
        ...prev,
        image: null,
        is_offerable: !!updated.is_offerable,
      }));
    } catch (e) {
      setError(e.message || t("products.saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!product || !canEdit) return;
    if (!window.confirm(t("products.deleteConfirm"))) {
      return;
    }
    setDeleting(true);
    setError("");
    try {
      await deleteProduct(id);
      navigate("/products");
    } catch (e) {
      setError(e.message || t("products.deleteFailed"));
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="new-product-page">
        <p>{t("common.loading")}</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="new-product-page">
        <p className="form-error">{error || t("products.notFound")}</p>
      </div>
    );
  }

  const readOnlyDetail = (
    <>
      {product.image ? (
        <img
          className="product-detail-image"
          src={resolveMediaUrl(product.image)}
          alt=""
        />
      ) : null}
      <p>
        <strong>{t("products.shop")}:</strong> {product.shop_name}
      </p>
      <p>
        <strong>{t("products.branch")}:</strong> {product.branch_name || "—"}
      </p>
      <p>
        <strong>{t("products.titleLabel")}:</strong> {product.title}
      </p>
      <p>
        <strong>{t("products.price")}:</strong> {product.price}
      </p>
      <p>
        <strong>{t("products.score")}:</strong> {product.score}
      </p>
      <p>
        <strong>{t("products.categoryLabel")}:</strong>{" "}
        {product.category_title || t("common.none")}
      </p>
      <p>
        <strong>{t("common.active")}:</strong>{" "}
        {product.is_active ? t("common.yes") : t("common.no")}
      </p>
    </>
  );

  return (
    <div className="new-product-page">
      <header className="new-product-header">
        <h1>{t("products.productDetail")}</h1>
        <button
          type="button"
          onClick={() => navigate("/products")}
          className="btn-secondary"
        >
          {t("products.backToProducts")}
        </button>
      </header>

      {canEdit ? (
        <form onSubmit={handleSave} className="new-product-form">
          <p>
            <strong>{t("products.shop")}:</strong> {product.shop_name}
          </p>
          <label>
            {t("products.branch")}
            <select
              className="form-control"
              name="branch"
              value={form.branch || ""}
              onChange={handleChange}
              required
            >
              <option value="">{t("products.selectBranch")}</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("products.titleLabel")}
            <input
              className="form-control"
              name="title"
              value={form.title}
              onChange={handleChange}
              required
              maxLength={255}
            />
          </label>
          <label>
            {t("products.secondIdPerBranch")}
            <input
              className="form-control"
              name="second_id"
              type="number"
              min="1"
              value={form.second_id}
              onChange={handleChange}
              required
            />
          </label>
          <label>
            {t("products.price")}
            <input
              className="form-control"
              name="price"
              type="number"
              min="0"
              value={form.price}
              onChange={handleChange}
              required
            />
          </label>
          <label>
            {t("products.score")}
            <input
              className="form-control"
              name="score"
              type="number"
              min="0"
              value={form.score}
              onChange={handleChange}
              required
            />
          </label>
          <label>
            {t("products.categoryLabel")}
            <select
              className="form-control"
              name="category"
              value={form.category}
              onChange={handleChange}
            >
              <option value="">{t("common.none")}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("products.imageReplace")}
            <input
              className="form-control form-control--file"
              type="file"
              accept="image/*"
              onChange={handleImageChange}
            />
          </label>
          <label className="checkbox-label">
            <input
              name="is_active"
              type="checkbox"
              checked={form.is_active}
              onChange={handleChange}
            />
            {t("common.active")}
          </label>
          <label className="checkbox-label">
            <input
              name="is_offerable"
              type="checkbox"
              checked={form.is_offerable}
              onChange={handleChange}
            />
            {t("products.offerableLabel")}
          </label>
          {error && <p className="form-error">{error}</p>}
          <div className="form-actions">
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? t("common.saving") : t("products.saveChanges")}
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="btn-secondary"
            >
              {deleting ? t("products.deleting") : t("products.deleteProduct")}
            </button>
          </div>
        </form>
      ) : canToggleOfferable ? (
        <div className="new-product-form product-detail-offerable-only">
          <p className="muted">{t("products.branchManagerDetailHint")}</p>
          {readOnlyDetail}
          <div className="product-detail-offerable-action">
            <button
              type="button"
              className={`product-offerable-toggle product-offerable-toggle--detail${form.is_offerable ? " product-offerable-toggle--on" : ""}`}
              onClick={() =>
                setForm((prev) => ({ ...prev, is_offerable: !prev.is_offerable }))
              }
              aria-pressed={form.is_offerable}
            >
              {form.is_offerable ? "★" : "☆"}
            </button>
            <div>
              <strong>{t("products.offerableLabel")}</strong>
              <p className="muted product-detail-offerable-status">
                {form.is_offerable
                  ? t("products.offerableOn")
                  : t("products.offerableOff")}
              </p>
            </div>
          </div>
          {error && <p className="form-error">{error}</p>}
          <div className="form-actions">
            <button
              type="button"
              disabled={saving}
              className="btn-primary"
              onClick={handleSaveOfferable}
            >
              {saving ? t("common.saving") : t("products.saveOfferable")}
            </button>
          </div>
        </div>
      ) : (
        <div className="new-product-form">
          <p className="muted">{t("products.viewOnlyDetail")}</p>
          {readOnlyDetail}
          <p>
            <strong>{t("products.offerableLabel")}:</strong>{" "}
            {product.is_offerable ? t("products.offerableOn") : t("products.offerableOff")}
          </p>
        </div>
      )}
    </div>
  );
}
