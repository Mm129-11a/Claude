// Small web server: Render needs the bot to answer on a port, and the
// Netvy Studios website reads /status to show where Netvi is right now.
import http from 'node:http';
import { config } from './config.js';
import * as wander from './wander.js';

export function startWeb(getClient) {
  const port = Number(process.env.PORT) || 3000;
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 'no-store');
    if (url.pathname === '/status') {
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      return res.end(JSON.stringify(status(getClient())));
    }
    if (url.pathname === '/' || url.pathname === '/health') {
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      return res.end(`${config.name} ${getClient()?.isReady() ? 'está conectado a Discord' : 'no está conectado a Discord todavía'}.\n`);
    }
    res.statusCode = 404;
    res.end('No encontrado\n');
  });
  server.listen(port, () => console.log(`Web de estado en el puerto ${port} (/status)`));
  keepAwake();
  return server;
}

/**
 * Render's free plan stops a web service after 15 minutes without visits,
 * which would disconnect the bot. Visiting our own public URL every 10
 * minutes keeps it running. Render sets RENDER_EXTERNAL_URL; KEEP_AWAKE=0 turns it off.
 */
function keepAwake() {
  const base = process.env.RENDER_EXTERNAL_URL;
  if (!base || process.env.KEEP_AWAKE === '0') return;
  setInterval(() => {
    fetch(new URL('/health', base), { signal: AbortSignal.timeout(20_000) }).catch(err => console.error('[despierto]', err.message));
  }, 10 * 60_000);
  console.log(`Me mantengo despierto visitando ${base} cada 10 minutos.`);
}

/** Public info only: names of channels Netvi is in, never message content or members. */
function status(client) {
  if (!client?.isReady()) return { name: config.name, online: false };
  const places = [...client.guilds.cache.values()].map(guild => {
    const st = wander.stateOf(guild.id);
    const ch = st?.channelId && guild.channels.cache.get(st.channelId);
    return { server: guild.name, channel: ch ? ch.name : null, asleep: Boolean(st?.asleep), since: st?.since || null };
  });
  return { name: config.name, online: true, places };
}
