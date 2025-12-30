// Dedicated geolocation helper (separate from chat UI)
// Goal: get the user's current coordinates reliably and provide clear error info.

export function isSecureContextForGeo() {
  // Geolocation typically requires https or localhost.
  return (
    window.isSecureContext === true ||
    location.protocol === 'https:' ||
    location.hostname === 'localhost' ||
    location.hostname === '127.0.0.1'
  );
}

function geolocationErrorToText(err) {
  if (!err) return 'Unknown error';
  const code = err.code;
  if (code === 1) return 'PERMISSION_DENIED';
  if (code === 2) return 'POSITION_UNAVAILABLE';
  if (code === 3) return 'TIMEOUT';
  return err.message || 'Unknown error';
}

function getCurrentPositionAsync(options) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('GEOLOCATION_NOT_SUPPORTED'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => resolve(pos),
      (err) => reject(err),
      options
    );
  });
}

async function maybeCheckPermissions() {
  // Permissions API is not available everywhere.
  if (!navigator.permissions || !navigator.permissions.query) {
    return { state: 'unknown' };
  }

  try {
    const status = await navigator.permissions.query({ name: 'geolocation' });
    return { state: status.state };
  } catch {
    return { state: 'unknown' };
  }
}

export async function getUserLocation({
  timeoutMs = 20000,
  enableHighAccuracy = true,
  maximumAgeMs = 60000
} = {}) {
  const secureOk = isSecureContextForGeo();
  if (!secureOk) {
    const e = new Error('INSECURE_CONTEXT');
    e.details = { protocol: location.protocol, host: location.host };
    throw e;
  }

  const perm = await maybeCheckPermissions();
  // If explicitly denied, fail fast with a clear error.
  if (perm.state === 'denied') {
    const e = new Error('PERMISSION_DENIED');
    e.details = { permissionState: perm.state };
    throw e;
  }

  try {
    const pos = await getCurrentPositionAsync({
      enableHighAccuracy,
      timeout: timeoutMs,
      maximumAge: maximumAgeMs
    });

    const lat = pos?.coords?.latitude;
    const lon = pos?.coords?.longitude;
    const acc = pos?.coords?.accuracy;

    if (typeof lat !== 'number' || typeof lon !== 'number') {
      const e = new Error('INVALID_COORDS');
      e.details = { lat, lon, accuracy: acc };
      throw e;
    }

    return {
      lat,
      lon,
      accuracy: acc,
      source: 'geolocation'
    };
  } catch (err) {
    const codeText = geolocationErrorToText(err);
    const e = new Error(codeText);
    e.details = {
      originalMessage: err?.message,
      originalCode: err?.code,
      permissionState: perm.state,
      secureContext: secureOk
    };
    throw e;
  }
}

export async function getUserLocationWithRetry(retries = 2) {
  const attempts = [];
  const configs = [
    { timeoutMs: 15000, enableHighAccuracy: true, maximumAgeMs: 60000 },
    { timeoutMs: 25000, enableHighAccuracy: true, maximumAgeMs: 0 },
    { timeoutMs: 30000, enableHighAccuracy: false, maximumAgeMs: 0 }
  ];

  const n = Math.max(1, Math.min(configs.length, retries + 1));
  for (let i = 0; i < n; i++) {
    try {
      const loc = await getUserLocation(configs[i]);
      loc.attempts = attempts;
      return loc;
    } catch (e) {
      attempts.push({ attempt: i + 1, error: e?.message, details: e?.details });
      // If user denied, no point retrying
      if (e?.message === 'PERMISSION_DENIED') {
        throw e;
      }
    }
  }

  const final = new Error('GEOLOCATION_FAILED');
  final.details = { attempts };
  throw final;
}
