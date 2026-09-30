// Shared helpers for Pages Functions (no route: this file exports no onRequest* handler).

let schemaReady = false;

/** JSON response; `cache-control: no-store` unless the caller overrides it. */
export function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...headers },
  });
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
