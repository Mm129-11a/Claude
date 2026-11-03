// Reads settings from the environment (and from a .env file next to package.json, if there is one).
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { existsSync } from 'node:fs';

const envFile = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '.env');
if (existsSync(envFile)) process.loadEnvFile(envFile);

const list = v => (v || '').split(',').map(s => s.trim()).filter(Boolean);
const num = (v, d) => (v === undefined || v === '' || Number.isNaN(Number(v)) ? d : Number(v));

export const config = {
  // Tolerates stray spaces, quotes or a "Bot " prefix pasted along with the token.
  token: (process.env.DISCORD_TOKEN || '').trim().replace(/^["']|["']$/g, '').replace(/^Bot\s+/i, '').trim(),
  anthropicKey: process.env.ANTHROPIC_API_KEY || '',
  model: process.env.CLAUDE_MODEL || 'claude-opus-5-5',
  name: process.env.BOT_NAME || 'Netvi',
  // Words that count as calling the bot by name (case-insensitive).
  nameTriggers: list(process.env.NAME_TRIGGERS || 'netvi,netvy'),
  // Channels it may walk into. Empty = every text channel it can write in.
  channels: list(process.env.WANDER_CHANNELS),
  excludeChannels: list(process.env.EXCLUDE_CHANNELS),
  wanderMin: num(process.env.WANDER_MIN_MINUTES, 25),
  wanderMax: num(process.env.WANDER_MAX_MINUTES, 70),
  // Only wander into / do things in channels where someone wrote in the last N minutes (0 = anywhere).
  activeWindow: num(process.env.ACTIVE_WINDOW_MINUTES, 180),
  quietHours: process.env.QUIET_HOURS || '1-9',        // "start-end" in 24h, empty to disable
  timezone: process.env.TIMEZONE || 'Europe/Madrid',
  reactChance: num(process.env.REACT_CHANCE, 0.06),
  maxRepliesPerHour: num(process.env.MAX_REPLIES_PER_HOUR, 120),
  welcomeChannel: process.env.WELCOME_CHANNEL_ID || '',
};

export function inQuietHours(date = new Date(), quiet = config.quietHours, timeZone = config.timezone) {
  const m = /^(\d{1,2})-(\d{1,2})$/.exec(quiet.trim());
  if (!m) return false;
  const [start, end] = [Number(m[1]), Number(m[2])];
  const hour = Number(new Intl.DateTimeFormat('en-GB', { hour: 'numeric', hourCycle: 'h23', timeZone }).format(date));
  return start <= end ? hour >= start && hour < end : hour >= start || hour < end;
}
