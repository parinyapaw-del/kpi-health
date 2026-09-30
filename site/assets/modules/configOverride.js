// Config override (§8.2): GET /api/config → merge the admin's KV override over index.json before render.
// The admin page's live preview posts a draft override via postMessage (same origin only).

const TIMEOUT_MS = 3000;
const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const str = (v) => typeof v === 'string' && v.trim() !== '';

/** Pure: deep clone of `base` with the override applied; malformed parts are ignored. */
export function applyOverride(base, override) {
  const out = structuredClone(base);
  if (!isObj(override)) return out;

  for (const k of ['name', 'org', 'footerNote']) if (str(override[k])) out[k] = override[k];
  if (Number.isInteger(override.currentYear) && (out.years ?? []).map(Number).includes(override.currentYear)) {
    out.currentYear = override.currentYear;
  }

  if (isObj(override.indicators) && isObj(out.indicators)) {
    for (const [id, o] of Object.entries(override.indicators)) {
      const ind = own(out.indicators, id) ? out.indicators[id] : null;
      if (!ind || !isObj(o)) continue;
      if (str(o.name_th)) ind.name_th = o.name_th;
      if (str(o.short)) ind.short = o.short;
      if (Array.isArray(o.cards) && Array.isArray(ind.cards)) {
        o.cards.forEach((label, i) => {
          if (str(label) && isObj(ind.cards[i])) ind.cards[i].label = label;
        });
      }
    }
  }

  if (isObj(override.targets)) {
    for (const [id, years] of Object.entries(override.targets)) {
      const known = own(out.indicators ?? {}, id) || own(out.targets ?? {}, id);
      if (!known || !isObj(years)) continue;
      for (const [year, t] of Object.entries(years)) {
        if (!/^\d{4}$/.test(year) || !isObj(t) || !own(t, 'value')) continue;
        const v = t.value;
        if (v !== null && !(typeof v === 'number' && Number.isFinite(v))) continue;
        out.targets = isObj(out.targets) ? out.targets : {};
        out.targets[id] = isObj(out.targets[id]) ? out.targets[id] : {};
        const existing = out.targets[id][year];
        out.targets[id][year] = v === null ? { value: null } : { ...(isObj(existing) ? existing : {}), value: v };
      }
    }
  }
  return out;
}

/** Fetch the saved override; any failure (no Functions, timeout, bad JSON) → repo defaults with one console.warn. */
export async function loadOverride() {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch('/api/config', { cache: 'no-cache', signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const j = await res.json();
    return { override: isObj(j?.override) ? j.override : {}, googleClientId: typeof j?.googleClientId === 'string' ? j.googleClientId : null };
  } catch (e) {
    console.warn(`kpi-health: ใช้ค่าจาก repo (โหลด /api/config ไม่สำเร็จ: ${e?.name === 'AbortError' ? 'timeout' : e?.message ?? e})`);
    return { override: {}, googleClientId: null };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Live preview: accept {type: 'kpi-config-draft', config} from the same origin only.
 * When framed (the admin preview), tell the parent we are ready so it can send the current draft.
 */
export function listenDraft(onDraft) {
  window.addEventListener('message', (e) => {
    if (e.origin !== location.origin || e.data?.type !== 'kpi-config-draft' || !isObj(e.data.config)) return;
    onDraft(e.data.config);
  });
  if (window.parent !== window) {
    try {
      window.parent.postMessage({ type: 'kpi-config-ready' }, location.origin);
    } catch {
      /* cross-origin parent: ignore */
    }
  }
}
