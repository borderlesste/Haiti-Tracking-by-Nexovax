import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useId,
} from "react";
import {
  Eye,
  EyeSlash,
  CircleNotch,
  ArrowRight,
  MapPin,
  UserCircle,
  List,
  X,
  SignOut,
} from "@phosphor-icons/react";
import { useLocale } from "./i18n";
import { useApp } from "./context.js";
export { AppContext, useApp } from "./context.js";
const FormErrors = createContext({});
export function Link({ to, children, ...props }) {
  const { navigate } = useApp();
  return (
    <a
      href={to}
      {...props}
      onClick={(event) => {
        props.onClick?.(event);
        if (
          !event.defaultPrevented &&
          !event.ctrlKey &&
          !event.metaKey &&
          !event.shiftKey &&
          event.button === 0
        ) {
          event.preventDefault();
          navigate(to);
        }
      }}
    >
      {children}
    </a>
  );
}
export function Brand() {
  return (
    <Link to="/" className="brand" aria-label="Haiti Tracking by Nexovax">
      <span className="brand-mark">
        <MapPin weight="fill" size={53} />
        <img src="/assets/flag.png" alt="" />
      </span>
      <span>
        <strong>Haiti Tracking</strong>
        <small>by Nexovax</small>
      </span>
    </Link>
  );
}
export function Button({
  children,
  busy,
  variant = "",
  className = "",
  ...props
}) {
  return (
    <button
      className={`button ${variant} ${className}`}
      {...props}
      disabled={props.disabled || busy}
      aria-busy={busy || undefined}
    >
      <span className="button-label">{children}</span>
      {busy && (
        <CircleNotch
          className="spin button-loader"
          size={20}
          aria-hidden="true"
        />
      )}
    </button>
  );
}
export function Notice({ children, tone = "info" }) {
  return children ? (
    <div
      className={`notice ${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  ) : null;
}
export function Field({ label, help, error, children, ...props }) {
  const id = props.id || props.name;
  const errors = useContext(FormErrors);
  const message = error || errors[id];
  const Control = props.as || "input";
  const { as, ...rest } = props;
  return (
    <div className={`field ${props.className || ""}`}>
      <label htmlFor={id}>
        {label}
        {props.required && <span className="required"> *</span>}
      </label>
      <Control
        {...rest}
        id={id}
        className="control"
        aria-invalid={!!message}
        aria-describedby={help || message ? `${id}-help` : undefined}
      >
        {children}
      </Control>
      {(help || message) && (
        <small id={`${id}-help`} className={message ? "field-error" : "help"}>
          {message || help}
        </small>
      )}
    </div>
  );
}
export function PasswordField({ label, name = "password", confirm = false }) {
  const [show, setShow] = useState(false);
  const errors = useContext(FormErrors);
  const { t } = useLocale();
  return (
    <div className="field">
      <label htmlFor={name}>
        {label}
        <span className="required"> *</span>
      </label>
      <div className="password-input">
        <input
          className="control"
          id={name}
          name={name}
          type={show ? "text" : "password"}
          required
          minLength={12}
          maxLength={128}
          autoComplete={confirm ? "new-password" : "current-password"}
          placeholder={confirm ? t("passwordHelp") : undefined}
          aria-invalid={!!errors[name]}
          aria-describedby={errors[name] ? `${name}-error` : undefined}
        />
        <button
          type="button"
          className="icon-button"
          aria-label={t(show ? "hidePassword" : "showPassword")}
          aria-pressed={show}
          onClick={() => setShow(!show)}
        >
          {show ? <EyeSlash size={20} /> : <Eye size={20} />}
        </button>
      </div>
      {errors[name] && (
        <small className="field-error" id={`${name}-error`}>
          {errors[name]}
        </small>
      )}
    </div>
  );
}
export function Form({ onSubmit, onChange, children, className = "" }) {
  const { t } = useLocale();
  const [errors, setErrors] = useState({});
  return (
    <FormErrors.Provider value={errors}>
      <form
        noValidate
        className={`${className} ${Object.keys(errors).length ? "validated" : ""}`}
        onChange={onChange}
        onInput={(event) => {
          if (event.target.validity?.valid && errors[event.target.id])
            setErrors((old) => {
              const next = { ...old };
              delete next[event.target.id];
              return next;
            });
        }}
        onSubmit={(event) => {
          event.preventDefault();
          const form = event.currentTarget;
          const invalid = Array.from(form.elements).filter(
            (el) => el.willValidate && !el.validity.valid,
          );
          if (invalid.length) {
            setErrors(
              Object.fromEntries(
                invalid.map((el) => [el.id || el.name, t("required")]),
              ),
            );
            invalid[0].focus();
            return;
          }
          setErrors({});
          onSubmit(new FormData(form), form);
        }}
      >
        {Object.keys(errors).length > 0 && (
          <Notice tone="error">{t("required")}</Notice>
        )}
        {children}
      </form>
    </FormErrors.Provider>
  );
}
export function Dialog({ title, open, onClose, children }) {
  const ref = useRef();
  const opener = useRef();
  const titleId = useId();
  const { t } = useLocale();
  useEffect(() => {
    if (open && !ref.current.open) {
      opener.current = document.activeElement;
      ref.current.showModal();
    } else if (!open && ref.current.open) ref.current.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onClose={() => {
        onClose();
        requestAnimationFrame(() => {
          const target =
            opener.current?.isConnected && !opener.current.disabled
              ? opener.current
              : document.getElementById("content");
          target?.focus({ preventScroll: true });
        });
      }}
    >
      <div className="dialog-head">
        <h2 id={titleId}>{title}</h2>
        <button
          type="button"
          className="icon-button"
          onClick={onClose}
          aria-label={t("close")}
        >
          <X size={22} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Gate({ children, admin = false }) {
  const { user, path } = useApp();
  const { t } = useLocale();
  if (!user)
    return (
      <section className="center-card">
        <UserCircle size={54} weight="duotone" />
        <h1>{t("loginRequired")}</h1>
        <p>{t("join")}</p>
        <Link
          className="button"
          to={`/acceso?next=${encodeURIComponent(path)}`}
        >
          {t("login")}
          <ArrowRight size={18} />
        </Link>
        <Link to="/registro">{t("register")}</Link>
      </section>
    );
  if (admin && !["admin", "moderator"].includes(user.role))
    return (
      <section className="center-card">
        <h1>{t("forbidden")}</h1>
        <Link to="/">{t("home")}</Link>
      </section>
    );
  return children;
}
export function Header() {
  const { user, path, lang, setLang, logout } = useApp();
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  return (
    <header className="header">
      <div className="nav-inner">
        <Brand />
        <button
          className="mobile-toggle icon-button"
          aria-label="Menu"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? <X size={24} /> : <List size={24} />}
        </button>
        <nav className={open ? "open" : ""} aria-label="Navigation">
          {[
            ["/", "home"],
            ["/mapa", "map"],
            ["/contribuir/nueva", "contribute"],
            ["/desarrolladores", "api"],
          ].map(([to, key]) => (
            <Link
              key={to}
              to={to}
              className={
                (
                  to === "/"
                    ? path === "/"
                    : path.startsWith(to.split("/").slice(0, 2).join("/"))
                )
                  ? "active"
                  : ""
              }
            >
              {t(key)}
            </Link>
          ))}
        </nav>
        <div className="nav-actions">
          <label className="sr-only" htmlFor="language">
            {t("language")}
          </label>
          <select
            id="language"
            className="language"
            value={lang}
            onChange={(e) => setLang(e.target.value)}
          >
            <option value="es">ES</option>
            <option value="fr">FR</option>
            <option value="ht">HT</option>
          </select>
          {user ? (
            <>
              <Link
                to="/cuenta"
                className="account-link"
                aria-label={t("account")}
              >
                <UserCircle size={29} weight="duotone" />
                <span>{user.display_name?.split(" ")[0]}</span>
              </Link>
              <button
                className="icon-button logout"
                onClick={logout}
                aria-label={t("logout")}
              >
                <SignOut size={20} />
              </button>
            </>
          ) : (
            <Link to="/acceso" className="button outline login-button">
              <UserCircle size={20} />
              {t("login")}
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
