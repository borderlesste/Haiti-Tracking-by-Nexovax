import { useEffect, useState } from "react";
import {
  Code,
  Key,
  Plus,
  ArrowRight,
  ShieldCheck,
  Stack,
  FloppyDisk,
  UserCircle,
  ChartBar,
  MapPin,
  Warning,
  CheckCircle,
  Clock,
  DownloadSimple,
} from "@phosphor-icons/react";
import { api, queryString, pageOffset } from "./api";
import { useLocale } from "./i18n";
import {
  Button,
  Link,
  Form,
  Field,
  PasswordField,
  Notice,
  Dialog,
  Gate,
  useApp,
} from "./ui";
import { Map } from "./Map";
const statusLabels = {
  draft: ["Borrador", "Brouillon", "Bouyon"],
  submitted: ["En revisión", "En révision", "An revizyon"],
  needs_review: ["Revisión requerida", "Révision requise", "Bezwen revizyon"],
  approved: ["Aprobado", "Approuvé", "Apwouve"],
  rejected: ["Rechazado", "Rejeté", "Rejte"],
  changes_requested: [
    "Requiere cambios",
    "Corrections demandées",
    "Bezwen koreksyon",
  ],
  merged: ["Fusionado", "Fusionné", "Fizyone"],
  withdrawn: ["Retirado", "Retiré", "Retire"],
};
function Status({ value }) {
  const { lang } = useLocale();
  return (
    <span className={`badge ${value === "approved" ? "green" : ""}`}>
      {statusLabels[value]?.[{ es: 0, fr: 1, ht: 2 }[lang]] || value}
    </span>
  );
}
function useLoad(path) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [refresh, setRefresh] = useState(0),
    [pagination, setPagination] = useState(null);
  const { t } = useLocale();
  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError("");
    api(path, { signal: ac.signal })
      .then((j) => {
        setData(j.data);
        setPagination(j.pagination);
      })
      .catch((e) => {
        if (e.name !== "AbortError")
          setError(t(e.status === 403 ? "forbidden" : "error"));
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [path, refresh]);
  return {
    data,
    error,
    loading,
    pagination,
    reload: () => setRefresh((x) => x + 1),
  };
}
function Tabs() {
  const { t } = useLocale();
  const { path, user } = useApp();
  return (
    <nav className="workspace-tabs" aria-label={t("account")}>
      {[
        ["/cuenta", "account"],
        ["/contribuciones", "contributions"],
        ["/desarrolladores/panel", "portal"],
        ...(["admin", "moderator"].includes(user?.role)
          ? [["/admin", "admin"]]
          : []),
      ].map(([to, key]) => (
        <Link key={to} className={path === to ? "active" : ""} to={to}>
          {t(key)}
        </Link>
      ))}
    </nav>
  );
}
export function Contributions() {
  return (
    <Gate>
      <ContributionList />
    </Gate>
  );
}
function ContributionList() {
  const { t, lang } = useLocale();
  const { search: pageSearch } = useApp();
  const offset = pageOffset(pageSearch.get("offset"));
  const { data, error, loading, reload } = useLoad(
    `/me/contributions?limit=50&offset=${offset}`,
  );
  const [withdraw, setWithdraw] = useState(null), [busy, setBusy] = useState(false), [failure, setFailure] = useState("");
  return (
    <main className="page">
      <Tabs />
      <div className="page-heading">
        <div>
          <h1>{t("contributions")}</h1>
          <p>{t("humanReview")}</p>
        </div>
        <Link to="/contribuir/nueva" className="button red">
          <Plus size={21} />
          {t("newLocation")}
        </Link>
      </div>
      <Notice tone="error">{error}</Notice>
      <section className="panel">
        {loading ? (
          <p role="status">{t("loading")}</p>
        ) : data?.length ? (
          <div className="contribution-list">
            {data.map((c) => (
              <article key={c.id} className="contribution-row">
                <MapPin size={29} weight="duotone" />
                <div>
                  <h3>{c.payload?.name || c.name}</h3>
                  <p>{c.review_reason || t("humanReview")}</p>
                  <small className="contribution-receipt">{t("contributionId")}: {c.id}<br />{t("date")}: {new Date(c.created_at).toLocaleString({es: "es", fr: "fr", ht: "fr-HT"}[lang])}</small>
                  {c.published_code && (
                    <Link to={`/ubicaciones/${c.published_code}`}>
                      {c.published_code}
                    </Link>
                  )}
                </div>
                <Status value={c.status} />
                {["draft", "submitted", "needs_review", "changes_requested"].includes(c.status) && <Button variant="outline" onClick={() => { setFailure(""); setWithdraw(c); }}>{t("withdraw")}</Button>}
                {["draft", "changes_requested"].includes(c.status) && (
                  <Link className="button outline" to={`/contribuir/${c.id}`}>
                    {t("edit")}
                  </Link>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <Stack size={51} weight="duotone" />
            <h2>{t("noContributions")}</h2>
            <Link to="/contribuir/nueva" className="button">
              {t("newLocation")}
            </Link>
          </div>
        )}
      </section>
      <OffsetPager count={data?.length || 0} loading={loading} />
      <Dialog title={t("withdraw")} open={!!withdraw} onClose={() => { if (!busy) setWithdraw(null); }}>
        <p>{t("withdrawHelp")}</p>
        <Notice tone="error">{failure}</Notice>
        <div className="form-actions">
          <Button variant="outline" disabled={busy} onClick={() => setWithdraw(null)}>{t("cancel")}</Button>
          <Button variant="red" busy={busy} onClick={async () => {
            setBusy(true);
            try { await api(`/me/contributions/${withdraw.id}/withdraw`, {method: "POST", body: {version: withdraw.version}}); setWithdraw(null); reload(); }
            catch (error) { setFailure(t(error.status === 409 ? "conflict" : "error")); }
            finally { setBusy(false); }
          }}>{t("withdraw")}</Button>
        </div>
      </Dialog>
    </main>
  );
}
export function Developers() {
  const { t } = useLocale();
  return (
    <main>
      <section className="api-hero">
        <div>
          <span className="eyebrow">HAITI TRACKING API · V1</span>
          <h1>{t("apiTitle")}</h1>
          <p>{t("apiIntro")}</p>
          <div className="hero-actions">
            <Link className="button red" to="/desarrolladores/panel">
              <Key size={21} />
              {t("portal")}
            </Link>
            <Link
              className="button light-outline"
              to="/desarrolladores/documentacion"
            >
              {t("docs")}
              <ArrowRight size={18} />
            </Link>
          </div>
        </div>
        <div className="code-preview">
          <div className="code-toolbar">
            <span className="code-dot" />
            GET /v1/locations/search
          </div>
          <pre>
            <code>{`curl "$API_ORIGIN/v1/locations/search?q=Delmas" \\\n  -H "Authorization: Bearer $HAITI_TRACKING_API_KEY"\n\n{\n  "success": true,\n  "data": [],\n  "pagination": { "next_cursor": null }\n}`}</code>
          </pre>
          <small>{t("exampleOnly")}</small>
        </div>
      </section>
      <section className="page api-features">
        {[
          ["/v1/locations/search", "search", MapPin],
          ["/v1/locations/nearby", "nearby", Stack],
          ["/v1/territories", "territories", Code],
        ].map(([route, key, Icon]) => (
          <article className="panel" key={route}>
            <Icon size={36} weight="duotone" />
            <h2>{t(key)}</h2>
            <code>GET {route}</code>
            <p>{t("privacySub")}</p>
          </article>
        ))}
      </section>
      <section className="page">
        <div className="panel privacy-strip">
          <ShieldCheck size={36} />
          <div>
            <h2>{t("privacyNotice")}</h2>
            <p>{t("recognitionDesc")}</p>
          </div>
        </div>
      </section>
    </main>
  );
}
export function ApiDocs() {
  const { t } = useLocale();
  const [q, setQ] = useState(""),
    [result, setResult] = useState(),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <main className="page docs-page">
      <Link className="back-link" to="/desarrolladores">
        ← API
      </Link>
      <h1>Haiti Tracking API v1</h1>
      <p>{t("apiIntro")}</p>
      <div className="docs-layout">
        <aside className="panel">
          <h2>{t("docs")}</h2>
          {["search", "nearby", "territories", "keys"].map((k) => (
            <a key={k} href={`#${k}`}>
              {t(k)}
            </a>
          ))}
        </aside>
        <section className="panel">
          <h2 id="search">GET /v1/locations/search</h2>
          <p>
            <code>q</code> · <code>type</code> · <code>territory_id</code> ·{" "}
            <code>limit ≤ 50</code> · <code>cursor</code>
          </p>
          <Form
            noValidate
            onSubmit={async () => {
              setBusy(true);
              setError("");
              try {
                setResult(
                  await api(`/locations/search?q=${encodeURIComponent(q)}`),
                );
              } catch {
                setError(t("error"));
              } finally {
                setBusy(false);
              }
            }}
          >
            <Field
              label={t("search")}
              id="try-query"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Button type="submit" busy={busy}>
              {t("tryApi")}
            </Button>
          </Form>
          <Notice tone="error">{error}</Notice>
          {result && (
            <pre className="json-result">{JSON.stringify(result, null, 2)}</pre>
          )}
          <h2 id="nearby">GET /v1/locations/nearby</h2>
          <p>
            <code>lat</code> · <code>lon</code> · <code>radius_m</code> (1–5000)
            · <code>limit</code>
          </p>
          <h2 id="territories">GET /v1/territories</h2>
          <p>
            <code>parent_id</code> · <code>q</code> · <code>limit</code>
          </p>
          <h2>GET /v1/locations/&#123;code&#125;</h2>
          <p>
            <code>requested_code</code> · <code>canonical_code</code> ·{" "}
            <code>was_redirected</code>
          </p>
          <h2 id="keys">{t("keys")}</h2>
          <p>{t("secretWarning")}</p>
          <pre className="json-result">
            Authorization: Bearer $HAITI_TRACKING_API_KEY
          </pre>
          <p>401 · 403 · 404 · 409 · 422 · 429 / Retry-After</p>
          <Link to="/desarrolladores/panel" className="button outline">
            {t("portal")}
            <ArrowRight size={18} />
          </Link>
          <a href="/openapi.json" target="_blank" rel="noreferrer">
            OpenAPI 3.1 JSON
          </a>
        </section>
      </div>
    </main>
  );
}
export function DeveloperPortal() {
  return (
    <Gate>
      <Portal />
    </Gate>
  );
}
function Portal() {
  const { t } = useLocale();
  const { data, error, loading, reload } = useLoad("/developer/apps");
  const [busy, setBusy] = useState(false),
    [localError, setError] = useState(""),
    [newKey, setNewKey] = useState(null),
    [secret, setSecret] = useState(null),
    [revoke, setRevoke] = useState(null);
  return (
    <main className="page">
      <Tabs />
      <div className="page-heading">
        <div>
          <span className="eyebrow blue">HAITI TRACKING API</span>
          <h1>{t("portal")}</h1>
          <p>{t("secretWarning")}</p>
        </div>
        <Link to="/desarrolladores/documentacion" className="button outline">
          {t("docs")}
        </Link>
      </div>
      <Notice tone="error">{error || localError}</Notice>
      <section className="panel app-create">
        <h2>{t("createApp")}</h2>
        <Form
          noValidate
          className="inline-form"
          onSubmit={async (d, f) => {
            setBusy(true);
            setError("");
            try {
              await api("/developer/apps", {
                method: "POST",
                body: { name: d.get("name"), environment: "test" },
              });
              f.reset();
              reload();
            } catch {
              setError(t("error"));
            } finally {
              setBusy(false);
            }
          }}
        >
          <Field
            label={t("appName")}
            name="name"
            required
            minLength={2}
            maxLength={100}
          />
          <Button type="submit" busy={busy}>
            <Plus size={20} />
            {t("createApp")}
          </Button>
        </Form>
      </section>
      {secret && (
        <section className="panel secret-panel">
          <Notice>{t("secretWarning")}</Notice>
          <code>{secret}</code>
          <Button variant="outline" onClick={() => setSecret(null)}>
            {t("close")}
          </Button>
        </section>
      )}
      <h2>{t("apps")}</h2>
      {loading ? (
        <p role="status">{t("loading")}</p>
      ) : data?.length ? (
        data.map((app) => (
          <section className="panel developer-app" key={app.id}>
            <div className="section-divider">
              <h2>
                <Code size={26} />
                {app.name}
              </h2>
              <span className="badge">TEST</span>
            </div>
            <p>
              {t("quota")}: {app.daily_quota} / {t("day")}
            </p>
            <AppUsage id={app.id} />
            <h3>{t("keys")}</h3>
            {app.keys?.map((key) => (
              <div className="key-row" key={key.id}>
                <Key size={20} />
                <code>{key.prefix}…</code>
                <span>{key.revoked ? t("revoked") : t("active")}</span>
                <Button
                  variant="outline"
                  disabled={key.revoked}
                  onClick={() => setRevoke({ app, key })}
                >
                  {t("revoke")}
                </Button>
              </div>
            ))}
            <Button variant="outline" onClick={() => setNewKey(app)}>
              <Key size={18} />
              {t("createKey")}
            </Button>
          </section>
        ))
      ) : (
        <div className="panel empty-state">
          <Code size={48} />
          <p>{t("noApps")}</p>
        </div>
      )}
      <Dialog
        title={t("createKey")}
        open={!!newKey}
        onClose={() => setNewKey(null)}
      >
        <Form
          noValidate
          onSubmit={async (data) => {
            setBusy(true);
            setError("");
            try {
              const j = await api(`/developer/apps/${newKey.id}/keys`, {
                method: "POST",
                body: { password: data.get("password") },
              });
              setSecret(j.data.secret || j.data.key);
              setNewKey(null);
              reload();
            } catch {
              setError(t("error"));
            } finally {
              setBusy(false);
            }
          }}
        >
          <p>{t("secretWarning")}</p>
          <Notice tone="error">{localError}</Notice>
          <PasswordField label={t("password")} />
          <Button busy={busy} type="submit" className="full">
            {t("createKey")}
          </Button>
        </Form>
      </Dialog>
      <Dialog
        title={t("revoke")}
        open={!!revoke}
        onClose={() => setRevoke(null)}
      >
        <p>{t("revokeConfirm")}</p>
        <div className="form-actions">
          <Button variant="outline" onClick={() => setRevoke(null)}>
            {t("cancel")}
          </Button>
          <Button
            variant="red"
            busy={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await api(
                  `/developer/apps/${revoke.app.id}/keys/${revoke.key.id}/revoke`,
                  { method: "POST", body: {} },
                );
                setRevoke(null);
                reload();
              } catch {
                setError(t("error"));
              } finally {
                setBusy(false);
              }
            }}
          >
            {t("revoke")}
          </Button>
        </div>
      </Dialog>
    </main>
  );
}
function AppUsage({ id }) {
  const { data } = useLoad(`/developer/apps/${id}/usage`);
  const { t } = useLocale();
  return (
    <p className="usage">
      <ChartBar size={20} />
      {t("requests")}:{" "}
      {data?.days?.reduce((sum, day) => sum + day.count, 0) ?? 0}
    </p>
  );
}
export function Account() {
  return (
    <Gate>
      <AccountContent />
    </Gate>
  );
}
function AccountContent() {
  const { user, setUser, logout } = useApp();
  const { t } = useLocale();
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  return (
    <main className="page">
      <Tabs />
      <div className="page-heading">
        <div>
          <h1>{t("consentTitle")}</h1>
          <p>{t("sessionHelp")}</p>
        </div>
        <UserCircle size={54} weight="duotone" />
      </div>
      <div className="account-grid">
        <section className="panel">
          <Form
            noValidate
            onSubmit={async (data) => {
              setBusy(true);
              try {
                const j = await api("/me", {
                  method: "PATCH",
                  body: { display_name: data.get("display_name") },
                });
                setUser(j.data);
                setMessage(t("saved"));
              } catch {
                setMessage(t("error"));
              } finally {
                setBusy(false);
              }
            }}
          >
            <Field
              label={t("name")}
              name="display_name"
              defaultValue={user.display_name}
              required
              minLength={2}
              maxLength={100}
            />
            <Field
              label={t("email")}
              name="email"
              value={user.email}
              readOnly
            />
            <span className={`badge ${user.email_verified ? "green" : ""}`}>
              <ShieldCheck size={17} />
              {t(
                user.email_verified ? "emailVerified" : "verifiedEmailRequired",
              )}
            </span>
            <Notice>{message}</Notice>
            <Button className="full" type="submit" busy={busy}>
              <FloppyDisk size={19} />
              {t("save")}
            </Button>
          </Form>
        </section>
        <section className="panel">
          <h2>{t("privacy")}</h2>
          <p>{t("privacySub")}</p>
          <Button
            variant="outline full"
            onClick={async () => {
              try {
                const j = await api("/me/export");
                const url = URL.createObjectURL(
                  new Blob([JSON.stringify(j.data, null, 2)], {
                    type: "application/json",
                  }),
                );
                const a = document.createElement("a");
                a.href = url;
                a.download = "haiti-tracking-data.json";
                a.click();
                URL.revokeObjectURL(url);
              } catch {
                setMessage(t("error"));
              }
            }}
          >
            <DownloadSimple size={20} />
            {t("export")}
          </Button>
          <Link to="/legal/privacidad">{t("privacy")}</Link>
          <Button variant="red full" onClick={logout}>
            {t("logout")}
          </Button>
        </section>
      </div>
      <AccountExtras />
    </main>
  );
}
export function Admin({ section }) {
  return (
    <Gate admin>
      <AdminContent section={section} />
    </Gate>
  );
}
function AdminContent({ section }) {
  const { t } = useLocale();
  const { path, user } = useApp();
  return (
    <main className="page">
      <Tabs />
      <div className="page-heading">
        <div>
          <span className="eyebrow blue">NEXOVAX</span>
          <h1>{t("admin")}</h1>
          <p>{t("humanReview")}</p>
        </div>
      </div>
      <nav className="workspace-tabs">
        {[
          ["/admin", "adminOverview"],
          ["/admin/revision", "moderation"],
          ["/admin/territorios", "territories"],
          ...(user.role === "admin" ? [["/admin/auditoria", "audit"]] : []),
          ["/admin/reportes", "reports"],
          ["/admin/sugerencias", "suggestions"],
        ].map(([to, key]) => (
          <Link key={to} to={to} className={path === to ? "active" : ""}>
            {t(key)}
          </Link>
        ))}
      </nav>
      {!section ? (
        <AdminSummary />
      ) : section === "territorios" ? (
        <AdminTerritories />
      ) : section === "auditoria" ? (
        <AdminAudit />
      ) : section === "reportes" ? (
        <AdminReports />
      ) : section === "sugerencias" ? (
        <AdminSuggestions />
      ) : (
        <ReviewQueue />
      )}
    </main>
  );
}
function AdminSummary() {
  const { t } = useLocale();
  const { data, error, loading, reload } = useLoad("/admin/summary");
  const counts = data?.contributions || {};
  const pending = (counts.submitted || 0) + (counts.needs_review || 0);
  return (
    <>
      <div className="section-divider">
        <div>
          <h2>{t("adminOverview")}</h2>
          <p>{t("summaryHelp")}</p>
        </div>
        <Button variant="outline" onClick={reload} disabled={loading}>
          {t("retry")}
        </Button>
      </div>
      <Notice tone="error">{error}</Notice>
      {loading ? (
        <p role="status">{t("loading")}</p>
      ) : data && !error ? (
        <>
          <div className="account-grid">
            {[
              ["pendingReview", pending, "/admin/revision"],
              ["publicLocations", data.public_locations, "/mapa"],
              ["openReports", data.open_reports, "/admin/reportes"],
              ["pendingSuggestions", data.pending_suggestions, "/admin/sugerencias"],
            ].map(([key, value, to]) => (
              <section className="panel" key={key}>
                <h3>{t(key)}</h3>
                <strong>{Number.isInteger(value) ? value : "—"}</strong>
                <Link to={to}>{t(key)} <ArrowRight size={15} /></Link>
              </section>
            ))}
          </div>
          <section className="panel extra-panels">
            <h2>{t("adminAlerts")}</h2>
            {data.open_reports > 0 ? (
              <Notice>
                <Warning size={20} /> {t("pendingReportsHelp")}{" "}
                <Link to="/admin/reportes">{t("reports")} ({data.open_reports})</Link>
              </Notice>
            ) : <p>{t("noPending")}</p>}
            {data.pending_suggestions > 0 && (
              <p><Link to="/admin/sugerencias">{t("pendingSuggestions")} ({data.pending_suggestions})</Link></p>
            )}
            {data.cash_rewards_enabled === false && <p>{t("recognitionDesc")}</p>}
          </section>
          <section className="panel extra-panels">
            <h2>{t("statusBreakdown")}</h2>
            <p>{t("totalContributions")}: {Object.values(counts).reduce((total, value) => total + value, 0)}</p>
            {Object.keys(counts).length ? (
              <div className="table-scroll">
                <table>
                  <thead><tr><th>{t("status")}</th><th>{t("contributions")}</th></tr></thead>
                  <tbody>{Object.entries(counts).map(([status, count]) => (
                    <tr key={status}><td><Status value={status} /></td><td>{count}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            ) : <p>{t("noContributions")}</p>}
          </section>
          <section className="panel extra-panels">
            <h2>{t("territoryCounts")}</h2>
            <p>{t("coverageHelp")}</p>
            {data.territory_counts?.length ? <div className="table-scroll"><table>
              <thead><tr><th>{t("territories")}</th><th>{t("publicLocations")}</th></tr></thead>
              <tbody>{data.territory_counts.map(row => <tr key={row.id}><td>{row.name} <code>{row.id}</code></td><td>{row.count}</td></tr>)}</tbody>
            </table></div> : <p>{t("empty")}</p>}
          </section>
        </>
      ) : null}
    </>
  );
}
function ReviewQueue() {
  const { t, lang } = useLocale();
  const { search: pageSearch, navigate } = useApp();
  const offset = pageOffset(pageSearch.get("offset"));
  const status = pageSearch.get("status") || "";
  const { data, error, loading, reload } = useLoad(
    `/admin/contributions?${queryString({ limit: 50, offset, status })}`,
  );
  const [selected, setSelected] = useState(null),
    [busy, setBusy] = useState(false),
    [failure, setFailure] = useState("");
  return (
    <>
      <Field as="select" id="review-status" label={t("status")} value={status}
        onChange={(event) => navigate(`/admin/revision?${queryString({ status: event.target.value })}`, { scroll: false })}>
        <option value="">{t("all")}</option>
        {["submitted", "needs_review", "changes_requested", "approved", "rejected", "merged"].map((value) => (
          <option value={value} key={value}>{statusLabels[value][{ es: 0, fr: 1, ht: 2 }[lang]]}</option>
        ))}
      </Field>
      <Notice tone="error">{error}</Notice>
      {loading ? (
        <p role="status">{t("loading")}</p>
      ) : data?.length ? (
        data.map((c) => (
          <article className="panel review-card" key={c.id}>
            <div className="section-divider">
              <h2>{c.payload?.name || c.name}</h2>
              <Status value={c.status} />
            </div>
            <p>{c.payload?.address?.reference}</p>
            <p>{t("knowledgeSource")}: {t(c.payload?.knowledge_source || "own_observation")}</p>
            {c.payload?.pin_adjustment_reason && <p>{t("pinAdjustmentReason")}: {c.payload.pin_adjustment_reason}</p>}
            {["parent_location_code", "access_point_code"].map(key => c.payload?.[key] && <p key={key}><Link to={`/ubicaciones/${encodeURIComponent(c.payload[key])}`}>{c.payload[key]}</Link></p>)}
            {c.payload?.quality_flags?.length > 0 && (
              <Notice>
                {c.payload.quality_flags
                  .map((flag) =>
                    t(
                      flag === "territory_boundary_mismatch"
                        ? "territoryMismatch"
                        : "review",
                    ),
                  )
                  .join(" · ")}
              </Notice>
            )}
            {c.payload?.gps_observation && (
              <p>
                {t("accuracy")}: ± {c.payload.gps_observation.accuracy_m} m
              </p>
            )}
            {c.payload?.duplicate_candidates?.map((candidate) => (
              <p key={candidate.code}>
                <Link to={`/ubicaciones/${candidate.code}`}>
                  {candidate.name}
                </Link>{" "}
                · {candidate.distance_m} m
              </p>
            ))}
            <code>{c.id}</code>
            <p>{c.review_reason}</p>
            {c.payload?.selected_point && (
              <div className="review-map">
                <Map point={c.payload.selected_point} />
              </div>
            )}
            <ReviewPhotos id={c.id} />
            <div className="form-actions">
              {(["submitted", "needs_review"].includes(c.status)
                ? [
                    ["approve", "approve"],
                    ["request_changes", "changes"],
                    ["merge", "merge"],
                    ["reject", "reject"],
                  ]
                : []
              ).map(([decision, key]) => (
                <Button
                  key={decision}
                  variant={decision === "reject" ? "outline" : "primary"}
                  onClick={() => {
                    setFailure("");
                    setSelected({ c, decision });
                  }}
                >
                  {t(key)}
                </Button>
              ))}
            </div>
          </article>
        ))
      ) : (
        <div className="panel empty-state">
          <CheckCircle size={50} weight="duotone" />
          <h2>{t("noPending")}</h2>
        </div>
      )}
      <OffsetPager count={data?.length || 0} loading={loading} />
      <Dialog
        title={t(
          selected?.decision === "merge"
            ? "merge"
            : selected?.decision === "approve"
              ? "approve"
              : selected?.decision === "reject"
                ? "reject"
                : "changes",
        )}
        open={!!selected}
        onClose={() => setSelected(null)}
      >
        <Form
          noValidate
          onSubmit={async (data) => {
            setBusy(true);
            try {
              await api(`/admin/contributions/${selected.c.id}/decision`, {
                method: "POST",
                body: {
                  decision: selected.decision,
                  reason: data.get("reason"),
                  corroboration: data.get("corroboration") || "",
                  version: selected.c.version,
                  ...(selected.decision === "merge"
                    ? { canonical_code: data.get("canonical_code") }
                    : {}),
                },
              });
              setSelected(null);
              reload();
            } catch {
              setFailure(t("error"));
            } finally {
              setBusy(false);
            }
          }}
        >
          <h3>{selected?.c.payload?.name}</h3>
          {selected?.decision === "merge" && (
            <Field
              label={t("canonicalCode")}
              name="canonical_code"
              required
              pattern="HT-NXV-[A-Za-z0-9-]+"
            />
          )}
          <Notice tone="error">{failure}</Notice>
          {selected?.decision === "approve" && (selected.c.payload?.mode === "remote" || selected.c.payload?.gps_retention_expired || selected.c.payload?.gps_observation?.accuracy_m > 100) && <Field as="textarea" label={t("corroboration")} name="corroboration" required minLength={20} maxLength={1000} rows={3} help={t("corroborationHelp")} />}
          <Field
            label={t("reason")}
            name="reason"
            as="textarea"
            required
            minLength={10}
            maxLength={1000}
            rows={4}
          />
          <div className="form-actions">
            <Button
              type="button"
              variant="outline"
              onClick={() => setSelected(null)}
            >
              {t("cancel")}
            </Button>
            <Button type="submit" busy={busy}>
              {t("save")}
            </Button>
          </div>
        </Form>
      </Dialog>
    </>
  );
}
function AdminTerritories() {
  const { t } = useLocale();
  const { search, navigate, user } = useApp();
  const level = search.get("level") || "department";
  const cursor = search.get("cursor") || "";
  const { data, error, loading, pagination, reload } = useLoad(
    `/territories?${queryString({ level, cursor, limit: 50 })}`,
  );
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");
  function update(values) {
    navigate(`/admin/territorios?${queryString({ level, ...values })}`, {
      replace: true,
      scroll: false,
    });
  }
  return (
    <>
    <section className="panel">
      <div className="section-divider">
        <h2>{t("territories")}</h2>
        {user.role === "admin" && (
          <Button variant="outline" onClick={() => { setMessage(""); setSelected({ level, aliases: [] }); }}>
            <Plus size={18} />{t("createTerritory")}
          </Button>
        )}
        <Field
          as="select"
          label={t("level")}
          id="territory-level"
          value={level}
          onChange={(e) => update({ level: e.target.value, cursor: "" })}
        >
          {["country", "department", "commune", "section"].map((key) => (
            <option key={key} value={key}>
              {t(key)}
            </option>
          ))}
        </Field>
      </div>
      <Notice tone="error">{error}</Notice>
      <Notice>{message}</Notice>
      {user.role !== "admin" && <p>{t("adminOnly")}</p>}
      {loading ? (
        <p role="status">{t("loading")}</p>
      ) : data?.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>{t("name")}</th>
                <th>{t("source")}</th>
                {user.role === "admin" && <th>{t("action")}</th>}
              </tr>
            </thead>
            <tbody>
              {data?.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.name}</td>
                  <td>
                    <a href={row.source_url} target="_blank" rel="noreferrer">
                      {row.source_version}
                    </a>
                  </td>
                  {user.role === "admin" && (
                    <td><Button variant="outline" onClick={() => { setMessage(""); setSelected(row); }}>
                      {t("edit")}
                    </Button></td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !error && <p>{t("noTerritories")}</p>}
      <div className="form-actions">
        <Button
          variant="outline"
          disabled={!cursor || loading}
          onClick={() => update({ cursor: "" })}
        >
          {t("firstPage")}
        </Button>
        <Button
          variant="outline"
          disabled={!pagination?.next_cursor || loading}
          onClick={() => update({ cursor: pagination.next_cursor })}
        >
          {t("nextPage")}
        </Button>
      </div>
    </section>
    <Dialog title={t(selected?.id ? "editTerritory" : "createTerritory")} open={!!selected}
      onClose={() => setSelected(null)}>
      {selected && <TerritoryForm key={selected.id || "new"} territory={selected}
        onCancel={() => setSelected(null)}
        onReload={() => { setSelected(null); reload(); }}
        onSaved={() => { setSelected(null); setMessage(t("saved")); reload(); }} />}
    </Dialog>
    </>
  );
}
function TerritoryForm({ territory, onSaved, onCancel, onReload }) {
  const { t } = useLocale();
  const editing = !!territory.id;
  const [level, setLevel] = useState(territory.level);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const [conflict, setConflict] = useState(false);
  return (
    <Form noValidate onSubmit={async (data, form) => {
      const version = data.get("source_version").trim();
      if (editing && version === territory.source_version) {
        form.elements.source_version.setCustomValidity(t("territoryVersionHelp"));
        setFailure(t("territoryVersionHelp"));
        form.elements.source_version.focus();
        return;
      }
      const aliases = data.get("aliases").split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
      if (aliases.length > 20 || aliases.some((value) => value.length > 120)) {
        setFailure(t("aliasesHelp"));
        form.elements.aliases.focus();
        return;
      }
      setBusy(true);
      setFailure("");
      try {
        const body = {
          name: data.get("name").trim(),
          aliases,
          source_version: version,
          source_url: data.get("source_url").trim(),
          license: data.get("license").trim(),
          ...(editing ? { expected_source_version: territory.source_version } : {
            id: data.get("id").trim(),
            level,
            parent_id: level === "country" ? null : data.get("parent_id").trim() || null,
          }),
        };
        await api(editing ? `/admin/territories/${encodeURIComponent(territory.id)}` : "/admin/territories", {
          method: editing ? "PATCH" : "POST", body,
        });
        onSaved();
      } catch (error) {
        setConflict(editing && error.status === 409);
        setFailure(t(error.status === 409 && editing ? "conflict" : error.status === 422 || error.status === 409 ? "invalidData" : error.status === 403 ? "forbidden" : "error"));
      } finally {
        setBusy(false);
      }
    }}>
      <p>{t(editing ? "territoryEditHelp" : "territoryCreateHelp")}</p>
      {editing ? (
        <p><code>{territory.id}</code> · {t(territory.level)} · {territory.source_version}</p>
      ) : (
        <div className="form-grid">
          <Field label={t("territoryId")} name="id" required minLength={2} maxLength={40}
            pattern="[A-Za-z0-9_-]+" autoComplete="off" />
          <Field as="select" label={t("level")} name="level" value={level}
            onChange={(event) => setLevel(event.target.value)}>
            {["country", "department", "commune", "section"].map((value) => <option key={value} value={value}>{t(value)}</option>)}
          </Field>
          <Field label={t("parentTerritoryId")} name="parent_id" maxLength={40}
            disabled={level === "country"} required={["department", "commune", "section"].includes(level)}
            pattern="[A-Za-z0-9_-]+" autoComplete="off" />
        </div>
      )}
      <Field label={t("territoryName")} name="name" defaultValue={territory.name || ""}
        minLength={2} maxLength={100} required />
      <Field as="textarea" label={t("aliases")} name="aliases" rows={3}
        defaultValue={(territory.aliases || []).join("\n")} help={t("aliasesHelp")} maxLength={2420} />
      <Field label={t("sourceVersion")} name="source_version" defaultValue="" required
        maxLength={200} help={editing ? t("territoryVersionHelp") : undefined}
        onChange={(event) => event.target.setCustomValidity("")} />
      <Field label={t("sourceUrl")} name="source_url" type="url" pattern="https://.*"
        defaultValue={territory.source_url || ""} minLength={8} maxLength={1000} required />
      <Field as="textarea" label={t("license")} name="license" rows={3}
        defaultValue={territory.license || ""} minLength={3} maxLength={1000} required />
      <Notice tone="error">{failure}</Notice>
      <div className="form-actions">
        <Button type="button" variant="outline" disabled={busy} onClick={onCancel}>{t("cancel")}</Button>
        {conflict && <Button type="button" variant="outline" onClick={onReload}>{t("reloadCatalog")}</Button>}
        <Button type="submit" busy={busy} disabled={conflict}>{t("save")}</Button>
      </div>
    </Form>
  );
}
function AdminAudit() {
  const { t, lang } = useLocale();
  const { search: pageSearch, navigate } = useApp();
  const offset = pageOffset(pageSearch.get("offset"));
  const filters = Object.fromEntries(["actor_id", "subject_id", "action"].map((key) => [key, pageSearch.get(key) || ""]));
  const { data, error, loading } = useLoad(
    `/admin/audit?${queryString({ ...filters, limit: 50, offset })}`,
  );
  return (
    <section className="panel">
      <h2>{t("audit")}</h2>
      <Form noValidate key={queryString(filters)} onSubmit={(values) => {
        const next = Object.fromEntries(Object.keys(filters).map((key) => [key, values.get(key).trim()]));
        navigate(`/admin/auditoria?${queryString(next)}`, { scroll: false });
      }}>
        <div className="form-grid">
          <Field label={t("actorId")} name="actor_id" defaultValue={filters.actor_id} maxLength={100} autoComplete="off" />
          <Field label={t("subjectId")} name="subject_id" defaultValue={filters.subject_id} maxLength={100} autoComplete="off" />
          <Field label={t("action")} name="action" defaultValue={filters.action} maxLength={100} autoComplete="off" />
        </div>
        <div className="form-actions">
          <Button type="submit" disabled={loading}>{t("applyFilters")}</Button>
          <Link className="button outline" to="/admin/auditoria">{t("clearFilters")}</Link>
        </div>
      </Form>
      <Notice tone="error">{error}</Notice>
      {loading ? (
        <p>{t("loading")}</p>
      ) : data?.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t("date")}</th>
                <th>{t("action")}</th>
                <th>{t("actorId")}</th>
                <th>{t("subjectId")}</th>
              </tr>
            </thead>
            <tbody>
              {data?.map((x) => (
                <tr key={x.id}>
                  <td>{new Date(x.created_at).toLocaleString({ es: "es", fr: "fr", ht: "fr-HT" }[lang])}</td>
                  <td>{x.action}</td>
                  <td>{x.actor_id || "—"}</td>
                  <td>{x.subject_id || x.object_id || x.entity_id || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !error && <p>{t("noAuditEvents")}</p>}
      <OffsetPager count={data?.length || 0} loading={loading} />
    </section>
  );
}

function AccountExtras() {
  const { t } = useLocale();
  const { user } = useApp();
  const { data, error, reload } = useLoad("/me/sessions");
  const [selected, setSelected] = useState(null),
    [deletion, setDeletion] = useState(false),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  return (
    <div className="account-grid extra-panels">
      <section className="panel">
        <h2>{t("sessions")}</h2>
        <Notice tone="error">{error}</Notice>
        {data?.map((s) => (
          <div className="session-row" key={s.id}>
            <div>
              <strong>{t(s.current ? "currentSession" : "active")}</strong>
              <small>{new Date(s.created_at).toLocaleString()}</small>
            </div>
            {!s.current && (
              <Button variant="outline" onClick={() => setSelected(s)}>
                {t("revoke")}
              </Button>
            )}
          </div>
        ))}
      </section>
      <section className="panel">
        <h2>{t("privacy")}</h2>
        {!user.email_verified && (
          <Button
            variant="outline full"
            busy={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await api("/auth/resend-verification", {
                  method: "POST",
                  body: { email: user.email },
                });
                setMessage(t("checkEmail"));
              } catch {
                setMessage(t("error"));
              } finally {
                setBusy(false);
              }
            }}
          >
            {t("resend")}
          </Button>
        )}
        <p>{t("deletionHelp")}</p>
        <Button variant="outline full" onClick={() => setDeletion(true)}>
          {t("deletion")}
        </Button>
        <Notice>{message}</Notice>
      </section>
      <Dialog
        title={t("revoke")}
        open={!!selected}
        onClose={() => setSelected(null)}
      >
        <p>{t("revokeSessionHelp")}</p>
        <div className="form-actions">
          <Button variant="outline" onClick={() => setSelected(null)}>
            {t("cancel")}
          </Button>
          <Button
            busy={busy}
            variant="red"
            onClick={async () => {
              setBusy(true);
              try {
                await api(`/me/sessions/${selected.id}/revoke`, {
                  method: "POST",
                  body: {},
                });
                setSelected(null);
                reload();
              } catch {
                setMessage(t("error"));
              } finally {
                setBusy(false);
              }
            }}
          >
            {t("revoke")}
          </Button>
        </div>
      </Dialog>
      <Dialog
        title={t("deletion")}
        open={deletion}
        onClose={() => setDeletion(false)}
      >
        <p>{t("deletionHelp")}</p>
        <div className="form-actions">
          <Button variant="outline" onClick={() => setDeletion(false)}>
            {t("cancel")}
          </Button>
          <Button
            variant="red"
            busy={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await api("/me/deletion-request", { method: "POST", body: {} });
                setMessage(t("reportSent"));
                setDeletion(false);
              } catch {
                setMessage(t("error"));
              } finally {
                setBusy(false);
              }
            }}
          >
            {t("deletion")}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

function AdminReports() {
  const { t } = useLocale();
  const { search: pageSearch } = useApp();
  const offset = pageOffset(pageSearch.get("offset"));
  const { data, error, loading, reload } = useLoad(
    `/admin/reports?offset=${offset}`,
  );
  const [selected, setSelected] = useState(null),
    [busy, setBusy] = useState(false),
    [failure, setFailure] = useState("");
  return (
    <>
      <h2>{t("reports")}</h2>
      <Notice tone="error">{error}</Notice>
      {loading ? (
        <p role="status">{t("loading")}</p>
      ) : data?.length ? (
        data.map((r) => (
          <article className="panel report-card" key={r.id}>
            <span className="badge">{r.category}</span>
            <h3>{r.location_code || r.location_id}</h3>
            <p>{r.description}</p>
            <Button variant="outline" onClick={() => setSelected(r)}>
              {t("hide")}
            </Button>
          </article>
        ))
      ) : (
        <section className="panel empty-state">
          <ShieldCheck size={43} />
          <p>{t("noPending")}</p>
        </section>
      )}
      <OffsetPager count={data?.length || 0} loading={loading} />
      <Dialog
        title={t("hide")}
        open={!!selected}
        onClose={() => setSelected(null)}
      >
        <Form
          noValidate
          onSubmit={async (d) => {
            setBusy(true);
            setFailure("");
            try {
              await api(`/admin/locations/${selected.location_id}/hide`, {
                method: "POST",
                body: {
                  category: selected.category,
                  description: d.get("description"),
                },
              });
              setSelected(null);
              reload();
            } catch {
              setFailure(t("error"));
            } finally {
              setBusy(false);
            }
          }}
        >
          <p>{t("hideHelp")}</p>
          <Notice tone="error">{failure}</Notice>
          <Field
            as="textarea"
            name="description"
            label={t("reason")}
            rows={4}
            minLength={10}
            maxLength={1000}
            required
          />
          <div className="form-actions">
            <Button
              type="button"
              variant="outline"
              onClick={() => setSelected(null)}
            >
              {t("cancel")}
            </Button>
            <Button type="submit" variant="red" busy={busy}>
              {t("hide")}
            </Button>
          </div>
        </Form>
      </Dialog>
    </>
  );
}

function AdminSuggestions() {
  const { t } = useLocale();
  const { search: pageSearch } = useApp();
  const offset = pageOffset(pageSearch.get("offset"));
  const { data, error, loading, reload } = useLoad(
    `/admin/suggestions?offset=${offset}`,
  );
  const [selected, setSelected] = useState(null),
    [busy, setBusy] = useState(false),
    [failure, setFailure] = useState("");
  return (
    <>
      <h2>{t("suggestions")}</h2>
      <p>{t("suggestionReviewHelp")}</p>
      <Notice tone="error">{error}</Notice>
      {loading ? (
        <p>{t("loading")}</p>
      ) : data?.length ? (
        data.map((s) => (
          <article className="panel report-card" key={s.id}>
            <h3>{s.payload.name}</h3>
            <p>{s.payload.reference}</p>
            <div className="form-actions">
              <Button
                variant="outline"
                onClick={() => setSelected({ id: s.id, decision: "reviewed" })}
              >
                {t("reviewed")}
              </Button>
              <Button
                variant="outline"
                onClick={() => setSelected({ id: s.id, decision: "rejected" })}
              >
                {t("reject")}
              </Button>
            </div>
          </article>
        ))
      ) : (
        <section className="panel empty-state">
          <p>{t("noPending")}</p>
        </section>
      )}
      <OffsetPager count={data?.length || 0} loading={loading} />
      <Dialog
        title={t("suggestions")}
        open={!!selected}
        onClose={() => setSelected(null)}
      >
        <Form
          noValidate
          onSubmit={async (d) => {
            setBusy(true);
            setFailure("");
            try {
              await api(`/admin/suggestions/${selected.id}/decision`, {
                method: "POST",
                body: { decision: selected.decision, reason: d.get("reason") },
              });
              setSelected(null);
              reload();
            } catch {
              setFailure(t("error"));
            } finally {
              setBusy(false);
            }
          }}
        >
          <Notice tone="error">{failure}</Notice>
          <Field
            as="textarea"
            name="reason"
            label={t("reason")}
            rows={4}
            required
            minLength={10}
            maxLength={1000}
          />
          <Button type="submit" busy={busy} className="full">
            {t("save")}
          </Button>
        </Form>
      </Dialog>
    </>
  );
}

function ReviewPhotos({ id }) {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const { data, error, loading } = useLoad(
    open ? `/admin/contributions/${id}/photos` : "/health",
  );
  return (
    <div className="review-evidence">
      <Button variant="outline" onClick={() => setOpen(!open)}>
        {t(open ? "close" : "photos")}
      </Button>
      {open && (
        <>
          <Notice tone="error">{error}</Notice>
          {loading ? (
            <p>{t("loading")}</p>
          ) : Array.isArray(data) && data.length ? (
            <div className="evidence-grid">
              {data.map((p) => (
                <a
                  key={p.id}
                  href={`/v1/evidence/${p.id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <img
                    src={`/v1/evidence/${p.id}`}
                    alt={t("photos")}
                    width={160}
                    height={120}
                    loading="lazy"
                  />
                </a>
              ))}
            </div>
          ) : (
            <p>{t("noPhotos")}</p>
          )}
        </>
      )}
    </div>
  );
}

function OffsetPager({ count, loading }) {
  const { search, path, navigate } = useApp();
  const { t } = useLocale();
  const offset = pageOffset(search.get("offset"));
  function go(next) {
    const params = new URLSearchParams(search);
    params.set("offset", String(next));
    navigate(`${path}?${params}`, { scroll: false });
  }
  return (
    <div className="list-pager">
      <span>
        {loading
          ? t("loading")
          : `${t("results")}: ${count ? `${offset + 1}–${offset + count}` : "0"}`}
      </span>
      <Button
        variant="outline"
        disabled={!offset || loading}
        onClick={() => go(Math.max(0, offset - 50))}
      >
        {t("previousPage")}
      </Button>
      <Button
        variant="outline"
        disabled={count < 50 || loading || offset >= 100000}
        onClick={() => go(Math.min(100000, offset + 50))}
      >
        {t("nextPage")}
      </Button>
    </div>
  );
}
