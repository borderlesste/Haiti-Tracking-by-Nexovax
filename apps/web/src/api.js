let csrf;
export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}
export async function api(
  path,
  { method = "GET", body, signal, idempotencyKey } = {},
) {
  const headers = { Accept: "application/json" };
  if (method !== "GET") {
    if (!csrf) {
      const r = await fetch("/v1/auth/csrf", { credentials: "same-origin" });
      const j = await r.json();
      csrf = j.data?.csrf_token;
    }
    headers["X-CSRF-Token"] = csrf || "";
    headers["Content-Type"] = "application/json";
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  }
  const response = await fetch(`/v1${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "same-origin",
    signal,
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 403) csrf = undefined;
    throw new ApiError(
      json.error?.message || "No se pudo completar la solicitud.",
      response.status,
      json.error || json.detail,
    );
  }
  return json;
}
export function validNext(value) {
  return typeof value === "string" &&
    value.startsWith("/") &&
    !value.startsWith("//") &&
    !/[\\\u0000-\u0020]/.test(value)
    ? value
    : "/cuenta";
}
export function gpsQuality(accuracy) {
  return !Number.isFinite(accuracy) || accuracy <= 0
    ? "poor"
    : accuracy <= 30
      ? "good"
      : accuracy <= 100
        ? "review"
        : "poor";
}
export function distanceMeters(a, b) {
  if (![a, b].every(p => p && Number.isFinite(p.latitude) && Number.isFinite(p.longitude) && Math.abs(p.latitude) <= 90 && Math.abs(p.longitude) <= 180)) return null;
  const radians = Math.PI / 180;
  const d = Math.sin((a.latitude - b.latitude) * radians / 2) ** 2 + Math.cos(a.latitude * radians) * Math.cos(b.latitude * radians) * Math.sin((a.longitude - b.longitude) * radians / 2) ** 2;
  return 6371008.8 * 2 * Math.asin(Math.sqrt(Math.min(1, d)));
}
export function queryString(values) {
  return new URLSearchParams(
    Object.fromEntries(
      Object.entries(values).filter(
        ([, v]) => v !== "" && v !== null && v !== undefined,
      ),
    ),
  ).toString();
}
export function pageOffset(value) {
  const n = Number(value || 0);
  return Number.isInteger(n) && n >= 0 && n <= 100000 ? n : 0;
}
