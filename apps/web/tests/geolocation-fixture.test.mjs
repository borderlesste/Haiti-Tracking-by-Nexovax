import test from "node:test";
import assert from "node:assert/strict";
import { runInNewContext } from "node:vm";
import { onSiteGeolocation, deniedGeolocation } from "./e2e/geolocation.mjs";

test("GPS fixture supplies synthetic coordinates and a current timestamp", () => {
  const navigator = {};
  const before = Date.now();
  runInNewContext(onSiteGeolocation, { navigator });
  let received;
  navigator.geolocation.getCurrentPosition(value => { received = value; });
  assert.equal(received.coords.latitude, 18.58);
  assert.equal(received.coords.longitude, -72.28);
  assert.equal(received.coords.accuracy, 18.5);
  assert.ok(received.timestamp >= before && received.timestamp <= Date.now());
});

test("GPS denial fixture calls only the error callback", () => {
  const navigator = {};
  runInNewContext(deniedGeolocation, { navigator });
  let failure;
  navigator.geolocation.getCurrentPosition(() => assert.fail("Unexpected position"), value => { failure = value; });
  assert.equal(failure.code, 1);
});
