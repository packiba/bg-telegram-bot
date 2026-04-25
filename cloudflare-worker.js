/**
 * Cloudflare Worker - Proxy for Bulgarian dictionary APIs
 *
 * Bypasses IP blocking by proxying requests through Cloudflare's network.
 * Supports Wiktionary and Chitanka dictionaries.
 *
 * Deploy: https://dash.cloudflare.com/ → Workers & Pages → Create Worker
 */

export default {
  async fetch(request, env, ctx) {
    // Enable CORS for your bot
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle OPTIONS (CORS preflight)
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Only allow GET requests
    if (request.method !== 'GET') {
      return new Response('Method not allowed', { status: 405 });
    }

    const url = new URL(request.url);
    const word = url.searchParams.get('word');
    const source = url.searchParams.get('source') || 'wiktionary';

    if (!word) {
      return new Response(JSON.stringify({ error: 'Missing word parameter' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    try {
      let targetUrl;
      let headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'bg,en-US;q=0.7,en;q=0.3',
      };

      if (source === 'wiktionary') {
        // Wiktionary API request
        targetUrl = `https://bg.wiktionary.org/w/api.php?action=parse&page=${encodeURIComponent(word)}&format=json&prop=wikitext`;
        headers['Accept'] = 'application/json';
      } else if (source === 'chitanka') {
        // Chitanka dictionary
        targetUrl = `https://rechnik.chitanka.info/w/${encodeURIComponent(word)}`;
      } else {
        return new Response(JSON.stringify({ error: 'Invalid source' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json', ...corsHeaders },
        });
      }

      // Fetch from target
      const response = await fetch(targetUrl, { headers });

      // Return response with CORS headers
      const newHeaders = new Headers(response.headers);
      Object.keys(corsHeaders).forEach(key => newHeaders.set(key, corsHeaders[key]));

      return new Response(response.body, {
        status: response.status,
        headers: newHeaders,
      });

    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }
  },
};
