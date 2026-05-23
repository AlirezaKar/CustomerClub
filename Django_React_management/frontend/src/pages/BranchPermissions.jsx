import { useEffect, useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { isAuthenticated, fetchShops, fetchBranchPermissions } from "../api";
import "./CreateProduct.css";
import "./BranchPermissions.css";

export default function BranchPermissions() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [shops, setShops] = useState([]);
  const [shopId, setShopId] = useState("");
  const [branches, setBranches] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [selectedUserBranchIds, setSelectedUserBranchIds] = useState(new Set());
  const [selectedUserIsHead, setSelectedUserIsHead] = useState(false);
  const [selectedUserIsShopManager, setSelectedUserIsShopManager] = useState(false);
  const [selectedUserRole, setSelectedUserRole] = useState("");
  const [assignAsShopManager, setAssignAsShopManager] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [canEditBranchPermissions, setCanEditBranchPermissions] = useState(true);
  const branchPermFetchId = useRef(0);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login?next=/branch-permissions", { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const shopList = await fetchShops();
        if (cancelled) return;
        setShops(shopList);
        if (shopList.length > 0) {
          setShopId(String(shopList[0].id));
        }
      } catch (e) {
        if (!cancelled) setError(e.message || t("branchPermissions.loadShopsFailed"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  useEffect(() => {
    if (!shopId) {
      setBranches([]);
      setUsers([]);
      setSelectedUserId("");
      setSelectedUserBranchIds(new Set());
      setSelectedUserIsHead(false);
      setSelectedUserIsShopManager(false);
      setSelectedUserRole("");
      setAssignAsShopManager(false);
      return;
    }
    const fetchId = ++branchPermFetchId.current;
    setBranches([]);
    setUsers([]);
    setSelectedUserId("");
    setSelectedUserBranchIds(new Set());
    setSelectedUserIsHead(false);
    setSelectedUserIsShopManager(false);
    setSelectedUserRole("");
    setAssignAsShopManager(false);
    setError("");
    setSuccess("");
    setCanEditBranchPermissions(true);
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchBranchPermissions(shopId);
        if (cancelled || fetchId !== branchPermFetchId.current) return;
        const userList = data.users || [];
        setBranches(data.branches || []);
        setUsers(userList);
        setCanEditBranchPermissions(data.can_edit_branch_permissions !== false);
        if (userList.length === 1) {
          const u = userList[0];
          setSelectedUserId(String(u.id));
          setSelectedUserIsHead(!!u.is_head_manager);
          setSelectedUserIsShopManager(!!u.is_shop_manager);
          setSelectedUserRole(u.role || "");
          setSelectedUserBranchIds(new Set((u.branches || []).map((b) => String(b.id))));
        }
      } catch (e) {
        if (cancelled || fetchId !== branchPermFetchId.current) return;
        setError(e.message || t("branchPermissions.loadFailed"));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [shopId]);

  function handleSelectUser(e) {
    const userId = e.target.value;
    setSelectedUserId(userId);
    setSuccess("");
    if (!userId) {
      setSelectedUserBranchIds(new Set());
      setSelectedUserIsHead(false);
      setSelectedUserIsShopManager(false);
      setSelectedUserRole("");
      setAssignAsShopManager(false);
      return;
    }
    const user = users.find((u) => String(u.id) === String(userId));
    if (!user) {
      setSelectedUserBranchIds(new Set());
      setSelectedUserIsHead(false);
      setSelectedUserIsShopManager(false);
      setSelectedUserRole("");
      setAssignAsShopManager(false);
      return;
    }
    setSelectedUserIsHead(!!user.is_head_manager);
    setSelectedUserIsShopManager(!!user.is_shop_manager);
    setSelectedUserRole(user.role || "");
    setAssignAsShopManager(false);
    const branchIds = new Set((user.branches || []).map((b) => String(b.id)));
    setSelectedUserBranchIds(branchIds);
  }

  function toggleBranch(branchId) {
    setSelectedUserBranchIds((prev) => {
      const next = new Set(prev);
      if (next.has(branchId)) next.delete(branchId);
      else next.add(branchId);
      return next;
    });
  }

  async function handleSave() {
    if (!canEditBranchPermissions || !shopId || !selectedUserId) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const wasAssigningOwner = assignAsShopManager;
      const res = await fetchBranchPermissions(shopId, {
        user_id: Number(selectedUserId),
        assign_as_shop_manager: assignAsShopManager,
        is_head_manager: assignAsShopManager ? false : selectedUserIsHead,
        branch_ids: assignAsShopManager
          ? []
          : Array.from(selectedUserBranchIds).map((id) => Number(id)),
      });
      const updatedUser = res.user ?? res;
      setUsers((prev) =>
        prev.map((u) => (u.id === updatedUser.id ? updatedUser : u)),
      );
      setSelectedUserIsShopManager(!!updatedUser.is_shop_manager);
      setAssignAsShopManager(false);
      setSuccess(
        wasAssigningOwner
          ? t("branchPermissions.shopManagerAssigned")
          : t("branchPermissions.updateSuccess"),
      );
    } catch (e) {
      setError(e.message || t("branchPermissions.saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="create-product-page branch-permissions-page">
        <p>{t("common.loading")}</p>
      </div>
    );
  }

  const canAssignShopManager =
    (selectedUserRole === "shop_manager" || selectedUserRole === "branch_manager") &&
    !selectedUserIsShopManager;
  const showBranchPermissions =
    selectedUserId &&
    selectedUserRole === "branch_manager" &&
    !assignAsShopManager &&
    !selectedUserIsShopManager;

  if (shops.length === 0) {
    return (
      <div className="create-product-page branch-permissions-page">
        <p className="create-product-error">
          {t("branchPermissions.noShops")}
        </p>
      </div>
    );
  }

  return (
    <div className="create-product-page branch-permissions-page">
      <header className="create-product-header">
        <h1>{t("branchPermissions.title")}</h1>
      </header>

      <div className="create-product-layout">
        <section className="create-product-form-section">
          <h2>{t("branchPermissions.manageAccess")}</h2>
          {!canEditBranchPermissions && (
            <p className="muted branch-permissions-readonly-notice">{t("branchPermissions.readOnlyHint")}</p>
          )}

          <div className="branch-permissions-dropdowns">
            <label className="branch-permissions-field">
              {t("branchPermissions.shop")}
              <select
                value={shopId}
                onChange={(e) => setShopId(e.target.value)}
              >
                {shops.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="branch-permissions-field">
              {t("branchPermissions.user")}
              <select value={selectedUserId} onChange={handleSelectUser} disabled={!canEditBranchPermissions}>
                <option value="">{t("branchPermissions.selectUser")}</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.username} ({u.phone_number})
                  </option>
                ))}
              </select>
            </label>
          </div>

          {selectedUserId && (
            <>
              {selectedUserIsShopManager && (
                <p className="muted branch-permissions-role-hint">
                  {t("branchPermissions.currentShopManager")}
                </p>
              )}

              {canAssignShopManager && (
                <label className="checkbox-label branch-permissions-checkbox-row">
                  <input
                    type="checkbox"
                    checked={assignAsShopManager}
                    onChange={(e) => setAssignAsShopManager(e.target.checked)}
                    disabled={!canEditBranchPermissions}
                  />
                  {t("branchPermissions.assignShopManager")}
                </label>
              )}

              {selectedUserRole === "branch_manager" && !assignAsShopManager && (
                <p className="muted branch-permissions-role-hint">
                  {t("branchPermissions.branchManagerHint")}
                </p>
              )}
              {selectedUserRole === "branch_manager" && assignAsShopManager && (
                <p className="muted branch-permissions-role-hint">
                  {t("branchPermissions.promoteToShopManagerHint")}
                </p>
              )}

              {showBranchPermissions && (
              <div className="branch-permissions-access">
                <label className="checkbox-label branch-permissions-checkbox-row">
                  <input
                    type="checkbox"
                    checked={selectedUserIsHead}
                    onChange={(e) => setSelectedUserIsHead(e.target.checked)}
                    disabled={!canEditBranchPermissions}
                  />
                  {t("branchPermissions.headManager")}
                </label>

                <div className="branch-permissions-list">
                  <p className="branch-permissions-list-heading">{t("branchPermissions.selectBranches")}</p>
                  {branches.length === 0 ? (
                    <p className="muted">{t("branchPermissions.noBranches")}</p>
                  ) : (
                    <ul className="branch-permissions-branch-ul">
                      {branches.map((b) => (
                        <li key={b.id} className="branch-permissions-branch-item">
                          <label className="checkbox-label branch-permissions-branch-label">
                            <input
                              type="checkbox"
                              checked={selectedUserBranchIds.has(String(b.id))}
                              onChange={() => toggleBranch(String(b.id))}
                              disabled={!canEditBranchPermissions}
                            />
                            {b.name}
                          </label>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              )}

              <div className="branch-permissions-footer">
                {error && <p className="form-error">{error}</p>}
                {success && <p className="form-success">{success}</p>}
                {canEditBranchPermissions && (
                  <button type="button" className="branch-permissions-save" onClick={handleSave} disabled={saving}>
                    {saving ? t("common.saving") : t("branchPermissions.savePermissions")}
                  </button>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

