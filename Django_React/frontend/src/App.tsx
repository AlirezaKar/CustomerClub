import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchCategories,
  fetchPublicShops,
  nfcCompleteLogin,
  SmsSendLimitError,
  sendLoginCode,
  signupUser,
  submitOfferUse,
  verifyLoginCode,
} from "./api";
import { type AuthSession } from "./api";
import type { CartLine, Category, Gender, ShopOption, UserProfile } from "./types";
import {
  clearSelectedShopId,
  getSelectedShopId,
  setSelectedShopId,
} from "./shopSession";
import { resolveProductImageUrl } from "./media";
import NFCAuth from "./NFCAuth";
import NFCLoginScan from "./NFCLoginScan";
import NFCRegistrationScan from "./NFCRegistrationScan";
import { applyAuthSession, clearTokens, getAccessToken } from "./auth";

type Screen =
  | "landing"
  | "register"
  | "login"
  | "verify"
  | "nfcSettings"
  | "products"
  | "finalize";

type KeypadTarget = "phone" | "age" | "code";

const TAX_RATE = 0.09;
const CHECKOUT_TIMEOUT_SECONDS = 10;
const SMS_CODE_LIFE_SECONDS = Number(
  import.meta.env.VITE_SMS_CODE_LIFE_SECONDS ?? "300",
);
const SMS_SEND_LIMIT_SECONDS = Number(
  import.meta.env.VITE_SMS_SEND_LIMIT_SECONDS ?? "120",
);

const CUSTOMER_CLUB_BRAND = "باشگاه مشتریان";

function formatBrandTitle(shopName?: string | null): string {
  const name = shopName?.trim();
  return name ? `${name} | ${CUSTOMER_CLUB_BRAND}` : CUSTOMER_CLUB_BRAND;
}

function formatPrice(price: number): string {
  return `${price.toLocaleString("en-US")} تومن`;
}

function formatReceiptPrice(price: number): string {
  return `${price.toLocaleString("en-US")} تومان`;
}

function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (!digits) return "";
  if (digits.length <= 7) return digits;
  return `${digits.slice(0, 4)}***${digits.slice(-3)}`;
}

function asciiSafe(value: string): string {
  return value.replace(/[^\x20-\x7E]/g, "?");
}

function NumericKeypad({
  onDigit,
  onBackspace,
  onConfirm,
  confirmLabel,
  disabled,
}: {
  onDigit: (digit: string) => void;
  onBackspace: () => void;
  onConfirm: () => void;
  confirmLabel: string;
  disabled?: boolean;
}) {
  const digits: Array<{ value: string; label: string }> = [
    { value: "1", label: "۱" },
    { value: "2", label: "۲" },
    { value: "3", label: "۳" },
    { value: "4", label: "۴" },
    { value: "5", label: "۵" },
    { value: "6", label: "۶" },
    { value: "7", label: "۷" },
    { value: "8", label: "۸" },
    { value: "9", label: "۹" },
  ];

  return (
    <aside className="keypad">
      {digits.map((digit) => (
        <button
          key={digit.value}
          className="keypad-btn"
          type="button"
          onClick={() => onDigit(digit.value)}
          disabled={disabled}
        >
          {digit.label}
        </button>
      ))}
      <button
        className="keypad-btn keypad-secondary"
        type="button"
        onClick={onBackspace}
        disabled={disabled}
        aria-label="backspace"
      >
        ⌫
      </button>
      <button
        className="keypad-btn"
        type="button"
        onClick={() => onDigit("0")}
        disabled={disabled}
      >
        ۰
      </button>
      <button
        className="keypad-btn keypad-confirm"
        type="button"
        onClick={onConfirm}
        disabled={disabled}
        aria-label={confirmLabel}
      >
        {confirmLabel === "..." ? (
          "..."
        ) : (
          <>
            <span className="keypad-confirm-icon">تایید</span>
            <span className="sr-only">{confirmLabel}</span>
          </>
        )}
      </button>
    </aside>
  );
}

