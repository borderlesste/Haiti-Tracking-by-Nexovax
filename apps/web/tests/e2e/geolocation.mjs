// Test-only browser API responses: no hardware lookup or permission grant.
export const onSiteGeolocation = `Object.defineProperty(navigator, "geolocation", {
  configurable: true,
  value: { getCurrentPosition(success) {
    success({coords: {latitude: 18.58, longitude: -72.28, accuracy: 18.5}, timestamp: Date.now()});
  } }
});`;

export const deniedGeolocation = `Object.defineProperty(navigator, "geolocation", {
  configurable: true,
  value: { getCurrentPosition(_success, failure) { failure({code: 1}); } }
});`;
