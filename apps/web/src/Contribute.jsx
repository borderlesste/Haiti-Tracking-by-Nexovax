import { useEffect, useState, useRef } from "react";
import {
  MapPin,
  Crosshair,
  ShieldCheck,
  Lightbulb,
  CheckCircle,
  Stack,
  FloppyDisk,
  PaperPlaneTilt,
  Medal,
  Info,
  Images,
  UploadSimple,
} from "@phosphor-icons/react";
import { api, gpsQuality, distanceMeters, queryString } from "./api";
import { useLocale } from "./i18n";
import { Map } from "./Map";
import { useTerritories, TerritoryFields, TypeField } from "./Places";
import { useApp, Gate, Field, Form, Button, Notice, Link, Dialog } from "./ui";
export function Contribute({ id }) {
  return (
    <Gate>
      <ContributionForm id={id} />
    </Gate>
  );
}
function ContributionForm({ id }) {
  const { t } = useLocale();
  const { user, navigate, search } = useApp();
  const targetCode = search.get("code");
  const { items: territories, error: territoryError, retry: retryTerritories } = useTerritories();
  const [department, setDepartment] = useState(""),
    [commune, setCommune] = useState(""),
    [section, setSection] = useState(""),
    [sections, setSections] = useState([]),
    [sectionError, setSectionError] = useState(false),
    [sectionsLoading, setSectionsLoading] = useState(false),
    [sectionRevision, setSectionRevision] = useState(0),
    [extraOpen, setExtraOpen] = useState(false),
    [point, setPoint] = useState(null),
    [gps, setGps] = useState(null),
    [gpsBusy, setGpsBusy] = useState(false),
    [gpsError, setGpsError] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [duplicates, setDuplicates] = useState(null),
    [duplicateBusy, setDuplicateBusy] = useState(false),
    [version, setVersion] = useState(null),
    [initial, setInitial] = useState(null),
    [files, setFiles] = useState([]),
    [confirmed, setConfirmed] = useState(false),
    [recovery, setRecovery] = useState(false);
  const [review, setReview] = useState(null);
  const correctionCode = id ? initial?.target_location_code : initial?.code || targetCode;
  const formRef = useRef();
  const submitMode = useRef("on_site");
  const requestKey = useRef(crypto.randomUUID());
  const savedContribution = useRef(null);
  const uploadedFiles = useRef(new Set());
  useEffect(() => {
    if (!id && !targetCode) return;
    const ac = new AbortController();
    api(
      id
        ? `/me/contributions/${encodeURIComponent(id)}`
        : `/locations/${encodeURIComponent(targetCode)}`,
      { signal: ac.signal },
    )
      .then((j) => {
        const c = { ...j.data.payload, ...j.data };
        setInitial(c);
        if (id) setVersion(c.version);
        setExtraOpen(!!(c.address?.unit_label || c.address?.access_notes || c.parent_location_code || c.access_point_code || c.aliases?.length));
        setPoint(c.selected_point || c.coordinates);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(t("error"));
      });
    return () => ac.abort();
  }, [id, targetCode]);
  useEffect(() => {
    if (!initial || !territories.length) return;
    const ac = new AbortController();
    (async () => {
      const selected = territories.find(x => x.id === initial.territory_id) || (await api(`/territories/${encodeURIComponent(initial.territory_id)}`, {signal: ac.signal})).data;
      const parent = selected.level === "section" ? territories.find(x => x.id === selected.parent_id) : selected;
      if (parent?.level !== "commune") throw new Error("Unavailable commune");
      setCommune(parent.id);
      setDepartment(parent.parent_id);
      setSection(selected.level === "section" ? selected.id : "");
      if (selected.level === "section") setExtraOpen(true);
    })().catch(failure => { if (failure.name !== "AbortError") setError(t("error")); });
    return () => ac.abort();
  }, [initial, territories]);
  useEffect(() => {
    const ac = new AbortController();
    setSections([]);
    setSectionError(false);
    setSectionsLoading(false);
    if (!commune) return () => ac.abort();
    setSectionsLoading(true);
    (async () => {
      let cursor;
      const rows = [];
      do {
        const j = await api(`/territories?${queryString({level: "section", parent_id: commune, limit: 50, cursor})}`, {signal: ac.signal});
        rows.push(...j.data);
        cursor = j.pagination?.next_cursor;
      } while (cursor);
      setSections(rows);
    })().catch(failure => { if (failure.name !== "AbortError") setSectionError(true); })
      .finally(() => { if (!ac.signal.aborted) setSectionsLoading(false); });
    return () => ac.abort();
  }, [commune, sectionRevision]);
  useEffect(() => setDuplicates(null), [point, commune, section]);
  async function locate() {
    setGpsBusy(true);
    setGpsError("");
    if (!navigator.geolocation) {
      setGpsBusy(false);
      setGpsError(t("gpsDenied"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const observation = {
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy_m: pos.coords.accuracy,
          captured_at: new Date(pos.timestamp).toISOString(),
          source: "browser_geolocation",
        };
        setGps(observation);
        setPoint({
          latitude: observation.latitude,
          longitude: observation.longitude,
        });
        setConfirmed(false);
        setGpsBusy(false);
      },
      (failure) => {
        setGpsError(t(({1: "gpsDenied", 2: "gpsUnavailable", 3: "gpsTimeout"})[failure.code] || "error"));
        setGpsBusy(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  }
  async function check(form) {
    const data = new FormData(form);
    if (!data.get("name") || !data.get("type") || !commune || !point) {
      setError(t("required"));
      return;
    }
    setDuplicateBusy(true);
    setError("");
    try {
      const j = await api("/contributions/check-duplicates", {
        method: "POST",
        body: {
          name: data.get("name"),
          type: data.get("type"),
          territory_id: section || commune,
          selected_point: point,
        },
      });
      setDuplicates(j.data.candidates || []);
    } catch {
      setError(t("error"));
    } finally {
      setDuplicateBusy(false);
    }
  }
  async function uploadFiles(contributionId) {
    for (const file of files) {
      const identity = `${file.name}:${file.size}:${file.lastModified}`;
      if (uploadedFiles.current.has(identity)) continue;
      const content_base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = reject;
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.readAsDataURL(file);
      });
      await api(`/me/contributions/${contributionId}/photos`, {
        method: "POST",
        body: { content_base64 },
      });
      uploadedFiles.current.add(identity);
    }
  }
  async function submit(data, reviewed = false) {
    setError("");
    const draft = submitMode.current === "draft";
    if (!point) {
      setError(t("confirmPoint"));
      return;
    }
    if (!draft && (!gps || !confirmed)) {
      setError(t("gpsRequired"));
      return;
    }
    if (!draft && !user.email_verified) {
      setError(t("verifiedEmailRequired"));
      return;
    }
    if (!draft && duplicates === null) {
      setError(t("duplicatesHelp"));
      return;
    }
    const aliases = data.get("aliases").split(/\r?\n/).map(value => value.trim()).filter(Boolean);
    if (aliases.length > 10 || aliases.some(value => value.length > 160)) {
      setError(t("locationAliasesHelp"));
      return;
    }
    if (!draft && !reviewed) { setReview(data); return; }
    setBusy(true);
    try {
      const body = {
        mode: draft ? "draft" : "on_site",
        type: data.get("type"),
        name: data.get("name"),
        territory_id: section || commune,
        selected_point: point,
        address: {
          neighborhood: data.get("neighborhood"),
          street: data.get("street") || null,
          house_number: data.get("house_number") || null,
          unit_label: data.get("unit_label") || null,
          access_notes: data.get("access_notes") || null,
          reference: data.get("reference"),
        },
        description: data.get("description") || "",
        aliases,
        knowledge_source: data.get("knowledge_source"),
        parent_location_code: data.get("parent_location_code") || null,
        access_point_code: data.get("access_point_code") || null,
        gps_observation: draft ? null : gps,
        pin_adjustment_reason: data.get("pin_adjustment_reason") || "",
        source_declaration_accepted: !!data.get("source"),
        duplicate_resolution: {
          choice: correctionCode ? "update_existing" : duplicates?.length ? "distinct_place" : "no_match",
          justification: data.get("justification") || "",
        },
        ...(version ? { version } : {}),
        ...(correctionCode ? { target_location_code: correctionCode } : {}),
      };
      const j = await api(
        id ? `/me/contributions/${encodeURIComponent(id)}` : "/contributions",
        {
          method: id ? "PATCH" : "POST",
          body,
          idempotencyKey: requestKey.current,
        },
      );
      const contributionId = j.data.contribution_id || j.data.id || id;
      savedContribution.current = contributionId;
      await uploadFiles(contributionId);
      navigate("/contribuciones");
    } catch {
      setError(t("error"));
      if (savedContribution.current) { setRecovery(true); setReview(null); }
    } finally {
      setBusy(false);
    }
  }
  const quality = gps ? gpsQuality(gps.accuracy_m) : "noGps";
  const separation = distanceMeters(gps, point);
  return (
    <main className="page contribute-page">
      <div className="page-heading">
        <div className="heading-with-icon">
          <MapPin size={48} weight="fill" className="red" />
          <div>
            <h1>{t(correctionCode ? "proposeCorrection" : "contributeTitle")}</h1>
            <p>{t("contributeSub")}</p>
          </div>
        </div>
        <span className="badge red">
          <Crosshair size={18} />
          {t("gpsRequired")}
        </span>
      </div>
      <div className="contribute-layout">
        <section className="panel contribution-panel" ref={formRef}>
          <Notice tone="error">{error}</Notice>
          {territoryError && <Notice tone="error">{t("error")} <Button type="button" variant="outline" onClick={retryTerritories}>{t("retry")}</Button></Notice>}
          {(id || targetCode) && !initial && !error && (
            <p role="status">{t("loading")}</p>
          )}
          {recovery && (
            <div className="upload-recovery">
              <Notice tone="error">{t("photoRecovery")}</Notice>
              <Button
                busy={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await uploadFiles(savedContribution.current);
                    navigate("/contribuciones");
                  } catch {
                    setError(t("error"));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {t("retry")}
              </Button>
              <Link to="/contribuciones">{t("contributions")}</Link>
            </div>
          )}
          {!recovery && (!(id || targetCode) || initial) && (
            <Form
              noValidate
              onSubmit={data => submit(data)}
              onChange={(e) => {
                if (["name", "type"].includes(e.target.name))
                  setDuplicates(null);
              }}
            >
              <div className="form-grid">
                <TerritoryFields
                  {...{
                    territories,
                    department,
                    setDepartment,
                    commune,
                    setCommune: (value) => { setCommune(value); setSection(""); },
                  }}
                />
                <Field
                  label={t("neighborhood")}
                  name="neighborhood"
                  required
                  maxLength={120}
                  defaultValue={initial?.address?.neighborhood}
                  placeholder="Delmas 33"
                />
                <Field
                  label={t("street")}
                  name="street"
                  maxLength={160}
                  defaultValue={initial?.address?.street}
                  placeholder="Rue Saint-Michel"
                />
                <Field
                  label={t("number")}
                  name="house_number"
                  maxLength={40}
                  defaultValue={initial?.address?.house_number}
                  placeholder="#123"
                />
                <Field
                  label={t("reference")}
                  name="reference"
                  required
                  maxLength={500}
                  defaultValue={initial?.address?.reference}
                />
                <TypeField defaultValue={initial?.type || ""} />
                <Field
                  label={t("placeName")}
                  name="name"
                  required
                  minLength={2}
                  maxLength={160}
                  defaultValue={initial?.name}
                />
              </div>
              <details className="additional-address" open={extraOpen} onToggle={event => setExtraOpen(event.currentTarget.open)}>
                <summary>{t("additionalAddress")}</summary>
                <Field as="select" label={t("sectionOptional")} id="communal_section" value={section} disabled={!commune || sectionsLoading} onChange={event => setSection(event.target.value)}>
                  <option value="">{t(sectionsLoading ? "loading" : "noSection")}</option>
                  {sections.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}
                </Field>
                {sectionError && <Notice tone="error">{t("error")} <Button type="button" variant="outline" onClick={() => setSectionRevision(v => v + 1)}>{t("retry")}</Button></Notice>}
                <Field label={t("unitLabel")} name="unit_label" maxLength={80} defaultValue={initial?.address?.unit_label || ""} />
                <Field as="textarea" label={t("accessNotes")} name="access_notes" maxLength={500} rows={2} defaultValue={initial?.address?.access_notes || ""} />
                <Field label={t("parentLocation")} name="parent_location_code" maxLength={30} pattern="HT-NXV-[A-Za-z0-9-]+" defaultValue={initial?.parent_location_code || ""} />
                <Field label={t("accessPoint")} name="access_point_code" maxLength={30} pattern="HT-NXV-[A-Za-z0-9-]+" defaultValue={initial?.access_point_code || ""} help={t("relationsHelp")} />
                <Field as="textarea" label={t("aliases")} name="aliases" rows={2} maxLength={1610} defaultValue={(initial?.aliases || []).join("\n")} help={t("locationAliasesHelp")} />
              </details>
              <Field as="select" name="knowledge_source" label={t("knowledgeSource")} defaultValue={initial?.knowledge_source || "own_observation"}>
                {["own_observation", "local_representative", "community_reference"].map(value => <option key={value} value={value}>{t(value)}</option>)}
              </Field>
              <Field
                label={t("description")}
                as="textarea"
                name="description"
                maxLength={1000}
                rows={3}
                defaultValue={initial?.description}
              />
              <div className="section-divider">
                <h2>
                  <Crosshair size={22} weight="fill" />
                  {t("coordinates")}
                </h2>
                <Button
                  variant="outline"
                  type="button"
                  busy={gpsBusy}
                  onClick={locate}
                >
                  <Crosshair size={19} />
                  {t("activateGps")}
                </Button>
              </div>
              <p className="help">{t("gpsPrivacy")}</p>
              {gpsBusy && (
                <img
                  className="gps-animation"
                  src="/assets/gps-locating.webp"
                  width="48"
                  height="48"
                  alt=""
                />
              )}
              <Notice tone="error">{gpsError}</Notice>
              <div className="gps-values">
                <div>
                  <label>{t("lat")}</label>
                  <output>{gps?.latitude?.toFixed(6) || "—"}</output>
                </div>
                <div>
                  <label>{t("lon")}</label>
                  <output>{gps?.longitude?.toFixed(6) || "—"}</output>
                </div>
                <div>
                  <label>{t("accuracy")}</label>
                  <output>
                    {gps ? `± ${gps.accuracy_m.toFixed(1)} m` : "—"}
                  </output>
                </div>
              </div>
              <div className="map-field">
                <h3>
                  <MapPin size={23} />
                  {t("confirmPoint")}
                </h3>
                <p>{t("confirmPointSub")}</p>
                <div className="contribution-map">
                  <Map
                    point={point}
                    onPoint={setPoint}
                    gps={gps}
                  />
                </div>
                <div className="form-grid point-inputs">
                  <Field
                    label={t("lat")}
                    id="selected_latitude"
                    type="number"
                    step="any"
                    min={-90}
                    max={90}
                    value={point?.latitude ?? ""}
                    onChange={(e) =>
                      setPoint((p) => ({
                        ...p,
                        latitude: Number(e.target.value),
                        longitude: p?.longitude || -72.33,
                      }))
                    }
                  />
                  <Field
                    label={t("lon")}
                    id="selected_longitude"
                    type="number"
                    step="any"
                    min={-180}
                    max={180}
                    value={point?.longitude ?? ""}
                    onChange={(e) =>
                      setPoint((p) => ({
                        ...p,
                        longitude: Number(e.target.value),
                        latitude: p?.latitude || 18.54,
                      }))
                    }
                  />
                </div>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                  />
                  <span>{t("confirmPoint")}</span>
                </label>
                {separation !== null && <p className="help">{t("pinDistance")}: {Math.round(separation)} m · {t("observedPositionHint")}</p>}
                {separation > 50 && <Field as="textarea" name="pin_adjustment_reason" label={t("pinAdjustmentReason")} required minLength={10} maxLength={1000} rows={2} />}
              </div>
              <div className="duplicate-panel">
                <div className="section-divider">
                  <h3>
                    <Stack size={22} />
                    {t("checkDuplicates")}
                  </h3>
                  <Button
                    type="button"
                    variant="outline"
                    busy={duplicateBusy}
                    onClick={() => check(formRef.current.querySelector("form"))}
                  >
                    <Magnifier />
                    {t("checkDuplicates")}
                  </Button>
                </div>
                <p className="help">{t("duplicatesHelp")}</p>
                {duplicates &&
                  (duplicates.length ? (
                    <>
                      <ul>
                        {duplicates.map((c) => (
                          <li key={c.code}>
                            <Link to={`/ubicaciones/${c.code}`}>
                              {c.name || c.code}
                            </Link>
                            <span>{Math.round(c.distance_m)} m</span>
                            <Link to={`/ubicaciones/${c.code}`}>{t("thisPlace")}</Link>
                            <Link to={`/contribuir/nueva?code=${encodeURIComponent(c.code)}`}>{t("proposeCorrection")}</Link>
                          </li>
                        ))}
                      </ul>
                      <Field
                        as="textarea"
                        label={t(correctionCode ? "correctionReason" : "distinctReason")}
                        name="justification"
                        defaultValue={initial?.duplicate_resolution?.justification || ""}
                        required
                        minLength={10}
                        rows={2}
                        maxLength={1000}
                      />
                    </>
                  ) : (
                    <Notice>{t("noDuplicates")}</Notice>
                  ))}
              </div>
              <div className="upload-panel">
                <h3>
                  <Images size={22} />
                  {t("photos")}
                </h3>
                <label className="upload-zone">
                  <UploadSimple size={28} />
                  <strong>{t("addPhotos")}</strong>
                  <small>JPG, PNG · 5 MB · 5 {t("photos")}</small>
                  <input
                    type="file"
                    accept="image/jpeg,image/png"
                    multiple
                    onChange={(e) => {
                      const chosen = Array.from(e.target.files || []);
                      if (
                        chosen.length > 5 ||
                        chosen.some(
                          (f) =>
                            f.size > 5_000_000 ||
                            !["image/jpeg", "image/png"].includes(f.type),
                        )
                      ) {
                        setError(t("fileError"));
                        e.target.value = "";
                        return;
                      }
                      setFiles(chosen);
                    }}
                  />
                </label>
                <p className="help">{t("photoPolicy")}</p>
                {files.map((f) => (
                  <small key={f.name}>
                    {f.name} · {Math.round(f.size / 1024)} KB
                  </small>
                ))}
              </div>
              <label className="check consent">
                <input
                  type="checkbox"
                  name="source"
                  defaultChecked={initial?.source_declaration_accepted}
                  required
                />
                <span>{t("sourceConsent")}</span>
              </label>
              <div className="form-actions">
                <Button
                  type="submit"
                  variant="outline"
                  busy={busy}
                  onClick={() => (submitMode.current = "draft")}
                >
                  <FloppyDisk size={20} />
                  {t("draft")}
                </Button>
                <Button
                  type="submit"
                  variant="red"
                  busy={busy}
                  onClick={() => (submitMode.current = "on_site")}
                >
                  <PaperPlaneTilt size={20} />
                  {t("send")}
                </Button>
              </div>
            </Form>
          )}
        </section>
        <aside className="contribution-sidebar">
          <section className="panel quality-panel">
            <h2>
              <Medal weight="duotone" size={27} className="gold" />
              {t("quality")}
            </h2>
            <h3>
              {t("accuracy")} <Info size={16} />
            </h3>
            <div className={`quality-state ${quality}`}>
              <Crosshair size={20} />
              {t(quality)}
            </div>
            {gps && <p className="help">± {gps.accuracy_m.toFixed(1)} m</p>}
            <hr />
            <h3>
              <ShieldCheck size={21} weight="fill" className="green" />
              {t("status")}
            </h3>
            <span className="status-pill">{t("pending")}</span>
            <div className="small-note">
              <Info size={20} />
              <p>{t("humanReview")}</p>
            </div>
          </section>
          <section className="panel tips-panel">
            <h3>
              <Lightbulb size={22} className="blue" />
              {t("tips")}
            </h3>
            {["tip1", "tip2", "tip3"].map((k) => (
              <p key={k}>
                <CheckCircle className="green" size={18} weight="fill" />
                {t(k)}
              </p>
            ))}
          </section>
          <section className="panel reward-note">
            <ShieldCheck size={29} />
            <div>
              <strong>{t("recognition")}</strong>
              <p>{t("recognitionDesc")}</p>
            </div>
          </section>
        </aside>
      </div>
      <Dialog title={t("reviewBeforeSend")} open={!!review} onClose={() => { if (!busy) setReview(null); }}>
        {review && <>
          <Notice tone="error">{error}</Notice>
          <h3>{review.get("name")}</h3>
          <dl className="place-data">
            {[["type", t(review.get("type"))], ["commune", territories.find(row => row.id === commune)?.name], ["section", sections.find(row => row.id === section)?.name], ["neighborhood", review.get("neighborhood")], ["street", review.get("street")], ["number", review.get("house_number")], ["reference", review.get("reference")], ["unitLabel", review.get("unit_label")], ["accessNotes", review.get("access_notes")], ["parentLocation", review.get("parent_location_code")], ["accessPoint", review.get("access_point_code")], ["aliases", review.get("aliases")], ["description", review.get("description")], ["coordinates", `${point?.latitude.toFixed(6)}, ${point?.longitude.toFixed(6)}`], ["accuracy", `± ${gps?.accuracy_m.toFixed(1)} m`], ["knowledgeSource", t(review.get("knowledge_source"))], ["photos", String(files.length)]].filter(([, value]) => value).map(([label, value]) => <div key={label}><dt>{t(label)}</dt><dd>{value}</dd></div>)}
          </dl>
          <p>{t("humanReview")}</p>
          <div className="form-actions">
            <Button variant="outline" disabled={busy} onClick={() => setReview(null)}>{t("edit")}</Button>
            <Button variant="red" busy={busy} onClick={() => submit(review, true)}>{t("sendForReview")}</Button>
          </div>
        </>}
      </Dialog>
    </main>
  );
}
function Magnifier() {
  return <Stack size={17} />;
}
