const ALLOWED_ORIGIN = 'https://dksbluesky.github.io';
const ALLOWED_QUERY_PARAMS = [
  'period1',
  'period2',
  'interval',
  'events',
  'includeAdjustedClose',
];

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Vary': 'Origin',
  };
}

function jsonError(message, status, origin) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) },
  });
}

export default {
  async fetch(request) {
    const origin = request.headers.get('Origin') || '';

    if (request.method === 'OPTIONS') {
      if (origin !== ALLOWED_ORIGIN) return new Response(null, { status: 403 });
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (request.method !== 'GET') return jsonError('Method not allowed', 405, origin);
    if (origin && origin !== ALLOWED_ORIGIN) return jsonError('Origin not allowed', 403, origin);

    const requestUrl = new URL(request.url);
    const symbol = (requestUrl.searchParams.get('symbol') || '').toUpperCase();
    if (!/^[A-Z0-9.^=-]{1,20}$/.test(symbol)) {
      return jsonError('Invalid symbol', 400, origin || ALLOWED_ORIGIN);
    }

    const yahooUrl = new URL(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`);
    for (const name of ALLOWED_QUERY_PARAMS) {
      const value = requestUrl.searchParams.get(name);
      if (value !== null) yahooUrl.searchParams.set(name, value);
    }

    const upstream = await fetch(yahooUrl, {
      headers: { 'User-Agent': 'Mozilla/5.0 stock-comparison-pwa' },
      cf: { cacheEverything: true, cacheTtl: 300 },
    });

    if (!upstream.ok) {
      return jsonError(`Yahoo upstream HTTP ${upstream.status}`, 502, origin || ALLOWED_ORIGIN);
    }

    return new Response(upstream.body, {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=300',
        ...corsHeaders(origin || ALLOWED_ORIGIN),
      },
    });
  },
};
