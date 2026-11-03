// Netvi's walk around the server: which channel it is in, when it moves on,
// and when it falls asleep. One state per server.
import { ChannelType, PermissionFlagsBits, ActivityType } from 'discord.js';
import { config, inQuietHours } from './config.js';
import { gif, pick } from './anims.js';
import * as brain from './brain.js';

const NO_PINGS = { parse: [] };
const states = new Map();       // guildId -> { channelId, since, asleep, timer }
const lastActivity = new Map(); // channelId -> timestamp of the last human message

export const noteActivity = channelId => lastActivity.set(channelId, Date.now());
export const stateOf = guildId => states.get(guildId);

const minutes = n => n * 60_000;
const isActive = id => !config.activeWindow || Date.now() - (lastActivity.get(id) || 0) < minutes(config.activeWindow);

/** Channel name without emoji, decorations or accents: "¦•📝exámenes-de-ingreso" -> "examenes-de-ingreso". */
export const plainName = name => name.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9-]/g, '');

/** Matches a channel by ID or by (part of) its plain name. */
const nameMatches = (ch, wanted) => ch.id === wanted || (plainName(wanted) && plainName(ch.name).includes(plainName(wanted)));

/** "examenes" -> a clickable link to the server's channel with that name, if there is one. */
export function channelRef(guild, name) {
  const ch = guild?.channels.cache.find(c => c.type === ChannelType.GuildText && plainName(c.name).includes(plainName(name)));
  return ch ? `<#${ch.id}>` : `#${name}`;
}

/** Text channels Netvi may walk into. */
export function walkable(guild) {
  const me = guild.members.me;
  return guild.channels.cache.filter(ch =>
    ch.type === ChannelType.GuildText &&
    (!config.channels.length || config.channels.some(c => nameMatches(ch, c))) &&
    !config.excludeChannels.some(c => nameMatches(ch, c)) &&
    ch.permissionsFor(me)?.has([PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.AttachFiles, PermissionFlagsBits.ReadMessageHistory]),
  );
}

/** Recent human messages in a channel, oldest first, for context. */
export async function recentHistory(channel, { limit = 15, before } = {}) {
  try {
    const msgs = await channel.messages.fetch({ limit, before });
    const cutoff = Date.now() - minutes(90);
    return [...msgs.values()].reverse()
      .filter(m => m.createdTimestamp > cutoff && (m.cleanContent || '').trim())
      .map(m => ({ author: m.author.id === channel.client.user.id ? config.name : (m.member?.displayName || m.author.username), text: m.cleanContent.slice(0, 300) }));
  } catch {
    return [];
  }
}

function setPresence(client, text) {
  client.user.setPresence({ activities: [{ name: 'estado', type: ActivityType.Custom, state: text }], status: 'online' });
}

/** Walks from the current channel into `channel`. */
export async function moveTo(guild, channel, { announce = true } = {}) {
  const st = ensure(guild);
  const from = st.channelId && guild.channels.cache.get(st.channelId);
  if (from?.id === channel.id) return;
  if (announce && from && isActive(from.id)) {
    await from.send({ content: pick([`*se va caminando hacia ${channel}*`, `¡Me voy a dar una vuelta por ${channel}! 👋`, `Bueno, me piro a ${channel}. ¡Hasta luego!`]), files: [gif('leave')], allowedMentions: NO_PINGS }).catch(() => {});
  }
  st.channelId = channel.id;
  st.since = Date.now();
  setPresence(guild.client, `Paseando por #${channel.name}`);
  if (announce) {
    const text = await brain.entrance({ server: guild.name, channel: channel.name, history: await recentHistory(channel, { limit: 10 }) });
    await channel.send({ content: text, files: [gif('arrive')], allowedMentions: NO_PINGS }).catch(() => {});
  }
}

/** Quietly marks Netvi as being in `channel` (used when someone talks to it there). */
export function settleIn(guild, channel) {
  const st = ensure(guild);
  if (st.channelId === channel.id) return;
  st.channelId = channel.id;
  st.since = Date.now();
  if (!st.asleep) setPresence(guild.client, `Paseando por #${channel.name}`);
}

export async function sleep(guild, text) {
  const st = ensure(guild);
  st.asleep = true;
  setPresence(guild.client, 'Durmiendo 💤');
  const ch = guild.channels.cache.get(st.channelId);
  if (ch && text) await ch.send({ content: text, files: [gif('sleep')], allowedMentions: NO_PINGS }).catch(() => {});
}

export async function wake(guild, text) {
  const st = ensure(guild);
  st.asleep = false;
  const ch = guild.channels.cache.get(st.channelId);
  if (ch) {
    setPresence(guild.client, `Paseando por #${ch.name}`);
    if (text) await ch.send({ content: text, files: [gif('wave')], allowedMentions: NO_PINGS }).catch(() => {});
  }
}

/** Picks the next channel, preferring ones where people are talking. */
function nextChannel(guild) {
  const st = ensure(guild);
  const options = [...walkable(guild).values()].filter(ch => ch.id !== st.channelId && isActive(ch.id));
  if (!options.length) return null;
  const weights = options.map(ch => 1 + (Date.now() - (lastActivity.get(ch.id) || 0) < minutes(30) ? 6 : 0));
  let r = Math.random() * weights.reduce((a, b) => a + b, 0);
  return options.find((_, i) => (r -= weights[i]) < 0) || options[0];
}

async function tick(guild) {
  const st = ensure(guild);
  try {
    if (inQuietHours()) {
      if (!st.asleep && !st.manualAwake) await sleep(guild, pick(['*bosteza* Me voy a dormir un rato… 😴', 'Buenas noches, gente 💤']));
    } else if (st.asleep && !st.manualSleep) {
      await wake(guild, pick(['*se despierta y se estira* ¡Buenos días! ☀️', '¡Ya estoy despierto! ¿Qué me he perdido?']));
    } else if (!st.asleep) {
      st.manualAwake = false;
      const here = guild.channels.cache.get(st.channelId);
      // Sometimes it stays and does something where it is; usually it moves on.
      if (here && isActive(here.id) && Math.random() < config.stayChance) {
        const [anim, text] = pick([['dance', '*se pone a bailar solo* 🎶'], ['think', '*se queda pensando en sus cosas* 🤔'], ['idle', '*mira alrededor*'], ['wow', '¡Uy! ¿Qué ha sido eso?']]);
        await here.send({ content: text, files: [gif(anim)], allowedMentions: NO_PINGS }).catch(() => {});
      } else {
        const next = nextChannel(guild);
        if (next) await moveTo(guild, next);
      }
    }
  } catch (err) {
    console.error('[wander]', err);
  }
  schedule(guild);
}

export function schedule(guild, delayMs) {
  const st = ensure(guild);
  clearTimeout(st.timer);
  const span = Math.max(0, config.wanderMax - config.wanderMin);
  st.timer = setTimeout(() => tick(guild), delayMs ?? minutes(config.wanderMin + Math.random() * span));
}

function ensure(guild) {
  if (!states.has(guild.id)) states.set(guild.id, { channelId: null, since: Date.now(), asleep: false, timer: null, manualSleep: false, manualAwake: false });
  return states.get(guild.id);
}

/** Starts the walk in a server: it settles in a channel without spamming and waits for the first move. */
export function start(guild) {
  const st = ensure(guild);
  const first = walkable(guild).first();
  if (first && !st.channelId) settleIn(guild, first);
  schedule(guild, minutes(2));
}
