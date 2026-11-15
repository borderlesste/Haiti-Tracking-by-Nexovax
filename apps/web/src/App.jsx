import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { Locale, translator } from "./i18n";
import { AppContext, Header, Link, Notice } from "./ui";
import { Home } from "./Home";
import { Auth } from "./Auth";
import { Places, PlaceDetail } from "./Places";
import { Contribute } from "./Contribute";
import {
  Account,
  Admin,
  Contributions,
  DeveloperPortal,
  Developers,
  ApiDocs,
} from "./Workspace";
import "@fontsource-variable/nunito-sans";
export function App() {
  const [location, setLocation] = useState(
      window.location.pathname + window.location.search + window.location.hash,
    ),
    [user, setUser] = useState(null),
    [authLoading, setAuthLoading] = useState(true),
    [lang, setLanguage] = useState(() => {
      try {
        return localStorage.getItem("ht_language") || "es";
      } catch {
        return "es";
      }
    }),
    [notice, setNotice] = useState("");
  const t = useMemo(() => translator(lang), [lang]);
  const current = useMemo(
    () => new URL(location, window.location.origin),
    [location],
  );
  const path = current.pathname;
  const search = useMemo(() => {
    const p = new URLSearchParams(current.search);
    const fragment = new URLSearchParams(current.hash.slice(1));
    if (fragment.has("token")) p.set("token", fragment.get("token"));
    return p;
  }, [current]);
  const navigate = useCallback(
    (to, { replace = false, scroll = true } = {}) => {
      window.history[replace ? "replaceState" : "pushState"]({}, "", to);
      setLocation(
        window.location.pathname +
          window.location.search +
          window.location.hash,
      );
      if (scroll) {
        window.scrollTo(0, 0);
        requestAnimationFrame(() =>
          document.getElementById("content")?.focus({ preventScroll: true }),
        );
      }
    },
    [],
  );
  useEffect(() => {
    const pop = () =>
      setLocation(
        window.location.pathname +
          window.location.search +
          window.location.hash,
      );
    window.addEventListener("popstate", pop);
    window.addEventListener("hashchange", pop);
    return () => {
      window.removeEventListener("popstate", pop);
      window.removeEventListener("hashchange", pop);
    };
  }, []);
  useEffect(() => {
    const ac = new AbortController();
    api("/auth/me", { signal: ac.signal })
      .then((j) => setUser(j.data))
      .catch(() => {})
      .finally(() => {
        if (!ac.signal.aborted) setAuthLoading(false);
      });
    return () => ac.abort();
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = `Haiti Tracking by Nexovax · ${t(path === "/mapa" ? "map" : "slogan")}`;
  }, [path, t, lang]);
  const setLang = (value) => {
    setLanguage(value);
    try {
      localStorage.setItem("ht_language", value);
    } catch {}
  };
  const logout = async () => {
    try {
      await api("/auth/logout", { method: "POST", body: {} });
      setUser(null);
      navigate("/");
    } catch {
      setNotice(t("error"));
    }
  };
  let page;
  if (path === "/") page = <Home />;
  else if (path === "/mapa") page = <Places />;
  else if (path.startsWith("/ubicaciones/"))
    page = <PlaceDetail key={path} code={path.split("/")[2]} />;
  else if (
    [
      "/registro",
      "/acceso",
      "/recuperar",
      "/restablecer",
      "/verificar",
    ].includes(path)
  )
    page = <Auth key={path} mode={path.slice(1)} />;
  else if (path.startsWith("/contribuir/"))
    page = (
      <Contribute
        key={path}
        id={path === "/contribuir/nueva" ? undefined : path.split("/")[2]}
      />
    );
  else if (path === "/contribuciones") page = <Contributions />;
  else if (path === "/cuenta") page = <Account />;
  else if (path === "/desarrolladores/panel") page = <DeveloperPortal />;
  else if (path === "/desarrolladores/documentacion") page = <ApiDocs />;
  else if (path === "/desarrolladores") page = <Developers />;
  else if (path.startsWith("/admin"))
    page = <Admin section={path.split("/")[2]} />;
  else if (path.startsWith("/legal/"))
    page = (
      <main className="page legal-page">
        <section className="panel">
          <span className="eyebrow blue">HAITI TRACKING · PILOTO</span>
          <h1>{t(path.includes("privacidad") ? "privacy" : "terms")}</h1>
          <Notice>{t("legalDraft")}</Notice>
          <h2>{t("privacyNotice")}</h2>
          <p>{t("privacySub")}</p>
          <h2>{t("contribute")}</h2>
          <p>{t("sourceConsent")}</p>
          <p>{t("humanReview")}</p>
          <h2>{t("account")}</h2>
          <p>{t("sessionHelp")}</p>
          <p>{t("recognitionDesc")}</p>
          <Link to="/cuenta">{t("consentTitle")}</Link>
        </section>
      </main>
    );
  else
    page = (
      <main className="center-card">
        <h1>404</h1>
        <p>{t("notFound")}</p>
        <Link to="/">{t("home")}</Link>
      </main>
    );
  const privateRoute =
    path.startsWith("/contribuir") ||
    path.startsWith("/admin") ||
    ["/cuenta", "/contribuciones", "/desarrolladores/panel"].includes(path);
  return (
    <Locale.Provider value={{ lang, t }}>
      <AppContext.Provider
        value={{ user, setUser, path, search, navigate, lang, setLang, logout }}
      >
        <a href="#content" className="skip-link">
          {t("skipContent")}
        </a>
        {![
          "/registro",
          "/acceso",
          "/verificar",
          "/restablecer",
          "/recuperar",
        ].includes(path) && <Header />}
        <div id="content" tabIndex={-1}>
          {authLoading && privateRoute ? (
            <main className="page" role="status">
              {t("loading")}
            </main>
          ) : (
            page
          )}
        </div>
        {notice && (
          <div className="app-toast">
            <Notice tone="error">{notice}</Notice>
            <button onClick={() => setNotice("")}>{t("close")}</button>
          </div>
        )}
        <footer className="footer">
          <div>
            <strong>
              Haiti Tracking <span>by Nexovax</span>
            </strong>
            <small>{t("slogan")}</small>
          </div>
          <nav>
            <Link to="/legal/terminos">{t("terms")}</Link>
            <Link to="/legal/privacidad">{t("privacy")}</Link>
            <Link to="/desarrolladores/documentacion">API</Link>
          </nav>
          <span>© {new Date().getFullYear()} Nexovax</span>
        </footer>
      </AppContext.Provider>
    </Locale.Provider>
  );
}
