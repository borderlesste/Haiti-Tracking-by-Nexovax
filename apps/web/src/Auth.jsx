import { useState } from "react";
import {
  UsersThree,
  Buildings,
  Code,
  UserPlus,
  ArrowRight,
  EnvelopeSimple,
  ShieldCheck,
} from "@phosphor-icons/react";
import { useLocale } from "./i18n";
import {
  Brand,
  Button,
  Field,
  Form,
  PasswordField,
  Notice,
  Link,
  useApp,
} from "./ui";
import { api, validNext } from "./api";
export function Auth({ mode }) {
  const { t } = useLocale();
  const { navigate, setUser, search } = useApp();
  const [profile, setProfile] = useState("collaborator");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const signup = mode === "registro";
  const title = signup
    ? "register"
    : mode === "recuperar"
      ? "recover"
      : mode === "restablecer"
        ? "reset"
        : mode === "verificar"
          ? "verify"
          : "login";
  async function submit(data, form) {
    setError("");
    if (signup && data.get("password") !== data.get("password_confirm")) {
      setError(t("passwordMismatch"));
      form.elements.password_confirm.focus();
      return;
    }
    setBusy(true);
    try {
      if (signup) {
        await api("/auth/register", {
          method: "POST",
          body: {
            display_name: data.get("display_name"),
            email: data.get("email"),
            phone: data.get("phone") || null,
            password: data.get("password"),
            profile: profile === "company" ? "business" : profile,
            terms_accepted: !!data.get("terms"),
            privacy_accepted: !!data.get("privacy"),
          },
        });
        setSuccess(true);
      } else if (mode === "recuperar") {
        await api("/auth/forgot-password", {
          method: "POST",
          body: { email: data.get("email") },
        });
        setSuccess(true);
      } else if (mode === "restablecer") {
        await api("/auth/reset-password", {
          method: "POST",
          body: {
            token: search.get("token") || data.get("token"),
            password: data.get("password"),
          },
        });
        setSuccess(true);
      } else if (mode === "verificar") {
        await api("/auth/verify-email", {
          method: "POST",
          body: { token: search.get("token") || data.get("token") },
        });
        navigate("/acceso?verified=1", { replace: true });
      } else {
        const j = await api("/auth/login", {
          method: "POST",
          body: {
            email: data.get("email"),
            password: data.get("password"),
            otp: data.get("otp") || null,
          },
        });
        setUser(j.data.user || j.data);
        navigate(validNext(search.get("next")));
      }
    } catch (e) {
      setError(
        e.status === 422
          ? t("invalidData")
          : e.status === 429
            ? t("rateLimited")
            : e.status === 401
              ? t("loginRequired")
              : e.status === 400 && ["verificar", "restablecer"].includes(mode)
                ? t("tokenError")
                : t("error"),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <section className="auth-card">
        <Brand />
        <h1>{t(title)}</h1>
        <p className="auth-subtitle">{t(signup ? "join" : "slogan")}</p>
        {mode === "acceso" && search.has("verified") && (
          <Notice>{t("emailVerified")}</Notice>
        )}
        {success ? (
          <div className="success-panel">
            <EnvelopeSimple size={48} weight="duotone" />
            <h2>
              {t(
                mode === "verificar"
                  ? "emailVerified"
                  : mode === "restablecer"
                    ? "passwordUpdated"
                    : "checkEmail",
              )}
            </h2>
            <Link to="/acceso" className="button">
              {t("login")}
              <ArrowRight size={18} />
            </Link>
          </div>
        ) : (
          <Form noValidate onSubmit={submit}>
            <Notice tone="error">{error}</Notice>
            {signup && (
              <Field
                label={t("name")}
                name="display_name"
                minLength={2}
                placeholder="Jean Michel Pierre"
                required
                autoComplete="name"
                maxLength={100}
              />
            )}
            {!["restablecer", "verificar"].includes(mode) && (
              <Field
                label={t("email")}
                name="email"
                type="email"
                placeholder="tu@ejemplo.com"
                required
                autoComplete="email"
                maxLength={254}
              />
            )}{" "}
            {signup && (
              <Field
                label={t("phone")}
                name="phone"
                type="tel"
                placeholder="+509 37 12 34 56"
                autoComplete="tel"
                maxLength={30}
              />
            )}{" "}
            {["registro", "acceso", "restablecer"].includes(mode) && (
              <PasswordField
                label={t("password")}
                confirm={signup || mode === "restablecer"}
              />
            )}{" "}
            {signup && (
              <>
                <small className="help">{t("passwordHelp")}</small>
                <PasswordField
                  label={t("confirmPassword")}
                  name="password_confirm"
                  confirm
                />
                <fieldset className="profile-options">
                  <legend>
                    {t("profile")} <span className="required">*</span>
                  </legend>
                  {[
                    [
                      "collaborator",
                      UsersThree,
                      "collaborator",
                      "collaboratorDesc",
                    ],
                    ["company", Buildings, "company", "companyDesc"],
                    ["developer", Code, "developer", "developerDesc"],
                  ].map(([value, Icon, key, desc]) => (
                    <label
                      className={profile === value ? "selected" : ""}
                      key={value}
                    >
                      <Icon size={27} weight="duotone" />
                      <span>
                        <strong>{t(key)}</strong>
                        <small>{t(desc)}</small>
                      </span>
                      <input
                        type="radio"
                        name="profile"
                        value={value}
                        checked={profile === value}
                        onChange={() => setProfile(value)}
                      />
                    </label>
                  ))}
                </fieldset>
                <label className="check">
                  <input type="checkbox" name="terms" required />
                  <span>
                    {t("accept")} <Link to="/legal/terminos">{t("terms")}</Link>{" "}
                    *
                  </span>
                </label>
                <label className="check">
                  <input type="checkbox" name="privacy" required />
                  <span>
                    {t("acceptPrivacy")}{" "}
                    <Link to="/legal/privacidad">{t("privacy")}</Link> *
                  </span>
                </label>
              </>
            )}
            {["verificar", "restablecer"].includes(mode) &&
              !search.get("token") && (
                <Field label="Token" name="token" required autoComplete="off" />
              )}
            {mode === "acceso" && (
              <Field
                label={t("otp")}
                name="otp"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                minLength={6}
                maxLength={6}
              />
            )}
            <Button type="submit" busy={busy} className="full red">
              {signup && <UserPlus size={20} />} {t(title)}
            </Button>
            {mode === "acceso" && (
              <Link className="under-form" to="/recuperar">
                {t("forgot")}
              </Link>
            )}
            <Link className="under-form" to={signup ? "/acceso" : "/registro"}>
              {t(signup ? "haveAccount" : "noAccount")}
            </Link>
          </Form>
        )}
        <div className="reward-note">
          <ShieldCheck size={31} weight="duotone" />
          <div>
            <strong>{t("recognition")}</strong>
            <p>{t("recognitionDesc")}</p>
          </div>
        </div>
      </section>
    </div>
  );
}
