// Anonymous page-view counter (§6): POST /api/hit once per route change (debounced 1 s).
// Sends only {route, newDevice}; newDevice = first visit today (ICT) on this browser (localStorage).
// Any failure → counts = null (footer shows "–"), at most one console.warn per session.

const SEEN_KEY = 'kpiSeen';
let timer = null;
let lastRoute = null;
let warned = false;
let disabled = false; // no Functions on this host (404/405/501) → stop trying for this session
let counts; // undefined = pending, null = failed, {total_devices, today_devices}
const listeners = new Set();

export const getCounts = () => counts;
export function onCounts(fn) {
  listeners.add(fn);
}
function emit(c) {
  counts = c;
  for (const fn of listeners) fn(c);
}

/** Today's date in Asia/Bangkok as YYYY-MM-DD. */
export function todayICT() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(),
  );
}

function takeNewDevice() {
  const today = todayICT();
  try {
    const seen = localStorage.getItem(SEEN_KEY);
    localStorage.setItem(SEEN_KEY, today);
    return seen !== today;
  } catch {
    return false; // storage blocked: do not count the device (avoids inflating the count)
  }
}

function fail(msg) {
  if (!warned) {
    warned = true;
    console.warn(`kpi-health: ตัวนับผู้ใช้งานไม่พร้อม (${msg})`);
  }
  emit(null);
}

async function send(route) {
  if (disabled) return emit(null);
  const newDevice = takeNewDevice();
  try {
    const res = await fetch('/api/hit', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ route, newDevice }),
      cache: 'no-store',
    });
    if (!res.ok) {
      if ([404, 405, 501].includes(res.status)) disabled = true;
      if (newDevice) {
        try {
          localStorage.removeItem(SEEN_KEY); // not counted → retry "new device" next time
        } catch {
          /* ignore */
        }
      }
      return fail(`HTTP ${res.status}`);
    }
    const j = await res.json();
    emit({ total_devices: j.total_devices, today_devices: j.today_devices });
  } catch (e) {
    fail(e?.message ?? 'network');
  }
}

/** route = "<indicator>/<level>/<code>" */
export function trackRoute(route) {
  if (route === lastRoute) return;
  lastRoute = route;
  clearTimeout(timer);
  timer = setTimeout(() => send(route), 1000);
}
