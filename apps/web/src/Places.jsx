import { useEffect, useState } from "react";
import {
  MagnifyingGlass,
  MapPin,
  ArrowRight,
  ShieldCheck,
  Copy,
  Flag,
  Plus,
  MapTrifold,
  QrCode,
} from "@phosphor-icons/react";
import { api, queryString } from "./api";
import { useLocale } from "./i18n";
import { Map } from "./Map";
import { Link, useApp, Field, Button, Form, Notice, Dialog } from "./ui";
export function useTerritories() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState(false), [loading, setLoading] = useState(true), [revision, setRevision] = useState(0);
  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError(false);
    Promise.all(
      ["department", "commune"].map(async (level) => {
        const rows = [];
        let cursor;
        do {
          const j = await api(
            `/territories?${queryString({ level, limit: 50, cursor })}`,
            { signal: ac.signal },
          );
          rows.push(...j.data);
          cursor = j.pagination?.next_cursor;
        } while (cursor);
        return rows;
      }),
    )
      .then((groups) => setItems(groups.flat()))
      .catch((failure) => { if (failure.name !== "AbortError") setError(true); })
      .finally(() => { if (!ac.signal.aborted) setLoading(false); });
    return () => ac.abort();
  }, [revision]);
  return { items, loading, error, retry: () => setRevision(v => v + 1) };
}
export function TerritoryFields({
  territories,
  department,
  setDepartment,
  commune,
  setCommune,
}) {
  const { t } = useLocale();
  return (
    <>
      <Field
        as="select"
        label={t("department")}
        id="department"
        value={department}
        required
        onChange={(e) => {
          setDepartment(e.target.value);
          setCommune("");
        }}
      >
        <option value="">{t("choose")}</option>
        {territories
          .filter((x) => x.level === "department")
          .map((x) => (
            <option key={x.id} value={x.id}>
              {x.name}
            </option>
          ))}
      </Field>
      <Field
        as="select"
        label={t("commune")}
        id="territory_id"
        name="territory_id"
        value={commune}
        required
        onChange={(e) => setCommune(e.target.value)}
      >
        <option value="">{t("choose")}</option>
        {territories
          .filter((x) => x.level === "commune" && x.parent_id === department)
          .map((x) => (
            <option key={x.id} value={x.id}>
              {x.name}
            </option>
          ))}
      </Field>
    </>
  );
}
export function TypeField(props) {
  const { t } = useLocale();
  return (
    <Field as="select" label={t("category")} name="type" required {...props}>
      <option value="">{t("choose")}</option>
      {["business", "public", "landmark", "road", "access"].map((x) => (
        <option key={x} value={x}>
          {t(x)}
        </option>
      ))}
    </Field>
  );
}
export function Suggestion({ open, onClose }) {
  const { t } = useLocale();
  const { items: territories, error: territoryError, retry: retryTerritories } = useTerritories();
  const [department, setDepartment] = useState(""),
    [commune, setCommune] = useState(""),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(false),
    [busy, setBusy] = useState(false);
  return (
    <Dialog title={t("suggest")} open={open} onClose={onClose}>
      {success ? (
        <Notice>{t("saved")}</Notice>
      ) : (
        <Form
          noValidate
          onSubmit={async (data) => {
            setBusy(true);
            setError("");
            try {
              await api("/public-suggestions", {
                method: "POST",
                body: {
                  name: data.get("name"),
                  type: data.get("type"),
                  territory_id: commune,
                  reference: data.get("reference"),
                  website: data.get("website") || "",
                  source_declaration_accepted: true,
                },
              });
              setSuccess(true);
            } catch {
              setError(t("error"));
            } finally {
              setBusy(false);
            }
          }}
        >
          <p>{t("suggestionHint")}</p>
          {territoryError && <Notice tone="error">{t("error")} <Button type="button" variant="outline" onClick={retryTerritories}>{t("retry")}</Button></Notice>}
          <Notice tone="error">{error}</Notice>
          <Field
            label={t("placeName")}
            name="name"
            minLength={2}
            maxLength={160}
            required
          />
          <div className="form-grid">
            <TerritoryFields
              {...{
                territories,
                department,
                setDepartment,
                commune,
                setCommune,
              }}
            />
          </div>
          <TypeField />
          <Field
            label={t("reference")}
            as="textarea"
            name="reference"
            required
            minLength={5}
            maxLength={500}
            rows={3}
          />
          <div className="honeypot" aria-hidden="true">
            <input name="website" tabIndex={-1} autoComplete="off" />
          </div>
          <label className="check">
            <input required type="checkbox" />
            <span>{t("sourceConsent")}</span>
          </label>
          <Button busy={busy} type="submit" className="full red">
            {t("suggest")}
          </Button>
        </Form>
      )}
    </Dialog>
  );
}
export function Places() {
  const { t } = useLocale();
  const { search, navigate } = useApp();
  const [query, setQuery] = useState(search.get("q") || "");
  const type = search.get("type") || "";
  const territory = search.get("territory_id") || "";
  const [data, setData] = useState([]),
    [cursor, setCursor] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [suggest, setSuggest] = useState(false);
  const { items: territories, error: territoryError, retry: retryTerritories } = useTerritories();
  const [composition, setComposition] = useState(false);
  function update(values) {
    const p = new URLSearchParams(search);
    Object.entries(values).forEach(([k, v]) => (v ? p.set(k, v) : p.delete(k)));
    navigate(`/mapa?${p.toString()}`, { replace: true, scroll: false });
  }
  useEffect(() => {
    if (composition) return;
    const timer = setTimeout(() => {
      if (query !== (search.get("q") || "")) update({ q: query });
    }, 300);
    return () => clearTimeout(timer);
  }, [query, composition]);
  useEffect(() => {
    setQuery(search.get("q") || "");
    const ac = new AbortController();
    setLoading(true);
    setError("");
    api(
      `/locations/search?${queryString({ q: search.get("q") || "", type, territory_id: territory, limit: "20" })}`,
      { signal: ac.signal },
    )
      .then((j) => {
        setData(j.data);
        setCursor(j.pagination?.next_cursor);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(t("error"));
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [search.toString()]);
  return (
    <main className="page map-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow blue">HAITI TRACKING</span>
          <h1>{t("explore")}</h1>
          <p>{t("slogan")}</p>
        </div>
        <Button variant="red" onClick={() => setSuggest(true)}>
          <Plus size={21} />
          {t("suggest")}
        </Button>
      </div>
      <div className="map-layout">
        <aside className="results-panel">
          <form
            noValidate
            role="search"
            className="search-bar"
            onSubmit={(e) => {
              e.preventDefault();
              update({ q: query });
            }}
          >
            <MagnifyingGlass size={21} />
            <input
              aria-label={t("search")}
              placeholder={t("search")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onCompositionStart={() => setComposition(true)}
              onCompositionEnd={() => setComposition(false)}
            />
            <button className="icon-button" aria-label={t("search")}>
              <ArrowRight size={19} />
            </button>
          </form>
          <div className="map-filters">
            {territoryError && <Notice tone="error">{t("error")} <Button variant="outline" onClick={retryTerritories}>{t("retry")}</Button></Notice>}
            <Field
              as="select"
              label={t("category")}
              id="filter-type"
              value={type}
              onChange={(e) => update({ type: e.target.value })}
            >
              <option value="">{t("all")}</option>
              {["business", "public", "landmark", "road", "access"].map((x) => (
                <option key={x} value={x}>
                  {t(x)}
                </option>
              ))}
            </Field>
            <Field
              as="select"
              label={t("commune")}
              id="filter-territory"
              value={territory}
              onChange={(e) => update({ territory_id: e.target.value })}
            >
              <option value="">{t("all")}</option>
              {territories
                .filter((x) => x.level === "commune")
                .map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name}
                  </option>
                ))}
            </Field>
          </div>
          <div className="result-heading">
            <h2>{t("results")}</h2>
            <span>{data.length}</span>
          </div>
          <Notice tone="error">{error}</Notice>
          {loading ? (
            <p role="status">{t("loading")}</p>
          ) : data.length ? (
            data.map((place) => (
              <Link
                className="place-card"
                key={place.code}
                to={`/ubicaciones/${encodeURIComponent(place.code)}`}
              >
                <span className="place-icon">
                  <MapPin size={27} weight="fill" />
                </span>
                <div>
                  <h3>{place.name}</h3>
                  <p>
                    {place.address?.commune} · {t(place.type)}
                  </p>
                  <small>{place.code}</small>
                </div>
                <ArrowRight size={18} />
              </Link>
            ))
          ) : (
            <div className="empty-state">
              <MapTrifold size={50} weight="duotone" />
              <h3>{t("empty")}</h3>
              <p>{t("emptyHint")}</p>
              <button className="text-button" onClick={() => setSuggest(true)}>
                {t("suggest")}
                <ArrowRight size={17} />
              </button>
            </div>
          )}
          {cursor && (
            <Button
              variant="outline full"
              busy={loading}
              onClick={async () => {
                setLoading(true);
                try {
                  const j = await api(
                    `/locations/search?${queryString({ q: query, type, territory_id: territory, cursor, limit: "20" })}`,
                  );
                  setData((old) => [...old, ...j.data]);
                  setCursor(j.pagination?.next_cursor);
                } catch {
                  setError(t("error"));
                } finally {
                  setLoading(false);
                }
              }}
            >
              {t("loadMore")}
            </Button>
          )}
        </aside>
        <div className="explorer-map">
          <Map home places={data} />
          <div className="map-legend">
            <ShieldCheck size={18} weight="fill" />
            {t("privacyNotice")}
          </div>
        </div>
      </div>
      <Suggestion open={suggest} onClose={() => setSuggest(false)} />
    </main>
  );
}
export function PlaceDetail({ code }) {
  const { t } = useLocale();
  const [place, setPlace] = useState(),
    [error, setError] = useState(""),
    [actionError, setActionError] = useState(""),
    [copied, setCopied] = useState(false),
    [copiedLink, setCopiedLink] = useState(false),
    [share, setShare] = useState(false),
    [qrError, setQrError] = useState(false),
    [report, setReport] = useState(false),
    [busy, setBusy] = useState(false),
    [sent, setSent] = useState(false);
  useEffect(() => {
    const ac = new AbortController();
    api(`/locations/${encodeURIComponent(code)}`, { signal: ac.signal })
      .then((j) => setPlace(j.data))
      .catch((e) => {
        if (e.name !== "AbortError") setError(t("notFound"));
      });
    return () => ac.abort();
  }, [code]);
  if (error)
    return (
      <div className="center-card">
        <h1>{error}</h1>
        <Link to="/mapa">{t("map")}</Link>
      </div>
    );
  if (!place)
    return (
      <p className="page" role="status">
        {t("loading")}
      </p>
    );
  return (
    <main className="page detail-page">
      <Link className="back-link" to="/mapa">
        ← {t("map")}
      </Link>
      <Notice tone="error">{actionError}</Notice>
      <div className="detail-layout">
        <section className="panel">
          <span className="badge green">
            <ShieldCheck size={17} weight="fill" />
            {t(place.is_demo ? "demonstration" : "verified")}
          </span>
          <h1>{place.name}</h1>
          <p>
            {t(place.type)} · {place.address?.commune}
          </p>
          <div className="code-box">
            <code>{place.code}</code>
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(place.code);
                  setCopied(true);
                } catch {
                  setActionError(t("error"));
                }
              }}
            >
              <Copy size={18} />
              {t(copied ? "copied" : "copy")}
            </Button>
          </div>
          <dl className="place-data">
            {[
              ["department", place.address?.department],
              ["commune", place.address?.commune],
              ["section", place.address?.communal_section],
              ["neighborhood", place.address?.neighborhood],
              ["street", place.address?.street],
              ["number", place.address?.house_number],
              ["unitLabel", place.address?.unit_label],
              ["accessNotes", place.address?.access_notes],
              ["reference", place.address?.reference],
              ["description", place.description],
              ["aliases", place.aliases?.join(" · ")],
              ["confidence", `${Math.round(place.confidence_score * 100)}/100 — ${t("confidenceHint")}`],
            ]
              .filter(([, v]) => v)
              .map(([key, value]) => (
                <div key={key}>
                  <dt>{t(key)}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
          </dl>
          {[["parentLocation", place.parent_location_code], ["accessPoint", place.access_point_code]].filter(([, value]) => value).map(([label, value]) => <p key={label}>{t(label)}: <Link to={`/ubicaciones/${encodeURIComponent(value)}`}>{value}</Link></p>)}
          <p>
            {t("lastReviewed")}: {" "}
            {place.last_verified_at &&
              new Intl.DateTimeFormat(undefined, {
                dateStyle: "medium",
              }).format(new Date(place.last_verified_at))}
          </p>
          <Button variant="outline" onClick={() => setReport(true)}>
            <Flag size={18} />
            {t("report")}
          </Button>
          <Button variant="outline" onClick={() => { setActionError(""); setQrError(false); setShare(true); }}>
            <QrCode size={18} /> {t("sharePlace")}
          </Button>
          <Link
            className="button outline"
            to={`/contribuir/nueva?code=${encodeURIComponent(place.code)}`}
          >
            {t("proposeCorrection")}
          </Link>
        </section>
        <div className="detail-map">
          <Map point={place.coordinates} />
        </div>
      </div>
      <Dialog title={t("sharePlace")} open={share} onClose={() => setShare(false)}>
        <h3>{place.name}</h3>
        <p>{t("qrHint")}</p>
        <Notice tone="error">{actionError || (qrError ? t("error") : "")}</Notice>
        {!qrError && <img className="public-qr" width={240} height={240}
          src={`/v1/locations/${encodeURIComponent(place.code)}/qr`} alt={t("publicQr")}
          onError={() => setQrError(true)} />}
        <a className="share-link" href={`/ubicaciones/${encodeURIComponent(place.code)}`}>
          {new URL(`/ubicaciones/${encodeURIComponent(place.code)}`, window.location.origin).href}
        </a>
        <div className="form-actions">
          <Button variant="outline" onClick={async () => {
            try {
              await navigator.clipboard.writeText(new URL(`/ubicaciones/${encodeURIComponent(place.code)}`, window.location.origin).href);
              setCopiedLink(true);
            } catch { setActionError(t("error")); }
          }}><Copy size={18} />{t(copiedLink ? "copied" : "copyLink")}</Button>
          {!qrError && <a className="button outline" href={`/v1/locations/${encodeURIComponent(place.code)}/qr`} download={`${place.code}-qr.png`}>{t("downloadQr")}</a>}
        </div>
      </Dialog>
      <Dialog
        title={t("report")}
        open={report}
        onClose={() => setReport(false)}
      >
        {sent ? (
          <Notice>{t("reportSent")}</Notice>
        ) : (
          <Form
            noValidate
            onSubmit={async (data) => {
              setBusy(true);
              try {
                await api(`/locations/${encodeURIComponent(code)}/reports`, {
                  method: "POST",
                  body: {
                    category: data.get("category"),
                    description: data.get("description"),
                  },
                });
                setSent(true);
              } catch {
                setActionError(t("error"));
              } finally {
                setBusy(false);
              }
            }}
          >
            <Notice tone="error">{actionError}</Notice>
            <Field as="select" name="category" label={t("reason")}>
              <option value="error">{t("report")}</option>
              <option value="privacy">{t("privacy")}</option>
              <option value="duplicate">{t("dedupe")}</option>
            </Field>
            <Field
              as="textarea"
              name="description"
              label={t("description")}
              required
              minLength={5}
              maxLength={1000}
              rows={4}
            />
            <Button busy={busy} type="submit" className="full red">
              {t("report")}
            </Button>
          </Form>
        )}
      </Dialog>
    </main>
  );
}
