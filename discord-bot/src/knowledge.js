// Answers general-knowledge questions ("¿qué es un agujero negro?", "¿quién
// fue Einstein?", "¿cuál es la capital de Japón?") with a short summary from
// Wikipedia in Spanish, found through DuckDuckGo's free instant-answer API
// (no key needed), with Wikipedia's own search as a fallback.

const UA = 'NetviDiscordBot/1.0 (+https://github.com/Mm129-11a/Claude)';

// Question openings: what is left after them is the topic to look up.
const OPENERS = [
  /^(?:dime |sabes |me puedes decir |puedes decirme |explicame |explica |hablame (?:de|sobre) |cuentame (?:de|sobre) |informacion (?:de|sobre) |busca |investiga )?/,
  /^(?:que (?:es|son|era|eran|fue|fueron|significa|quiere decir)|quien (?:es|fue|era|invento|descubrio|creo|escribio|pinto)|quienes (?:son|fueron|eran)|cual (?:es|era|fue)|cuales (?:son|eran|fueron)|donde (?:esta|queda|estan|se encuentra)|cuando (?:fue|es|nacio|murio|empezo|termino|se creo|se fundo)|como (?:funciona|se hace|se forma|se dice)|por que|porque|para que sirve|de que trata|que paso en|cuant[oa]s?(?= ))\s+/,
];
const ARTICLES = /^(?:el|la|los|las|un|una|unos|unas|lo|del|al)\s+/;

/** Is this message a general-knowledge question? Returns the topic, or null. */
export function knowledgeTopic(norm) {
  const q = norm.replace(/[¿?¡!.]+/g, ' ').replace(/\s+/g, ' ').trim();
  let rest = q.replace(OPENERS[0], '');
  const opened = OPENERS[1].test(rest) || /^(hablame|cuentame|explicame|informacion|busca|investiga)\b/.test(q);
  if (!opened) return null;
  rest = rest.replace(OPENERS[1], '');
  rest = rest.replace(/^(?:[a-zñ]+ )?(?:mide|miden|pesa|pesan|hay|tiene|tienen|vive|viven|dura|duran|cuesta|cuestan)\s+/, m => (/^(?:mide|miden|pesa|pesan|hay|tiene|tienen|vive|viven|dura|duran|cuesta|cuestan)\s+$/.test(m) ? '' : m.split(' ')[0] + ' '));
  for (let i = 0; i < 2; i++) rest = rest.replace(ARTICLES, '');
  rest = rest.replace(/\b(por favor|porfa|plis|pls)\b/g, '').trim();
  // Questions about Netvi itself or the chat ("¿cuántos años tienes?", "¿qué es eso?") are not for Wikipedia.
  if (rest.length < 3 || /^(tu|tus|eso|esto|aquello|hora|dia|fecha)\b/.test(rest) || /\b(tienes|eres|estas|haces|te llamas|te gusta|tu|tus)\b/.test(rest)) return null;
  return rest;
}

async function getJSON(url) {
  const res = await fetch(url, { headers: { 'User-Agent': UA, Accept: 'application/json' }, signal: AbortSignal.timeout(6000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** First 1-2 sentences, at most ~320 characters. */
function shorten(text) {
  const clean = text.replace(/\s*\([^)]*\)/g, '').replace(/\s+/g, ' ').trim();
  const sentences = clean.match(/[^.!?]+[.!?]+/g) || [clean];
  let out = '';
  for (const s of sentences) {
    if ((out + s).length > 320 && out) break;
    out += s;
  }
  return out.length > 340 ? out.slice(0, 337) + '…' : out.trim();
}

async function fromDuckDuckGo(q) {
  const url = `https://api.duckduckgo.com/?${new URLSearchParams({ q, format: 'json', no_html: '1', skip_disambig: '1', kl: 'es-es' })}`;
  const d = await getJSON(url);
  if (d.AbstractText) return { text: shorten(d.AbstractText), url: d.AbstractURL, title: d.Heading };
  if (d.Answer && typeof d.Answer === 'string') return { text: d.Answer, url: d.AbstractURL || null, title: d.Heading };
  return null;
}

async function fromWikipedia(q) {
  const search = await getJSON(`https://es.wikipedia.org/w/api.php?${new URLSearchParams({ action: 'query', list: 'search', srsearch: q, srlimit: '1', format: 'json', utf8: '1' })}`);
  const title = search?.query?.search?.[0]?.title;
  if (!title) return null;
  const page = await getJSON(`https://es.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title.replace(/ /g, '_'))}`);
  if (!page?.extract) return null;
  return { text: shorten(page.extract), url: page.content_urls?.desktop?.page, title };
}

const cache = new Map();   // topic -> answer, so repeated questions do not hit the APIs again

/**
 * Looks up `topic`. Tries the whole topic, then its last part ("cuantos planetas
 * hay en el sistema solar" -> "sistema solar"). Returns { text, url, title } or null.
 */
export async function lookup(topic) {
  if (cache.has(topic)) return cache.get(topic);
  const tail = topic.split(/\b(?:de|del|en|sobre|hay en|tiene)\b/).pop().replace(ARTICLES, '').trim();
  const tries = [...new Set([topic, tail].filter(t => t && t.length > 2))];
  let answer = null;
  for (const q of tries) {
    for (const source of [fromDuckDuckGo, fromWikipedia]) {
      try { answer = await source(q); } catch (err) { console.error(`[saber] ${source.name}: ${err.message}`); }
      if (answer) break;
    }
    if (answer) break;
  }
  if (cache.size > 300) cache.clear();
  cache.set(topic, answer);
  return answer;
}
