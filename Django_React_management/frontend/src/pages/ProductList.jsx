import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  isAuthenticated,
  fetchShops,
  fetchBranches,
  fetchProducts,
  createShop,
  createBranch,
  resolveMediaUrl,
  fetchProfile,
  updateProductOfferable,
} from "../api";
import "./ProductList.css";

export default function ProductList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [shops, setShops] = useState([]);
  const [branches, setBranches] = useState([]);
  const [totalBranchesInShop, setTotalBranchesInShop] = useState(0);
  const [canCreateBranches, setCanCreateBranches] = useState(false);
  const [products, setProducts] = useState([]);
  const [shopId, setShopId] = useState("");
  const [branchId, setBranchId] = useState("");
  const [loading, setLoading] = useState(true);
  const [newShopName, setNewShopName] = useState("");
  const [newBranchName, setNewBranchName] = useState("");
  const [creatingShop, setCreatingShop] = useState(false);
  const [creatingBranch, setCreatingBranch] = useState(false);
  const [listError, setListError] = useState("");
  const [canCreateShop, setCanCreateShop] = useState(true);
  const [userRole, setUserRole] = useState("");
  const [togglingOfferId, setTogglingOfferId] = useState(null);
  const branchesFetchId = useRef(0);
  const productsFetchId = useRef(0);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login?next=/products", { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [data, profile] = await Promise.all([fetchShops(), fetchProfile()]);
        if (!cancelled) {
          setListError("");
          setShops(data);
          setCanCreateShop(profile.can_create_shop !== false);
          setUserRole(profile.role || "");
          const fromUrl = searchParams.get("shop");
          if (fromUrl && data.some((s) => String(s.id) === String(fromUrl))) {
            setShopId(String(fromUrl));
          } else if (data.length) {
            setShopId((prev) =>
              prev && data.some((s) => String(s.id) === String(prev))
                ? String(prev)
                : String(data[0].id)
            );
          }
        }
      } catch (e) {
        if (!cancelled) {
          setShops([]);
          setListError(e.message || t("products.loadShopsFailed"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [navigate, searchParams]);

  useEffect(() => {
    if (!shopId) {
      setBranches([]);
      setTotalBranchesInShop(0);
      setBranchId("");
      return;
    }
    const fetchId = ++branchesFetchId.current;
    setBranches([]);
    setTotalBranchesInShop(0);
    setBranchId("");
    let cancelled = false;
    (async () => {
      try {
        const { branches: list, totalBranchesInShop: total, can_create_branches: canCreate } =
          await fetchBranches(shopId);
        if (cancelled || fetchId !== branchesFetchId.current) return;
        setNewBranchName("");
        setBranches(list);
        setTotalBranchesInShop(total);
        setCanCreateBranches(!!canCreate);
        setListError("");
      } catch (e) {
        if (cancelled || fetchId !== branchesFetchId.current) return;
        setBranches([]);
        setTotalBranchesInShop(0);
        setListError(e.message || t("products.loadBranchesFailed"));
      }
    })();
    return () => { cancelled = true; };
  }, [shopId]);

  useEffect(() => {
    if (!shopId) {
      setProducts([]);
      return;
    }
    const fetchId = ++productsFetchId.current;
    setProducts([]);
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchProducts(shopId, branchId || null);
        if (cancelled || fetchId !== productsFetchId.current) return;
        setProducts(data);
      } catch (e) {
        if (cancelled || fetchId !== productsFetchId.current) return;
        setProducts([]);
        setListError(e.message || t("products.loadProductsFailed"));
      }
    })();
    return () => { cancelled = true; };
  }, [shopId, branchId]);

  async function handleCreateShop(e) {
    e.preventDefault();
    setListError("");
    const name = newShopName.trim();
    if (!name) {
      setListError(t("products.shopNameRequired"));
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
      setListError(err.message || t("products.createShopFailed"));
    } finally {
      setCreatingShop(false);
    }
  }

  const isBranchManager = userRole === "branch_manager";
  const canAddProduct = !isBranchManager;

  async function handleToggleOfferable(product, e) {
    e.preventDefault();
    e.stopPropagation();
    if (!product.can_toggle_offerable) return;
    setListError("");
    setTogglingOfferId(product.id);
    try {
      const updated = await updateProductOfferable(product.id, !product.is_offerable);
      setProducts((prev) =>
        prev.map((p) => (p.id === product.id ? { ...p, ...updated } : p))
      );
    } catch (err) {
      setListError(err.message || t("products.offerableToggleFailed"));
    } finally {
      setTogglingOfferId(null);
    }
  }

  async function handleCreateBranch(e) {
    e.preventDefault();
    setListError("");
    const name = newBranchName.trim();
    if (!shopId || !name) {
      setListError(t("products.branchNameRequired"));
      return;
    }
    setCreatingBranch(true);
    try {
      await createBranch(shopId, { name });
      setNewBranchName("");
      const { branches: list, totalBranchesInShop: total } = await fetchBranches(shopId);
      setBranches(list);
      setTotalBranchesInShop(total);
    } catch (err) {
      setListError(err.message || t("products.createBranchFailed"));
    } finally {
      setCreatingBranch(false);
    }
  }

  if (loading) {
    return (
      <div className="product-list-page product-list-page--plain">
        <p className="product-list-loading">{t("common.loading")}</p>
      </div>
    );
  }

  if (shops.length === 0) {
    return (
      <div className="product-list-page product-list-page--plain">
        <div className="product-list-hero">
          <h1 className="product-list-title-main">{t("products.title")}</h1>
        </div>
        <p className="product-list-empty-msg product-list-empty-msg--center">
          {canCreateShop ? t("products.noShops") : t("products.noShopAccess")}
        </p>
        {canCreateShop ? (
          <form className="product-list-create-form" onSubmit={handleCreateShop}>
            <label className="product-list-select-label">
              {t("products.newShopName")}
              <input
                type="text"
                className="product-list-shop-select"
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
        ) : null}
        {listError ? <p className="product-list-toolbar-error">{listError}</p> : null}
      </div>
    );
  }

  return (
    <div className="product-list-page product-list-page--plain">
      <div className="product-list-hero">
        <h1 className="product-list-title-main">{t("products.title")}</h1>
        {canAddProduct ? (
          <Link
            to={
              branchId
                ? `/products/new?shop=${shopId}&branch=${branchId}`
                : `/products/new?shop=${shopId}`
            }
            className="btn-primary product-list-add-btn"
          >
            {t("products.addProduct")}
          </Link>
        ) : null}
      </div>

      <div className="product-list-toolbar">
        <label className="product-list-select-label">
          {t("products.branch")}
          <div className="product-list-branch-controls">
            {branches.length > 0 ? (
              <select
                value={branchId}
                onChange={(e) => setBranchId(e.target.value)}
                className="product-list-shop-select"
              >
                <option value="">{t("products.allBranches")}</option>
                {branches.map((b) => (
                  <option key={b.id} value={String(b.id)}>{b.name}</option>
                ))}
              </select>
            ) : null}
            {branches.length > 0 || totalBranchesInShop === 0 ? (
              canCreateBranches ? (
              <form className="product-list-inline-branch-create" onSubmit={handleCreateBranch}>
                <input
                  type="text"
                  className="product-list-shop-select"
                  value={newBranchName}
                  onChange={(e) => setNewBranchName(e.target.value)}
                  placeholder={t("products.newBranchNamePlaceholder")}
                  maxLength={255}
                  disabled={creatingBranch}
                />
                <button type="submit" className="btn-primary" disabled={creatingBranch}>
                  {creatingBranch ? t("common.saving") : t("products.createBranch")}
                </button>
              </form>
              ) : (
                <span className="product-list-muted-inline">{t("products.onlyOwnerCreatesBranches")}</span>
              )
            ) : (
              <span className="product-list-muted-inline">{t("products.noBranchesForYou")}</span>
            )}
          </div>
        </label>
        <label className="product-list-select-label">
          {t("products.shop")}
          <select
            value={shopId}
            onChange={(e) => setShopId(e.target.value)}
            className="product-list-shop-select"
          >
            {shops.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>
      </div>
      {listError ? <p className="product-list-toolbar-error">{listError}</p> : null}

      {products.length === 0 ? (
        <div className="product-list-empty-state">
          <p className="product-list-empty">
            {branchId ? t("products.noProductsInBranch") : t("products.noProductsInShop")}
          </p>
        </div>
      ) : (
        <>
          {branchId && branches.length > 0 && (
            <p className="product-list-branch-context">
              {t("products.showingIn")}{" "}
              <strong>{branches.find((b) => String(b.id) === branchId)?.name ?? t("products.thisBranch")}</strong>
            </p>
          )}
          <ul className="product-list-grid">
            {products.map((p) => (
              <li
                key={p.id}
                className={`product-list-card${!p.is_active ? " product-list-card--unavailable" : ""}`}
              >
                {!p.is_active ? (
                  <span className="product-unavailable-badge">ناموجود</span>
                ) : null}
                {p.image ? (
                  <img
                    className="product-list-card-thumb"
                    src={resolveMediaUrl(p.image)}
                    alt=""
                    loading="lazy"
                  />
                ) : null}
                <div className="product-list-card-title-row">
                  {p.can_toggle_offerable && (
                    <button
                      type="button"
                      className={`product-offerable-toggle${p.is_offerable ? " product-offerable-toggle--on" : ""}`}
                      onClick={(e) => handleToggleOfferable(p, e)}
                      disabled={togglingOfferId === p.id || !p.can_toggle_offerable}
                      title={
                        p.is_offerable
                          ? t("products.offerableOn")
                          : t("products.offerableOff")
                      }
                      aria-pressed={!!p.is_offerable}
                      aria-label={
                        p.is_offerable
                          ? t("products.offerableOn")
                          : t("products.offerableOff")
                      }
                    >
                      {togglingOfferId === p.id ? "…" : p.is_offerable ? "★" : "☆"}
                    </button>
                  )}
                  <span className="product-list-card-title">
                    <Link to={`/products/${p.id}`}>{p.title}</Link>
                  </span>
                </div>
                <span className="product-list-card-meta">
                  {t("products.price")}: {p.price}
                  <br />
                  {t("products.score")}: {p.score}
                  {p.branch
                    ? ` · ${branches.find((b) => b.id === p.branch)?.name ?? t("products.branch")}`
                    : ` · ${t("products.shopLevel")}`}
                  {p.is_offerable && ` · ${t("products.offerableShort")}`}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
