// Shared helpers for Pages Functions (no route: this file exports no onRequest* handler).

let schemaReady = false;

/** JSON response; `cache-control: no-store` unless the caller overrides it. */
export function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...headers },
  });
}

/** 405 with an `allow` header, e.g. methodNotAllowed('GET, PUT'). */
export const methodNotAllowed = (allow) => json({ error: 'method not allowed' }, 405, { allow });

/** 503 when the D1 binding `env.DB` is missing. */
export const noDb = () => json({ error: 'no db' }, 503);

/**
 * Read and parse a JSON request body, limited to `maxBytes` (UTF-8 bytes; Content-Length is checked first).
 * Returns {body} on success or {error: Response} (413 too large / 400 invalid JSON) with the given messages.
 */
export async function readJsonBody(request, maxBytes, { tooLarge = 'body too large', invalid = 'invalid json' } = {}) {
  if (Number(request.headers.get('content-length') ?? 0) > maxBytes) return { error: json({ error: tooLarge }, 413) };
  try {
    const text = await request.text();
    if (new TextEncoder().encode(text).length > maxBytes) return { error: json({ error: tooLarge }, 413) };
    return { body: JSON.parse(text) };
  } catch {
    return { error: json({ error: invalid }, 400) };
  }
}

/** Today's date in Asia/Bangkok as YYYY-MM-DD. */
export function todayICT() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(),
  );
}

/** Create the D1 `hits` table on first use (web_spec_phase2.md §6); memoised per isolate. */
export async function ensureSchema(db) {
  if (schemaReady) return;
  await db
    .prepare(
      'CREATE TABLE IF NOT EXISTS hits(day TEXT, route TEXT, region TEXT, city TEXT, views INTEGER, devices INTEGER, PRIMARY KEY(day, route, region, city))',
    )
    .run();
  schemaReady = true;
}
