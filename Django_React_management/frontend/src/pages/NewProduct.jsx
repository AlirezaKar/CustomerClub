import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, Link } from "react-router-dom";
import {
  isAuthenticated,
  fetchShops,
  fetchBranches,
  fetchCategories,
  createCategory,
  createProduct,
  createShop,
  createBranch,
  fetchProfile,
} from "../api";
import "./NewProduct.css";

export default function NewProduct() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [shops, setShops] = useState([]);
  const [branches, setBranches] = useState([]);
  const [totalBranchesInShop, setTotalBranchesInShop] = useState(0);
  const [categories, setCategories] = useState([]);
  const [shopId, setShopId] = useState("");
  const [newShopName, setNewShopName] = useState("");
  const [newBranchName, setNewBranchName] = useState("");
  const [creatingShop, setCreatingShop] = useState(false);
  const [creatingBranch, setCreatingBranch] = useState(false);
  const [newCategoryTitle, setNewCategoryTitle] = useState("");
  const [creatingCategory, setCreatingCategory] = useState(false);
  const [form, setForm] = useState({
    title: "",
    second_id: "",
    price: "",
    score: "",
    category: "",
    branch: "",
    is_active: true,
    image: null,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingShops, setLoadingShops] = useState(true);
  const [canCreateShop, setCanCreateShop] = useState(true);
  const [isOwnerCurrentShop, setIsOwnerCurrentShop] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login?next=/products/new", { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [data, profile] = await Promise.all([fetchShops(), fetchProfile()]);
        if (!cancelled) {
          setShops(data);
          setCanCreateShop(profile.can_create_shop !== false);
          if (profile.role === "branch_manager") {
            navigate("/products", { replace: true });
            return;
          }
          if (data.length && !shopId) setShopId(String(data[0].id));
        }
      } catch (e) {
        if (!cancelled) {
          setShops([]);
          setError(e.message || t("products.loadShopsFailed"));
        }
      } finally {
        if (!cancelled) setLoadingShops(false);
      }
    })();
    return () => { cancelled = true; };
  }, [navigate]);

  useEffect(() => {
    if (!shopId) {
      setCategories([]);
      setBranches([]);
      setTotalBranchesInShop(0);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [branchPayload, catData] = await Promise.all([
          fetchBranches(shopId),
          fetchCategories(shopId),
        ]);
        if (!cancelled) {
          setNewBranchName("");
          setBranches(branchPayload.branches);
          setTotalBranchesInShop(branchPayload.totalBranchesInShop);
          setCategories(catData);
          setForm((prev) => ({ ...prev, branch: "" }));
        }
      } catch (e) {
        if (!cancelled) {
          setBranches([]);
          setTotalBranchesInShop(0);
          setCategories([]);
          setError(e.message || t("products.loadBranchesFailed"));
        }
      }
    })();
    return () => { cancelled = true; };
  }, [shopId]);

  useEffect(() => {
    const row = shops.find((s) => String(s.id) === String(shopId));
    setIsOwnerCurrentShop(!!row?.is_owner);
  }, [shops, shopId]);

  async function handleCreateShop(e) {
    e.preventDefault();
    setError("");
    const name = newShopName.trim();
    if (!name) {
      setError(t("products.shopNameRequired"));
      return;
    }
    setCreatingShop(true);
    try {
      const shop = await createShop({ name });
      setNewShopName("");
      const data = await fetchShops();
      setShops(data);
      setShopId(String(shop.id));
    } catch (err) {
      setError(err.message || t("products.createShopFailed"));
    } finally {
      setCreatingShop(false);
    }
  }

  async function handleCreateBranch() {
    setError("");
    const name = newBranchName.trim();
    if (!shopId || !name) {
      setError(t("products.branchNameRequired"));
      return;
    }
    setCreatingBranch(true);
    try {
      const branch = await createBranch(shopId, { name });
      const payload = await fetchBranches(shopId);
      setBranches(payload.branches);
      setTotalBranchesInShop(payload.totalBranchesInShop);
      setForm((prev) => ({ ...prev, branch: String(branch.id) }));
      setNewBranchName("");
    } catch (err) {
      setError(err.message || t("products.createBranchFailed"));
    } finally {
      setCreatingBranch(false);
    }
  }

  async function handleCreateCategory() {
    setError("");
    const title = newCategoryTitle.trim();
    if (!shopId) {
      setError(t("products.selectShopFirst"));
      return;
    }
    if (!title) {
      setError(t("products.categoryTitleRequired"));
      return;
    }
    setCreatingCategory(true);
    try {
      const payload = { title };
      if (form.branch) {
        payload.branch = Number(form.branch);
      }
      const created = await createCategory(shopId, payload);
      const catData = await fetchCategories(shopId);
      setCategories(catData);
      setForm((prev) => ({ ...prev, category: String(created.id) }));
      setNewCategoryTitle("");
    } catch (err) {
      setError(err.message || t("products.createCategoryFailed"));
    } finally {
      setCreatingCategory(false);
    }
  }

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

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!shopId) {
      setError(t("products.selectShopFirst"));
      return;
    }
    if (!form.branch) {
      setError(t("products.selectBranchForProduct"));
      return;
    }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("shop", shopId);
      fd.append("branch", form.branch);
      fd.append("title", form.title);
      fd.append("second_id", form.second_id);
      fd.append("price", form.price);
      fd.append("score", form.score);
      fd.append("is_active", form.is_active);
      if (form.category) fd.append("category", form.category);
      if (form.image) fd.append("image", form.image);

      await createProduct(fd);
      navigate("/products");
    } catch (err) {
      setError(err.message || t("products.createFailed"));
    } finally {
      setLoading(false);
    }
  }

  if (loadingShops) {
    return (
      <div className="new-product-page">
        <p>{t("common.loading")}</p>
      </div>
    );
  }

  if (shops.length === 0) {
    return (
      <div className="new-product-page">
        <h1>{t("products.newProduct")}</h1>
        {canCreateShop ? (
          <>
            <p>{t("products.noShopsCreateFirst")}</p>
            <form onSubmit={handleCreateShop} className="new-product-form">
              <label>
                {t("products.newShopName")}
                <input
                  className="form-control"
                  type="text"
                  value={newShopName}
                  onChange={(e) => setNewShopName(e.target.value)}
                  maxLength={255}
                  disabled={creatingShop}
                />
              </label>
              <button type="submit" className="btn-primary" disabled={creatingShop}>
                {creatingShop ? t("common.saving") : t("products.createMyShop")}
              </button>
            </form>
          </>
        ) : (
          <p>{t("products.noShopAccess")}</p>
        )}
        {error && <p className="form-error">{error}</p>}
        <Link to="/products" className="btn-secondary">{t("products.backToProducts")}</Link>
      </div>
    );
  }

  return (
    <div className="new-product-page">
      <header className="new-product-header">
        <h1>{t("products.newProduct")}</h1>
        <Link to="/products" className="btn-secondary">{t("common.cancel")}</Link>
      </header>

      <form onSubmit={handleSubmit} className="new-product-form">
        <label>
          {t("products.shop")}
          <select
            className="form-control"
            value={shopId}
            onChange={(e) => setShopId(e.target.value)}
            required
          >
            {shops.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>
        {branches.length > 0 ? (
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
        ) : null}
        {(branches.length > 0 || totalBranchesInShop === 0) && isOwnerCurrentShop ? (
          <div className="new-product-branch-create">
            {branches.length === 0 && totalBranchesInShop === 0 ? (
              <span className="new-product-branch-create-label">{t("products.branch")}</span>
            ) : null}
            <input
              className="form-control"
              type="text"
              value={newBranchName}
              onChange={(e) => setNewBranchName(e.target.value)}
              placeholder={t("products.newBranchNamePlaceholder")}
              maxLength={255}
              disabled={creatingBranch}
            />
            <button type="button" className="btn-secondary" onClick={handleCreateBranch} disabled={creatingBranch}>
              {creatingBranch ? t("common.saving") : t("products.createBranch")}
            </button>
          </div>
        ) : null}
        {!isOwnerCurrentShop && (branches.length > 0 || totalBranchesInShop === 0) ? (
          <p className="muted">{t("products.onlyOwnerCreatesBranches")}</p>
        ) : null}
        {branches.length === 0 && totalBranchesInShop > 0 ? (
          <p className="form-error">{t("products.noBranchesForYou")}</p>
        ) : null}
        <label>
          {t("products.titleLabel")}
          <input
            className="form-control"
            name="title"
            value={form.title}
            onChange={handleChange}
            required
            maxLength={255}
            placeholder={t("products.placeholderTitle")}
          />
        </label>
        <label>
          {t("products.secondId")}
          <input
            className="form-control"
            name="second_id"
            type="number"
            min="1"
            value={form.second_id}
            onChange={handleChange}
            required
            placeholder={t("products.placeholderSecondId")}
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
            placeholder={t("products.placeholderPrice")}
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
            placeholder={t("products.placeholderScore")}
          />
        </label>
        <label>
          {t("products.categoryOptional")}
          <div className="new-product-category-row">
            <select className="form-control" name="category" value={form.category} onChange={handleChange}>
              <option value="">{t("common.none")}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
            <div className="new-product-category-add">
              <input
                className="form-control"
                type="text"
                value={newCategoryTitle}
                onChange={(e) => setNewCategoryTitle(e.target.value)}
                placeholder={t("products.newCategoryTitlePlaceholder")}
                maxLength={255}
                disabled={creatingCategory || !isOwnerCurrentShop}
              />
              <button
                type="button"
                className="btn-secondary"
                onClick={handleCreateCategory}
                disabled={creatingCategory || !isOwnerCurrentShop}
              >
                {creatingCategory ? t("common.saving") : t("products.createCategory")}
              </button>
            </div>
          </div>
        </label>
        <label>
          {t("products.imageOptional")}
          <input className="form-control form-control--file" type="file" accept="image/*" onChange={handleImageChange} />
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
        {error && <p className="form-error">{error}</p>}
        <div className="form-actions">
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? t("common.saving") : t("products.saveProduct")}
          </button>
          <Link to="/products" className="btn-secondary">{t("common.cancel")}</Link>
        </div>
      </form>
    </div>
  );
}
