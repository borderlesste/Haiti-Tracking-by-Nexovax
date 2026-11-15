import { useEffect, useState } from "react";
import {
  MapPin,
  UsersThree,
  ShieldCheck,
  Code,
  Plus,
  MapTrifold,
  Crosshair,
  Stack,
  ArrowRight,
  GlobeHemisphereWest,
} from "@phosphor-icons/react";
import { useLocale } from "./i18n";
import { Link, useApp } from "./ui";
import { Map } from "./Map";
import { api } from "./api";
export function Home() {
  const { t, lang } = useLocale();
  const { navigate } = useApp();
  const [stats, setStats] = useState();
  const [places, setPlaces] = useState([]);
  useEffect(() => {
    const ac = new AbortController();
    api("/public/stats", { signal: ac.signal })
      .then((j) => setStats(j.data))
      .catch(() => {});
    api("/locations/search?limit=20", { signal: ac.signal })
      .then((j) => setPlaces(j.data))
      .catch(() => {});
    return () => ac.abort();
  }, []);
  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-copy">
            <div className="eyebrow">
              <GlobeHemisphereWest size={16} />
              {t("slogan")}
            </div>
            <h1>{t("hero")}</h1>
            <p>{t("intro")}</p>
            <div className="hero-actions">
              <Link to="/contribuir/nueva" className="button red">
                <Plus size={25} weight="bold" />
                {t("newLocation")}
              </Link>
              <Link to="/mapa" className="button light-outline">
                <MapTrifold size={23} />
                {t("explore")}
              </Link>
            </div>
          </div>
          <div className="hero-map">
            <Map home places={places} />
            <form
              noValidate
              className="map-search"
              role="search"
              onSubmit={(e) => {
                e.preventDefault();
                navigate(
                  `/mapa?q=${encodeURIComponent(new FormData(e.currentTarget).get("q"))}`,
                );
              }}
            >
              <MapPin size={20} />
              <input
                name="q"
                aria-label={t("search")}
                placeholder={t("search")}
              />
              <button className="icon-button" aria-label={t("search")}>
                <ArrowRight size={20} />
              </button>
            </form>
            <span className="map-tag">HAÏTI · 18.9712° N, 72.2852° W</span>
          </div>
        </div>
      </section>
      <section className="stats-wrap" aria-label={t("liveStats")}>
        <div className="stats">
          {[
            [
              MapPin,
              "locations",
              stats?.locations ?? stats?.registered_locations,
              "red",
            ],
            [UsersThree, "contributors", stats?.contributors, "blue"],
            [ShieldCheck, "verified", stats?.verified_locations, "green"],
            [Code, "requests", stats?.api_requests, "violet"],
          ].map(([Icon, key, value, color]) => (
            <div className="stat" key={key}>
              <Icon className={color} weight="fill" size={42} />
              <div>
                <strong>
                  {value === undefined
                    ? "—"
                    : new Intl.NumberFormat(lang).format(value)}
                </strong>
                <span>{t(key)}</span>
              </div>
            </div>
          ))}
        </div>
        <p className="stats-caption">{t("liveStats")}</p>
      </section>
      <section className="how">
        <h2>{t("how")}</h2>
        <p>{t("howSub")}</p>
        <div className="steps">
          {[
            [UsersThree, "community", "communityDesc", "blue"],
            [Crosshair, "gps", "gpsDesc", "red"],
            [Stack, "dedupe", "dedupeDesc", "cyan"],
            [Code, "apiAccess", "apiDesc", "violet"],
          ].map(([Icon, title, desc, color], i) => (
            <div className="step" key={title}>
              <span className={`step-icon ${color}`}>
                <Icon size={33} weight="duotone" />
              </span>
              <h3>{t(title)}</h3>
              <p>{t(desc)}</p>
              {i < 3 && <ArrowRight className="step-arrow" size={21} />}
            </div>
          ))}
        </div>
      </section>
      <div className="panorama">
        <img
          src="/assets/haiti-panorama.webp" loading="lazy" width="1800" height="600"
          alt="Panorama ilustrativo de Haití: casas coloridas, bahía y Citadelle"
        />
        <div className="panorama-caption">
          <span>
            HAITI TRACKING <b>by Nexovax</b>
          </span>
          <strong>{t("slogan")}</strong>
        </div>
      </div>
      <section className="privacy-strip">
        <ShieldCheck weight="duotone" size={36} />
        <div>
          <h3>{t("privacyNotice")}</h3>
          <p>{t("privacySub")}</p>
        </div>
        <Link to="/legal/privacidad">
          {t("privacy")}
          <ArrowRight size={18} />
        </Link>
      </section>
    </>
  );
}