function App() {
  const [screen, setScreen] = useState<Screen>("landing");
  const [activeTarget, setActiveTarget] = useState<KeypadTarget>("phone");
  const [loading, setLoading] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [successText, setSuccessText] = useState("");

  const [registerPhone, setRegisterPhone] = useState("");
  const [registerAge, setRegisterAge] = useState("");
  const [registerGender, setRegisterGender] = useState<Gender>("male");
  const [registerCardUid, setRegisterCardUid] = useState("");

  const [shops, setShops] = useState<ShopOption[]>([]);
  const [selectedShopId, setSelectedShopIdState] = useState<number | null>(
    () => getSelectedShopId(),
  );
  const [shopsLoading, setShopsLoading] = useState(false);

  const [loginPhone, setLoginPhone] = useState("");
  // Legacy manual UID input removed in favor of scanner-based NFC login.

  const [smsCode, setSmsCode] = useState("");
  const [smsLifeLeft, setSmsLifeLeft] = useState(SMS_CODE_LIFE_SECONDS);
  const [smsResendLeft, setSmsResendLeft] = useState(0);
  const [smsExpiresAt, setSmsExpiresAt] = useState<number | null>(null);
  const [smsResendAt, setSmsResendAt] = useState<number | null>(null);

  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(
    null,
  );
  const [user, setUser] = useState<UserProfile | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(
    getAccessToken(),
  );
  const [cart, setCart] = useState<Record<string, CartLine>>({});

  const [checkoutCountdown, setCheckoutCountdown] = useState(
    CHECKOUT_TIMEOUT_SECONDS,
  );
  const errorBannerRef = useRef<HTMLParagraphElement>(null);
  const productsNoticeRef = useRef<HTMLParagraphElement>(null);

  const selectedShop = useMemo(
    () => shops.find((shop) => shop.id === selectedShopId) ?? null,
    [shops, selectedShopId],
  );

  const shopBrandName = selectedShop?.name ?? CUSTOMER_CLUB_BRAND;
  const brandTitle = useMemo(
    () => formatBrandTitle(selectedShop?.name),
    [selectedShop?.name],
  );

  useEffect(() => {
    document.title = brandTitle;
  }, [brandTitle]);

  useEffect(() => {
    if (screen !== "login") {
      setSuccessText("");
    }
  }, [screen]);

  useEffect(() => {
    if (!errorText) return;
    const frame = requestAnimationFrame(() => {
      const target =
        screen === "products"
          ? productsNoticeRef.current
          : errorBannerRef.current;
      target?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [errorText, screen]);

  function selectShop(shopId: number) {
    setSelectedShopIdState(shopId);
    setSelectedShopId(shopId);
  }

  function requireSelectedShop(): number | null {
    if (selectedShopId) return selectedShopId;
    setErrorText("لطفاً ابتدا فروشگاه را انتخاب کنید.");
    return null;
  }

  useEffect(() => {
    let cancelled = false;
    setShopsLoading(true);
    void fetchPublicShops()
      .then((data) => {
        if (cancelled) return;
        setShops(data);
        if (data.length === 1) {
          selectShop(data[0].id);
        } else if (selectedShopId && !data.some((s) => s.id === selectedShopId)) {
          setSelectedShopIdState(null);
          clearSelectedShopId();
        }
      })
      .catch(() => {
        if (!cancelled && screen === "landing") {
          setErrorText("بارگذاری فهرست فروشگاه‌ها ناموفق بود.");
        }
      })
      .finally(() => {
        if (!cancelled) setShopsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function resetSmsSession() {
    setSmsCode("");
    setSmsLifeLeft(SMS_CODE_LIFE_SECONDS);
    setSmsResendLeft(0);
    setSmsExpiresAt(null);
    setSmsResendAt(null);
    setErrorText("");
  }

  // On load: if URL has ?nfc_token=... (from NFC bridge), exchange for user and go to products
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const nfcToken = params.get("nfc_token");
    if (!nfcToken) return;
    const shopId = getSelectedShopId();
    if (!shopId) {
      setErrorText("لطفاً ابتدا فروشگاه را انتخاب کنید، سپس ورود NFC را انجام دهید.");
      return;
    }
    (async () => {
      try {
        const userProfile = await nfcCompleteLogin(nfcToken, shopId);
        setUser(userProfile);
        await loadCatalog(shopId);
        setScreen("products");
        setErrorText("");
        window.history.replaceState({}, "", window.location.pathname || "/");
      } catch {
        setErrorText("ورود با NFC ناموفق یا منقضی شده است.");
      }
    })();
  }, []);

  useEffect(() => {
    if (screen !== "verify") return;
    const timer = setInterval(() => {
      const now = Date.now();
      const lifeRemaining = smsExpiresAt
        ? Math.max(0, Math.ceil((smsExpiresAt - now) / 1000))
        : SMS_CODE_LIFE_SECONDS;
      const resendRemaining = smsResendAt
        ? Math.max(0, Math.ceil((smsResendAt - now) / 1000))
        : 0;
      setSmsLifeLeft(lifeRemaining);
      setSmsResendLeft(resendRemaining);
      if (lifeRemaining === 0) {
        setErrorText("کد پیامکی منقضی شده است. لطفاً مجدد درخواست پیامک کنید.");
      }
    }, 250);
    return () => clearInterval(timer);
  }, [screen, smsExpiresAt, smsResendAt]);

  useEffect(() => {
    if (screen !== "finalize") return;
    setCheckoutCountdown(CHECKOUT_TIMEOUT_SECONDS);
    const timer = setInterval(() => {
      setCheckoutCountdown((current) => {
        if (current <= 1) {
          resetFlow();
          return CHECKOUT_TIMEOUT_SECONDS;
        }
        return current - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [screen]);

  const currentCategory = useMemo(
    () =>
      categories.find((category) => category.id === selectedCategoryId) ??
      categories[0],
    [categories, selectedCategoryId],
  );

  const cartLines = useMemo(() => Object.values(cart), [cart]);
  const selectedItemsCount = useMemo(
    () => cartLines.reduce((sum, line) => sum + line.quantity, 0),
    [cartLines],
  );
  const subtotal = useMemo(
    () =>
      cartLines.reduce((sum, line) => {
        const unitPrice = line.isSpecialOffer ? 0 : line.product.price;
        return sum + unitPrice * line.quantity;
      }, 0),
    [cartLines],
  );
  const discount = useMemo(
    () =>
      cartLines.reduce((sum, line) => {
        if (line.isSpecialOffer) return sum;
        const lineDiscount = (line.product.price * line.offerRate) / 100;
        return sum + lineDiscount * line.quantity;
      }, 0),
    [cartLines],
  );
  const discountedTotal = subtotal - discount;
  const tax = Math.round(discountedTotal * TAX_RATE);
  const payable = discountedTotal + tax;

  const deals = user?.useroffer_set ?? [];

  async function loadCatalog(shopId = selectedShopId ?? undefined) {
    if (!shopId) return;
    const data = await fetchCategories(shopId);
    setCategories(data);
    if (data.length > 0) {
      setSelectedCategoryId(data[0].id);
    }
  }

  function pushDigit(digit: string) {
    if (activeTarget === "phone") {
      if (screen === "register") {
        if (registerPhone.length >= 11) return;
        setRegisterPhone((value) => `${value}${digit}`);
      } else if (screen === "login") {
        if (loginPhone.length >= 11) return;
        setLoginPhone((value) => `${value}${digit}`);
      }
      return;
    }
    if (activeTarget === "age") {
      if (registerAge.length >= 2) return;
      setRegisterAge((value) => `${value}${digit}`);
      return;
    }
    if (activeTarget === "code") {
      if (smsCode.length >= 4) return;
      setSmsCode((value) => `${value}${digit}`);
    }
  }

  function handleBackspace() {
    if (activeTarget === "phone") {
      if (screen === "register") {
        setRegisterPhone((value) => value.slice(0, -1));
      } else if (screen === "login") {
        setLoginPhone((value) => value.slice(0, -1));
      }
      return;
    }
    if (activeTarget === "age") {
      setRegisterAge((value) => value.slice(0, -1));
      return;
    }
    setSmsCode((value) => value.slice(0, -1));
  }

  async function registerAndContinue(event?: FormEvent) {
    event?.preventDefault();
    setErrorText("");
    setSuccessText("");
    if (!requireSelectedShop()) return;
    if (registerPhone.length !== 11) {
      setErrorText("شماره تلفن باید 11 رقم باشد.");
      return;
    }
    if (!registerAge) {
      setErrorText("سن خود را وارد کنید*");
      return;
    }

    setLoading(true);
    try {
      await signupUser({
        phone_number: registerPhone,
        age: Number(registerAge),
        gender: registerGender,
        uid_code: registerCardUid || undefined,
      });
      setScreen("login");
      setLoginPhone(registerPhone);
      setActiveTarget("phone");
      setSuccessText(
        "ثبت نام با موفقیت انجام شد. برای ورود پیامکی را دریافت و وارد کنید.",
      );
    } catch (error) {
      setSuccessText("");
      setErrorText(
        error instanceof Error ? error.message : "ثبت نام ناموفق بود.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function requestSmsCode() {
    setErrorText("");
    setSuccessText("");
    const shopId = requireSelectedShop();
    if (!shopId) return;
    if (smsResendLeft > 0) {
      setErrorText(`ارسال مجدد پیامک در ${smsResendLeft} ثانیه `);
      return;
    }
    if (loginPhone.length !== 11) {
      setErrorText("شماره تلفن باید 11 رقم باشد.");
      return;
    }
    setLoading(true);
    try {
      await sendLoginCode(loginPhone, shopId);
      setSmsCode("");
      const now = Date.now();
      setSmsExpiresAt(now + SMS_CODE_LIFE_SECONDS * 1000);
      setSmsResendAt(now + SMS_SEND_LIMIT_SECONDS * 1000);
      setSmsLifeLeft(SMS_CODE_LIFE_SECONDS);
      setSmsResendLeft(SMS_SEND_LIMIT_SECONDS);
      setScreen("verify");
      setActiveTarget("code");
    } catch (error) {
      if (error instanceof SmsSendLimitError) {
        const now = Date.now();
        setSmsResendAt(now + error.remainingSeconds * 1000);
        setSmsResendLeft(error.remainingSeconds);
        if (!smsExpiresAt) {
          setSmsExpiresAt(now + SMS_CODE_LIFE_SECONDS * 1000);
          setSmsLifeLeft(SMS_CODE_LIFE_SECONDS);
        }
        setErrorText(`ارسال مجدد پیامک در ${smsResendLeft} ثانیه `);
        setScreen("verify");
        setActiveTarget("code");
      } else {
        setErrorText(
          error instanceof Error ? error.message : "ارسال پیامک نا موفق",
        );
        // Stay on login page for real errors (e.g. SMS provider unavailable)
        setScreen("login");
        setActiveTarget("phone");
      }
    } finally {
      setLoading(false);
    }
  }

  async function verifyCodeAndEnter() {
    setErrorText("");
    const shopId = requireSelectedShop();
    if (!shopId) return;
    if (smsLifeLeft <= 0) {
      setErrorText("کد پیامکی منقضی شده است.");
      return;
    }
    if (smsCode.length !== 4) {
      setErrorText("کد پیامکی باید 4 رقمی باشد.");
      return;
    }

    setLoading(true);
    try {
      const session = await verifyLoginCode({
        phone_number: loginPhone,
        login_verification_code: smsCode,
        shop_id: shopId,
      });
      applyAuthSession(session);
      setAccessToken(session.access);
      setUser(session.user);
      setSuccessText("");
      await loadCatalog(shopId);
      setScreen("products");
      setErrorText("");
    } catch (error) {
      const raw = error instanceof Error ? error.message : "";
      const message = raw.trim().toLowerCase();

      if (message.includes("shop_not_found")) {
        setErrorText("فروشگاه انتخاب‌شده یافت نشد.");
      } else if (
        message.includes("expired") ||
        message.includes("token expired") ||
        message.includes("code expired")
      ) {
        setErrorText("کد پیامکی منقضی شده است. لطفاً مجدد درخواست پیامک کنید.");
      } else if (
        message.includes("invalid code") ||
        message.includes("incorrect code") ||
        message.includes("wrong code") ||
        message.includes("invalid verification") ||
        message.includes("verification code") ||
        message.includes("کد") ||
        message.includes("نادرست")
      ) {
        setErrorText("کد وارد شده نادرست است.");
      } else if (
        message.includes("phone") ||
        message.includes("mobile") ||
        message.includes("شماره") ||
        message.includes("not found") ||
        message.includes("invalid")
      ) {
        setErrorText("شماره همراه صحیح نیست یا در سیستم ثبت نشده است.");
      } else {
        setErrorText(raw || "ورود ناموفق");
      }
    } finally {
      setLoading(false);
    }
  }

  // NFC login is handled by the scanner-based `NFCAuth` component.

  function remainingScoreAfterCart(
    baseScore: number,
    cartState: Record<string, CartLine>,
    excludeKey?: string,
  ): number {
    let remaining = baseScore;
    for (const line of Object.values(cartState)) {
      if (!line.isSpecialOffer || line.key === excludeKey) continue;
      remaining -= line.product.score * line.quantity;
    }
    return remaining;
  }

  function addItemToCart(
    product: (typeof categories)[number]["products"][number],
    options: { offerRate?: number; isSpecialOffer?: boolean } = {},
  ) {
    const offerRate = options.offerRate ?? 0;
    const isSpecialOffer = Boolean(options.isSpecialOffer);
    const key = `${isSpecialOffer ? "special" : offerRate > 0 ? "offer" : "normal"}-${product.id}`;

    if (isSpecialOffer && user) {
      const existing = cart[key];
      const remaining = remainingScoreAfterCart(user.score, cart, key);
      const needed = product.score * ((existing?.quantity ?? 0) + 1);
      if (remaining < needed) {
        setErrorText(
          "امتیاز شما برای این پیشنهاد ویژه کافی نیست. لطفاً امتیاز خود را بررسی کنید.",
        );
        return;
      }
    }

    setErrorText("");
    setCart((current) => {
      const existing = current[key];
      return {
        ...current,
        [key]: {
          key,
          product,
          offerRate,
          isSpecialOffer,
          quantity: existing ? existing.quantity + 1 : 1,
        },
      };
    });
  }

  function addProductToCart(
    productId: number,
    options: { offerRate?: number; isSpecialOffer?: boolean } = {},
  ) {
    const product = categories
      .flatMap((category) => category.products)
      .find((item) => item.id === productId);
    if (!product) return;
    addItemToCart(product, options);
  }

  function removeCartLine(key: string) {
    setCart((current) => {
      const clone = { ...current };
      delete clone[key];
      return clone;
    });
  }

  async function confirmCheckout() {
    if (!user) return;
    const specialOfferLines = cartLines.filter((line) => line.isSpecialOffer);
    let updatedUser = user;
    try {
      for (const line of specialOfferLines) {
        for (let i = 0; i < line.quantity; i += 1) {
          // Keep backend offer usage in sync.
          updatedUser = await submitOfferUse({
            phone_number: user.phone_number,
            product_id: line.product.id,
          });
        }
      }
      setUser(updatedUser);
    } catch (error) {
      setErrorText(
        "امکان ثبت پیشنهاد ویژه وجود ندارد. لطفاً امتیاز را بررسی کنید و دوباره تلاش کنید.",
      );
      return;
    }
    setScreen("finalize");
  }

  function buildReceiptHtml(now: Date, receiptId: string, dateText: string): string {
    const safePhone = String(user?.phone_number ?? "").replace(/\D/g, "");
    return `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;">
        <div>
          <div style="font-size:18px;font-weight:700;">رسید خرید</div>
          <div style="font-size:12px;color:#555;">${asciiSafe(shopBrandName)}</div>
        </div>
        <div style="text-align:left;font-size:12px;color:#333;">
          <div><span style="color:#777;">شناسه رسید:</span> <span dir="ltr">${receiptId}</span></div>
          <div><span style="color:#777;">تاریخ:</span> <span>${dateText}</span></div>
        </div>
      </div>

      <hr style="border:none;border-top:1px dashed #ddd;margin:16px 0;" />

      <div style="font-size:13px;">
        <div><span style="color:#777;">شماره مشتری:</span> <span dir="ltr">${safePhone}</span></div>
        <div><span style="color:#777;">امتیاز مشتری:</span> <span>${user.score.toLocaleString("fa-IR")}</span></div>
      </div>

      <hr style="border:none;border-top:1px dashed #ddd;margin:16px 0;" />

      <div style="font-weight:700;margin-bottom:8px;">اقلام</div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        ${cartLines
          .map((line, index) => {
            const unit = line.isSpecialOffer ? 0 : line.product.price;
            const total = unit * line.quantity;
            const title = String(line.product.title ?? "");
            const badge = line.isSpecialOffer
              ? `<span style="font-size:11px;color:#0a7;padding:2px 6px;border:1px solid #bff3e5;border-radius:999px;">رایگان (پیشنهاد ویژه)</span>`
              : "";
            return `
              <div style="display:flex;justify-content:space-between;gap:12px;">
                <div style="flex:1;min-width:0;">
                  <div style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${title}</div>
                  <div style="font-size:12px;color:#666;">
                    تعداد: ${line.quantity.toLocaleString("fa-IR")}
                    ${badge ? ` • ${badge}` : ""}
                  </div>
                </div>
                <div style="text-align:left;white-space:nowrap;font-size:13px;">
                  <div style="color:#555;font-size:12px;">${formatReceiptPrice(unit)} × ${line.quantity.toLocaleString(
                    "fa-IR",
                  )}</div>
                  <div style="font-weight:700;">${formatReceiptPrice(total)}</div>
                </div>
              </div>
            `;
          })
          .join("")}
      </div>

      <hr style="border:none;border-top:1px solid #eee;margin:16px 0;" />

      <div style="display:flex;justify-content:space-between;">
        <div style="color:#666;">جمع جزء</div>
        <div style="font-weight:700;">${formatReceiptPrice(subtotal)}</div>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <div style="color:#666;">تخفیف</div>
        <div style="font-weight:700;">${formatReceiptPrice(discount)}</div>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <div style="color:#666;">مالیات (۹٪)</div>
        <div style="font-weight:700;">${formatReceiptPrice(tax)}</div>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:15px;">
        <div style="font-weight:800;">مبلغ قابل پرداخت</div>
        <div style="font-weight:900;">${formatReceiptPrice(payable)}</div>
      </div>

      <hr style="border:none;border-top:1px dashed #ddd;margin:16px 0;" />

      <div style="font-size:12px;color:#666;">
        <div>فروشگاه: ${selectedShop?.name ?? "—"}</div>
        <div>آدرس:</div>
      </div>
    `;
  }

  function printReceipt() {
    if (!user || cartLines.length === 0) return;
    const now = new Date();
    const receiptId = `RC-${Math.floor(Math.random() * 100000)}`;
    const dateText = `${now.toLocaleDateString("fa-IR")} ${now.toLocaleTimeString("fa-IR")}`;

    const printRoot = document.createElement("div");
    printRoot.className = "receipt-print-root";
    printRoot.dir = "rtl";
    printRoot.innerHTML = buildReceiptHtml(now, receiptId, dateText);
    document.body.appendChild(printRoot);

    const previousTitle = document.title;
    document.title = "رسید خرید";

    const cleanup = () => {
      printRoot.remove();
      document.title = previousTitle;
      window.removeEventListener("afterprint", cleanup);
    };
    window.addEventListener("afterprint", cleanup);

    window.setTimeout(() => {
      window.print();
      window.setTimeout(cleanup, 1000);
    }, 50);
  }

  function resetFlow() {
    setScreen("landing");
    resetSmsSession();
    setSuccessText("");
    setUser(null);
    setAccessToken(null);
    clearTokens();
    setCart({});
    setCategories([]);
    setSelectedShopIdState(null);
    clearSelectedShopId();
    setLoginPhone("");
    setRegisterAge("");
    setRegisterPhone("");
    setRegisterCardUid("");
  }

  const goBack = useCallback(() => {
    const shopId = selectedShopId;
    resetFlow();
    if (shopId !== null) {
      setSelectedShopIdState(shopId);
      setSelectedShopId(shopId);
    }
    window.history.replaceState(
      { kiosk: "landing" },
      "",
      window.location.pathname || "/",
    );
  }, [selectedShopId]);

  const goBackRef = useRef(goBack);
  goBackRef.current = goBack;

  useEffect(() => {
    if (window.history.state?.kiosk !== "root") {
      window.history.replaceState({ kiosk: "root" }, "");
      window.history.pushState({ kiosk: "app" }, "");
    }
    const onPopState = () => {
      goBackRef.current();
      window.history.pushState({ kiosk: "app" }, "");
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return (
    <div className="app-shell" dir="rtl">
      <header
        className={
          screen === "landing" ? "page-header page-header--no-back" : "page-header"
        }
      >
        {screen !== "landing" ? (
          <button type="button" className="ghost-button" onClick={goBack}>
            بازگشت
          </button>
        ) : null}
        <h1>{brandTitle}</h1>
      </header>

      {errorText && screen !== "products" ? (
        <p ref={errorBannerRef} className="error-box error-box--attention">
          {errorText}
        </p>
      ) : null}

      {screen === "landing" && (
        <section className="stage landing landing--stacked">
          <div className="landing-center">
            <p className="hero-title">خوش آمدید به {shopBrandName}</p>
            <p className="hero-subtitle">
              ابتدا فروشگاه را انتخاب کنید، سپس با شماره همراه یا کارت NFC وارد
              شوید.
            </p>
            <div className="panel landing-actions">
              <div className="landing-actions-col">
              <button
                type="button"
                className="action-button"
                disabled={!selectedShopId || shopsLoading}
                onClick={() => {
                  if (!requireSelectedShop()) return;
                  resetSmsSession();
                  setLoginPhone("");
                  setScreen("login");
                }}
              >
                ورود
              </button>
              <button
                type="button"
                className="outline-button"
                disabled={!selectedShopId || shopsLoading}
                onClick={() => {
                  if (!requireSelectedShop()) return;
                  resetSmsSession();
                  setRegisterCardUid("");
                  setScreen("register");
                }}
              >
                ثبت نام مشتری جدید
              </button>
            </div>
          </div>
          </div>
          <div className="panel shop-picker">
            <h2 className="shop-picker-title">انتخاب فروشگاه</h2>
            {shopsLoading ? (
              <p>در حال بارگذاری فروشگاه‌ها...</p>
            ) : shops.length === 0 ? (
              <p>فروشگاهی برای نمایش ثبت نشده است.</p>
            ) : (
              <div className="shop-grid">
                {shops.map((shop) => (
                  <button
                    key={shop.id}
                    type="button"
                    className={
                      selectedShopId === shop.id
                        ? "shop-card shop-card--selected"
                        : "shop-card"
                    }
                    onClick={() => selectShop(shop.id)}
                  >
                    {shop.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {screen === "register" && (
        <section className="stage split">
          <div className="form-panel">
            <form className="panel" onSubmit={registerAndContinue}>
              <h2>ثبت عضویت جدید</h2>
              {selectedShop ? (
                <p className="shop-context">فروشگاه: {selectedShop.name}</p>
              ) : null}
              <NFCRegistrationScan
                capturedUid={registerCardUid}
                onUidCaptured={setRegisterCardUid}
                onClear={() => setRegisterCardUid("")}
              />
              <label>
                شماره همراه
                <input
                  value={registerPhone}
                  onFocus={() => setActiveTarget("phone")}
                  onChange={(event) =>
                    setRegisterPhone(
                      event.target.value.replace(/\D/g, "").slice(0, 11),
                    )
                  }
                  placeholder="09xxxxxxxxx"
                />
              </label>
              <label>
                سن
                <input
                  value={registerAge}
                  onFocus={() => setActiveTarget("age")}
                  onChange={(event) =>
                    setRegisterAge(
                      event.target.value.replace(/\D/g, "").slice(0, 2),
                    )
                  }
                  placeholder="Age"
                />
              </label>
              <div className="gender-row">
                <span>جنسیت</span>
                <label>
                  <input
                    type="radio"
                    name="gender"
                    checked={registerGender === "male"}
                    onChange={() => setRegisterGender("male")}
                  />
                  مرد
                </label>
                <label>
                  <input
                    type="radio"
                    name="gender"
                    checked={registerGender === "female"}
                    onChange={() => setRegisterGender("female")}
                  />
                  زن
                </label>
              </div>
              <button
                type="button"
                className="action-button"
                onClick={() => void registerAndContinue()}
                disabled={loading}
              >
                تایید
              </button>
            </form>
          </div>
          <NumericKeypad
            onDigit={pushDigit}
            onBackspace={handleBackspace}
            onConfirm={() => void registerAndContinue()}
            confirmLabel={loading ? "..." : "ثبت"}
            disabled={loading}
          />
        </section>
      )}

      {screen === "login" && (
        <section className="stage split">
          <div className="form-panel">
            <div className="panel">
              <h2>ورود مشتری</h2>
              {successText ? (
                <p className="success-box">{successText}</p>
              ) : null}
              {selectedShop ? (
                <p className="shop-context">فروشگاه: {selectedShop.name}</p>
              ) : null}
              <label>
                شماره همراه
                <input
                  value={loginPhone}
                  onFocus={() => setActiveTarget("phone")}
                  onChange={(event) => {
                    setSuccessText("");
                    setLoginPhone(
                      event.target.value.replace(/\D/g, "").slice(0, 11),
                    );
                  }}
                  placeholder="09xxxxxxxxx"
                />
              </label>
              <p>
                بعد از ورود شماره، کد تایید پیامکی ارسال می‌شود. زمان اعتبار کد{" "}
                {SMS_CODE_LIFE_SECONDS} ثانیه و فاصله مجاز برای ارسال مجدد{" "}
                {SMS_SEND_LIMIT_SECONDS} ثانیه است.
              </p>
              <button
                type="button"
                className="action-button"
                onClick={requestSmsCode}
                disabled={loading}
              >
                ارسال کد پیامک
              </button>
            </div>
            <NFCLoginScan
              shopId={selectedShopId}
              disabled={loading || shopsLoading}
              onLoginSuccess={async (session: AuthSession) => {
                try {
                  applyAuthSession(session);
                  setAccessToken(session.access);
                  setUser(session.user);
                  setSuccessText("");
                  await loadCatalog(selectedShopId ?? undefined);
                  setScreen("products");
                  setErrorText("");
                } catch (e) {
                  setErrorText(
                    e instanceof Error
                      ? e.message
                      : "Could not store login session. Please retry.",
                  );
                }
              }}
            />
          </div>
          <NumericKeypad
            onDigit={pushDigit}
            onBackspace={handleBackspace}
            onConfirm={() => void requestSmsCode()}
            confirmLabel={loading ? "..." : "تایید"}
            disabled={loading}
          />
        </section>
      )}

      {screen === "verify" && (
        <section className="stage split">
          <div className="panel form-panel">
            <h2>تایید پیامکی</h2>
            <p>کد پیامک برای {loginPhone} ارسال شد.</p>
            <label>
              کد چهار رقمی
              <input
                value={smsCode}
                onFocus={() => setActiveTarget("code")}
                onChange={(event) =>
                  setSmsCode(event.target.value.replace(/\D/g, "").slice(0, 4))
                }
                placeholder="----"
              />
            </label>
            <div className="verify-timers">
              <p className={smsResendLeft > 0 ? "timer" : "timer success"}>
                {smsResendLeft > 0
                  ? `ارسال مجدد تا ${smsResendLeft} ثانیه دیگر`
                  : "اکنون می‌توانید کد را مجدد ارسال کنید."}
              </p>
            </div>
            <div className="row-actions">
              <button
                type="button"
                className="action-button"
                onClick={verifyCodeAndEnter}
                disabled={loading || smsLifeLeft <= 0}
              >
                ورود
              </button>
              <button
                type="button"
                className="outline-button"
                onClick={requestSmsCode}
                disabled={loading || smsResendLeft > 0}
              >
                ارسال مجدد
              </button>
            </div>
          </div>
          <NumericKeypad
            onDigit={pushDigit}
            onBackspace={handleBackspace}
            onConfirm={() => void verifyCodeAndEnter()}
            confirmLabel={loading ? "..." : "ورود"}
            disabled={loading}
          />
        </section>
      )}

      {screen === "products" && user && (
        <section className="stage products">
          <div className="panel score-bar">
            {selectedShop ? (
              <span>فروشگاه: {selectedShop.name}</span>
            ) : null}
            <span>شماره: {maskPhone(user.phone_number)}</span>
            <span>امتیاز: {user.score.toLocaleString("en-US")}</span>
            <span>تعداد انتخاب: {selectedItemsCount}</span>
          </div>

          <div className="selected-strip panel">
            <h3>انتخاب‌های فعلی</h3>
            {cartLines.length === 0 ? (
              <p>هنوز محصولی انتخاب نشده است.</p>
            ) : (
              <div className="chip-list">
                {cartLines.map((line) => (
                  <button
                    key={line.key}
                    className="chip"
                    type="button"
                    onClick={() => removeCartLine(line.key)}
                  >
                    {line.product.title} x{line.quantity}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="panel">
            <h3> پیشنهادات ویژه </h3>
            {deals.length === 0 ? (
              <p>با امتیاز فعلی شما، پیشنهاد خاصی فعال نیست.</p>
            ) : (
              <div className="deal-list">
                {deals.map((offer) => (
                  <article key={offer.product.id} className="deal-card">
                    <img
                      src={resolveProductImageUrl(offer.product.image_url)}
                      alt={offer.product.title}
                      loading="lazy"
                    />
                    <div>
                      <h4>{offer.product.title}</h4>
                      <p>
                        قیمت اصلی: {formatPrice(offer.product.price)} | امتیاز
                        لازم: {offer.product.score.toLocaleString("en-US")}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="outline-button small"
                      onClick={() =>
                        addItemToCart(offer.product, { isSpecialOffer: true })
                      }
                    >
                      اضافه کردن به سبد
                    </button>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="panel totals">
            {errorText ? (
              <p
                ref={productsNoticeRef}
                className="error-box error-box--attention"
              >
                {errorText}
              </p>
            ) : null}
            <p>جمع بدون تخفیف: {formatPrice(subtotal)}</p>
            <p>تخفیف: {formatPrice(discount)}</p>
            <p>مالیات (9%): {formatPrice(tax)}</p>
            <p className="payable">قابل پرداخت: {formatPrice(payable)}</p>
            <button
              type="button"
              className="action-button"
              onClick={() => void confirmCheckout()}
              disabled={cartLines.length === 0}
            >
              تایید نهایی سفارش
            </button>
          </div>
        </section>
      )}

      {screen === "finalize" && user && (
        <section className="stage finalize">
          <h2>کالاهای انتخابی شما</h2>
          <div className="panel checkout-list">
            {cartLines.map((line) => (
              <article key={line.key} className="checkout-row">
                <img
                  src={resolveProductImageUrl(line.product.image_url)}
                  alt={line.product.title}
                  loading="lazy"
                />
                <div>
                  <h4>{line.product.title}</h4>
                  <p>تعداد: {line.quantity}</p>
                  <p>
                    قیمت واحد:{" "}
                    {formatPrice(line.isSpecialOffer ? 0 : line.product.price)}
                  </p>
                  {line.isSpecialOffer && <p>پیشنهاد ویژه: رایگان</p>}
                  {!line.isSpecialOffer && line.offerRate > 0 && (
                    <p>تخفیف خط: {line.offerRate}%</p>
                  )}
                </div>
                <strong>
                  {formatPrice(
                    (line.isSpecialOffer ? 0 : line.product.price) *
                      line.quantity,
                  )}
                </strong>
              </article>
            ))}
          </div>
          <div className="panel">
            <p>جمع خرید: {formatPrice(subtotal)}</p>
            <p>تخفیف: {formatPrice(discount)}</p>
            <p>مالیات: {formatPrice(tax)}</p>
            <p className="payable">مبلغ نهایی: {formatPrice(payable)}</p>
            <button
              type="button"
              className="action-button"
              onClick={printReceipt}
            >
              چاپ رسید
            </button>
            <p className="timer">خروج خودکار پس از {checkoutCountdown} ثانیه</p>
          </div>
        </section>
      )}

      {screen === "nfcSettings" && user && (
        <section className="stage">
          <div className="panel form-panel">
            <h2>مدیریت NFC</h2>
            {!accessToken ? (
              <p className="error-box">
                توکن ورود یافت نشد. لطفا دوباره وارد شوید.
              </p>
            ) : (
              <>
                <NFCAuth
                  accessToken={accessToken}
                  mode="register"
                  onRegisterSuccess={() => {
                    setErrorText("تگ با موفقیت لینک شد.");
                  }}
                />
              </>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

export default App;
