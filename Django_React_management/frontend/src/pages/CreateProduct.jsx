import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  isAuthenticated,
  fetchShops,
  fetchBranches,
  fetchCategories,
  fetchProducts,
  createProduct,
  createShop,
  createBranch,
} from "../api";
import "./CreateProduct.css";

function getInitialShopAndBranch(searchParams) {
  const shop = searchParams.get("shop");
  const branch = searchParams.get("branch");
  return { shop: shop || "", branch: branch || "" };
}

export default function CreateProduct() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [shops, setShops] = useState([]);
  const [branches, setBranches] = useState([]);
  const [totalBranchesInShop, setTotalBranchesInShop] = useState(0);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [shopId, setShopId] = useState(() => getInitialShopAndBranch(searchParams).shop);
  const [newShopName, setNewShopName] = useState("");
  const [newBranchName, setNewBranchName] = useState("");
  const [creatingShop, setCreatingShop] = useState(false);
  const [creatingBranch, setCreatingBranch] = useState(false);
  const [form, setForm] = useState({
    title: "",
    second_id: "",
    price: "",
    score: "",
    category: "",
    branch: getInitialShopAndBranch(searchParams).branch,
    is_active: true,
    image: null,
  });
  const [initialBranchFromUrl, setInitialBranchFromUrl] = useState(
    () => getInitialShopAndBranch(searchParams).branch
  );
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingShops, setLoadingShops] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login?next=/products", { replace: true });
      return;
    }
    const { shop } = getInitialShopAndBranch(searchParams);
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchShops();
        if (!cancelled) {
          setShops(data);
          const initialShop = shop || (data.length ? String(data[0].id) : "");
          if (data.length && initialShop && !shopId) setShopId(initialShop);
        }
      } catch (e) {
        if (!cancelled) setError(e.message || t("branchPermissions.loadShopsFailed"));
      } finally {
        if (!cancelled) setLoadingShops(false);
      }
    })();
    return () => { cancelled = true; };
  }, [navigate, searchParams, shopId]);

  useEffect(() => {
    if (shopId && getInitialShopAndBranch(searchParams).shop !== shopId) {
      setInitialBranchFromUrl("");
    }
  }, [shopId, searchParams]);

  useEffect(() => {
    if (!shopId) {
      setBranches([]);
      setTotalBranchesInShop(0);
      setCategories([]);
      setProducts([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [branchPayload, cats, prods] = await Promise.all([
          fetchBranches(shopId),
          fetchCategories(shopId),
          fetchProducts(shopId),
        ]);
        if (!cancelled) {
          const branchList = branchPayload.branches;
          setNewBranchName("");
          setBranches(branchList);
          setTotalBranchesInShop(branchPayload.totalBranchesInShop);
          setCategories(cats);
          setProducts(prods);
          const branchFromUrl = initialBranchFromUrl;
          if (branchFromUrl && branchList.some((b) => String(b.id) === String(branchFromUrl))) {
            setForm((prev) => ({ ...prev, branch: branchFromUrl }));
            setInitialBranchFromUrl("");
          }
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

  async function handleCreateShop(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
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
    setSuccess("");
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
    setSuccess("");
    if (!shopId) {
      setError(t("products.selectShopFirst"));
      return;
    }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("shop", shopId);
      fd.append("title", form.title);
      fd.append("second_id", form.second_id);
      fd.append("price", form.price);
      fd.append("score", form.score);
      fd.append("is_active", form.is_active);
      if (form.category) fd.append("category", form.category);
      if (form.branch) fd.append("branch", form.branch);
      if (form.image) fd.append("image", form.image);

      await createProduct(fd);
      setSuccess(t("products.createSuccess"));
      setForm({
        title: "",
        second_id: "",
        price: "",
        score: "",
        category: "",
        branch: "",
        is_active: true,
        image: null,
      });
      const prods = await fetchProducts(shopId);
      setProducts(prods);
    } catch (err) {
      setError(err.message || t("products.createFailed"));
    } finally {
      setLoading(false);
    }
  }

  if (loadingShops) {
    return (
      <div className="create-product-page">
        <p>{t("common.loading")}</p>
      </div>
    );
  }

  if (shops.length === 0) {
    return (
      <div className="create-product-page">
        <p className="create-product-error">{t("products.noShops")}</p>
        <form onSubmit={handleCreateShop} className="product-form create-product-create-shop">
          <label>
            {t("products.newShopName")}
            <input
              type="text"
              value={newShopName}
              onChange={(e) => setNewShopName(e.target.value)}
              maxLength={255}
              disabled={creatingShop}
            />
          </label>
          <button type="submit" disabled={creatingShop}>
            {creatingShop ? t("common.saving") : t("products.createMyShop")}
          </button>
        </form>
        {error && <p className="form-error">{error}</p>}
      </div>
    );
  }

  return (
    <div className="create-product-page">
      <header className="create-product-header">
        <h1>{t("products.title")}</h1>
        <a href="/admin/" target="_blank" rel="noopener noreferrer" className="admin-link">
          {t("nav.admin")}
        </a>
      </header>

      <div className="create-product-layout">
        <section className="create-product-form-section">
          <h2>{t("products.addNewProduct")}</h2>
          <form onSubmit={handleSubmit} className="product-form">
            <label>
              {t("products.shop")}
              <select
                value={shopId}
                onChange={(e) => setShopId(e.target.value)}
                required
              >
                {shops.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            {branches.length > 0 ? (
              <label>
                {t("products.branchOptional")}
                <select
                  name="branch"
                  value={form.branch}
                  onChange={handleChange}
                >
                  <option value="">{t("products.shopLevelNoBranch")}</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {(branches.length > 0 || totalBranchesInShop === 0) ? (
              <div className="create-product-branch-create">
                {branches.length === 0 && totalBranchesInShop === 0 ? (
                  <span>{t("products.branchOptional")}</span>
                ) : null}
                <input
                  type="text"
                  value={newBranchName}
                  onChange={(e) => setNewBranchName(e.target.value)}
                  placeholder={t("products.newBranchNamePlaceholder")}
                  maxLength={255}
                  disabled={creatingBranch}
                />
                <button type="button" onClick={handleCreateBranch} disabled={creatingBranch}>
                  {creatingBranch ? t("common.saving") : t("products.createBranch")}
                </button>
              </div>
            ) : null}
            {branches.length === 0 && totalBranchesInShop > 0 ? (
              <p className="form-error">{t("products.noBranchesForYou")}</p>
            ) : null}
            <label>
              {t("products.titleLabel")}
              <input
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
              <select
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
              {t("products.imageOptional")}
              <input
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
            {error && <p className="form-error">{error}</p>}
            {success && <p className="form-success">{success}</p>}
            <button type="submit" disabled={loading}>
              {loading ? t("common.saving") : t("products.saveProduct")}
            </button>
          </form>
        </section>

        <section className="product-list-section">
          <h2>{t("products.productsInShop")}</h2>
          {products.length === 0 ? (
            <p className="muted">{t("products.noProductsYet")}</p>
          ) : (
            <ul className="product-list">
              {products.map((p) => (
                <li key={p.id} className={!p.is_active ? "product-list-item--unavailable" : ""}>
                  <span className="product-title">
                    {p.title}
                    {!p.is_active ? (
                      <span className="product-unavailable-badge">ناموجود</span>
                    ) : null}
                  </span>
                  <span className="product-meta">
                    {p.price} · {t("products.score")}: {p.score}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
