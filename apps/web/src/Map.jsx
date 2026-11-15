import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerUrl from "leaflet/dist/images/marker-icon.png";
import markerRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
import { useLocale } from "./i18n";
const icon = L.icon({
  iconUrl: markerUrl,
  iconRetinaUrl: markerRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
export function Map({ places = [], point, onPoint, gps, home = false }) {
  const root = useRef(),
    map = useRef(),
    layer = useRef(),
    callback = useRef(onPoint);
  const [tileError, setTileError] = useState(false);
  const { t } = useLocale();
  callback.current = onPoint;
  useEffect(() => {
    const m = L.map(root.current, {
      scrollWheelZoom: false,
      zoomControl: true,
      attributionControl: true,
    }).setView(home ? [19.04, -72.55] : [18.54, -72.33], home ? 7 : 12);
    map.current = m;
    L.tileLayer(
      import.meta.env.VITE_TILE_URL ||
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      },
    )
      .on("tileerror", () => setTileError(true))
      .addTo(m);
    layer.current = L.layerGroup().addTo(m);
    m.on("click", (event) =>
      callback.current?.({
        latitude: event.latlng.lat,
        longitude: event.latlng.lng,
      }),
    );
    const observer = new ResizeObserver(() => m.invalidateSize());
    observer.observe(root.current);
    return () => {
      observer.disconnect();
      m.remove();
      map.current = null;
    };
  }, [home]);
  useEffect(() => {
    if (!layer.current) return;
    layer.current.clearLayers();
    places.forEach((place) => {
      if (!place.coordinates) return;
      const p = L.marker(
        [place.coordinates.latitude, place.coordinates.longitude],
        { icon, title: place.name },
      ).addTo(layer.current);
      const anchor = document.createElement("a");
      anchor.href = `/ubicaciones/${encodeURIComponent(place.code)}`;
      anchor.textContent = place.name;
      p.bindPopup(anchor);
    });
    if (point) {
      const p = L.marker([point.latitude, point.longitude], {
        icon,
        title: t("selectedAccess"),
        alt: t("selectedAccess"),
        draggable: !!onPoint,
      }).addTo(layer.current);
      p.on("dragend", () =>
        callback.current?.({
          latitude: p.getLatLng().lat,
          longitude: p.getLatLng().lng,
        }),
      );
      map.current.setView(
        [point.latitude, point.longitude],
        Math.max(map.current.getZoom(), 15),
      );
    }
    if (gps) {
        L.circle([gps.latitude, gps.longitude], {
          radius: gps.accuracy_m,
          color: "#084cce",
          fillOpacity: 0.1,
          weight: 1,
        }).addTo(layer.current);
        L.circleMarker([gps.latitude, gps.longitude], {radius: 6, color: "white", weight: 2, fillColor: "#084cce", fillOpacity: 1})
          .bindTooltip(t("observedPosition")).addTo(layer.current);
    }
  }, [places, point, gps, onPoint, t]);
  return (
    <div className="map-wrapper">
      <div
        ref={root}
        className="map-canvas"
        role="region"
        aria-label={t("map")}
      />
      {tileError && <div className="map-warning">{t("error")}</div>}
    </div>
  );
}
