// Netvi: a 3D mascot that wanders around a Discord server, chats and plays with members.
import { Client, GatewayIntentBits, Partials, Events, ChannelType, SlashCommandBuilder, MessageFlags, InteractionContextType } from 'discord.js';
import { config } from './config.js';
import { gif, pick } from './anims.js';
import * as brain from './brain.js';
import * as wander from './wander.js';
import { startWeb } from './web.js';

let client = null;
startWeb(() => client);

if (!config.token) {
  // Keep the web server up (so a host like Render does not restart in a loop) until the token is set.
  console.error('Falta DISCORD_TOKEN. Ponlo en .env (o en las variables de entorno de Render) y reinicia.');
}

const intents = [
  GatewayIntentBits.Guilds,
  GatewayIntentBits.GuildMessages,
  GatewayIntentBits.MessageContent,
  GatewayIntentBits.GuildMessageReactions,
  GatewayIntentBits.DirectMessages,
];
if (config.welcomeChannel) intents.push(GatewayIntentBits.GuildMembers);

client = new Client({ intents, partials: [Partials.Channel, Partials.Message, Partials.Reaction] });
const NO_PINGS = { parse: [] };

/* ── Slash commands ─────────────────────────────────────────────────── */
const COMMANDS = [
  new SlashCommandBuilder().setName('llamar').setDescription(`${config.name} viene caminando a este canal`),
  new SlashCommandBuilder().setName('saludar').setDescription(`${config.name} te saluda`),
  new SlashCommandBuilder().setName('bailar').setDescription(`${config.name} se pone a bailar`),
  new SlashCommandBuilder().setName('acariciar').setDescription(`Dale cariño a ${config.name}`),
  new SlashCommandBuilder().setName('dormir').setDescription(`Manda a ${config.name} a dormir (deja de pasear)`),
  new SlashCommandBuilder().setName('despertar').setDescription(`Despierta a ${config.name}`),
  new SlashCommandBuilder().setName('donde').setDescription(`¿Dónde está ${config.name} ahora?`),
  new SlashCommandBuilder().setName('pasear').setDescription(`${config.name} se va a pasear a otro canal`),
].map(c => c.setContexts(InteractionContextType.Guild).toJSON());

client.once(Events.ClientReady, async () => {
  console.log(`${config.name} conectado como ${client.user.tag} en ${client.guilds.cache.size} servidor(es). Claude: ${brain.hasClaude ? 'sí' : 'no (frases de reserva)'}`);
  for (const guild of client.guilds.cache.values()) await setUp(guild);
});
client.on(Events.GuildCreate, setUp);

async function setUp(guild) {
  // Per-server commands show up instantly (global ones can take up to an hour).
  await guild.commands.set(COMMANDS).catch(err => console.error(`[comandos] ${guild.name}:`, err.message));
  wander.start(guild);
}

client.on(Events.InteractionCreate, async interaction => {
  if (!interaction.isChatInputCommand() || !interaction.guild) return;
  const { guild, channel, member, commandName } = interaction;
  const who = member?.displayName || interaction.user.username;
  const st = wander.stateOf(guild.id);
  const answer = (content, anim) => interaction.reply({ content, files: anim ? [gif(anim)] : [], allowedMentions: NO_PINGS });

  try {
    switch (commandName) {
      case 'llamar': {
        if (!wander.walkable(guild).has(channel.id)) return interaction.reply({ content: `${config.name} no puede pasear por este canal.`, flags: MessageFlags.Ephemeral });
        if (st?.channelId === channel.id) return answer(`¡Pero si ya estoy aquí, ${who}! 😄`, 'wave');
        if (st?.asleep) { st.asleep = false; st.manualSleep = false; st.manualAwake = true; }
        const from = st?.channelId;
        wander.settleIn(guild, channel);
        wander.schedule(guild);
        return answer(`*${from ? 'viene corriendo' : 'aparece'}* ¡Voy, ${who}! 🏃`, 'arrive');
      }
      case 'saludar':
        wander.settleIn(guild, channel);
        return answer(`¡Hola, ${who}! 👋`, 'wave');
      case 'bailar':
        wander.settleIn(guild, channel);
        return answer(pick(['¡Música, maestro! 🎶', '*se marca unos pasos* 💃', '¡Mira qué estilo!']), 'dance');
      case 'acariciar':
        wander.settleIn(guild, channel);
        return answer(pick([`¡Jeje, gracias ${who}! 💖`, '*se pone contento* 🥰', `¡${who} es mi persona favorita!`]), 'love');
      case 'dormir':
        if (st) { st.manualSleep = true; st.manualAwake = false; }
        await wander.sleep(guild, null);
        return answer('Vale… me echo una siesta. Despiértame con /despertar 😴', 'sleep');
      case 'despertar':
        if (st) { st.manualSleep = false; st.manualAwake = true; }
        await wander.wake(guild, null);
        wander.schedule(guild);
        return answer('*se despierta de golpe* ¡¿Eh?! ¡Estoy aquí! 😳', 'wow');
      case 'donde': {
        const here = st?.channelId && guild.channels.cache.get(st.channelId);
        if (!here) return answer(`Aún no he salido a pasear.`, 'shrug');
        const mins = Math.round((Date.now() - st.since) / 60_000);
        return interaction.reply({ content: `${st.asleep ? 'Estoy durmiendo 💤 en' : 'Estoy en'} ${here} desde hace ${mins} min.`, allowedMentions: NO_PINGS });
      }
      case 'pasear': {
        if (st?.asleep) return answer('Zzz… (está dormido, usa /despertar)', 'sleep');
        const options = [...wander.walkable(guild).values()].filter(ch => ch.id !== st?.channelId);
        if (!options.length) return answer('No hay otro canal por el que pueda pasear.', 'shrug');
        const next = pick(options);
        await interaction.reply({ content: `¡Allá voy! Me voy a ${next} 👋`, files: [gif('leave')], allowedMentions: NO_PINGS });
        wander.settleIn(guild, channel);
        await wander.moveTo(guild, next, { announce: false });
        await next.send({ content: (await brain.entrance({ server: guild.name, channel: next.name, history: await wander.recentHistory(next, { limit: 10 }) })), files: [gif('arrive')], allowedMentions: NO_PINGS }).catch(() => {});
        wander.schedule(guild);
        return;
      }
    }
  } catch (err) {
    console.error(`[/${commandName}]`, err);
    if (!interaction.replied) interaction.reply({ content: 'Ups, me he tropezado. Inténtalo otra vez.', flags: MessageFlags.Ephemeral }).catch(() => {});
  }
});

/* ── Chat ───────────────────────────────────────────────────────────── */
const cooldown = new Map(); // userId -> last time Netvi answered them
const namePattern = new RegExp(`\\b(${config.nameTriggers.map(n => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'i');
const REACTIONS = ['👀', '😂', '🔥', '💯', '😮', '👋', '🫶', '🤔'];

async function isTalkingToMe(message) {
  if (message.channel.type === ChannelType.DM) return true;
  if (message.mentions.users.has(client.user.id)) return true;
  if (namePattern.test(message.content)) return true;
  if (message.reference?.messageId) {
    const ref = await message.fetchReference().catch(() => null);
    if (ref?.author.id === client.user.id) return true;
  }
  return false;
}

client.on(Events.MessageCreate, async message => {
  if (message.author.bot || message.system) return;
  if (message.guild) wander.noteActivity(message.channel.id);

  if (!(await isTalkingToMe(message))) {
    // Not for Netvi: once in a while it reacts to what people say where it is.
    const st = message.guild && wander.stateOf(message.guild.id);
    if (st && !st.asleep && st.channelId === message.channel.id && Math.random() < config.reactChance) {
      message.react(pick(REACTIONS)).catch(() => {});
    }
    return;
  }

  const last = cooldown.get(message.author.id) || 0;
  if (Date.now() - last < 4000) return;
  cooldown.set(message.author.id, Date.now());

  const guild = message.guild;
  const st = guild && wander.stateOf(guild.id);
  if (st?.asleep) {
    if (Math.random() < 0.5) return void message.reply({ content: '*ronca* Zzz… (usa /despertar si quieres hablar conmigo)', files: [gif('sleep')], allowedMentions: { parse: [], repliedUser: false } }).catch(() => {});
    return;
  }
  if (guild && wander.walkable(guild).has(message.channel.id)) wander.settleIn(guild, message.channel);

  message.channel.sendTyping().catch(() => {});
  const text = message.cleanContent.replace(new RegExp(`@${client.user.username}`, 'gi'), config.name).trim() || '(te ha llamado)';
  const { anim, text: said } = await brain.reply({
    server: guild?.name || 'mensajes directos',
    channel: message.channel.name || 'privado',
    history: await wander.recentHistory(message.channel, { limit: 15, before: message.id }),
    author: message.member?.displayName || message.author.globalName || message.author.username,
    text,
  });
  await message.reply({ content: said || '…', files: [gif(anim)], allowedMentions: { parse: [], repliedUser: true } }).catch(err => console.error('[chat]', err.message));
});

/* ── Reactions on Netvi's own messages ──────────────────────────────── */
const LOVE = ['❤️', '💖', '😍', '🥰', '💕', '🫶', '😘'];
client.on(Events.MessageReactionAdd, async (reaction, user) => {
  if (user.bot) return;
  try {
    if (reaction.partial) await reaction.fetch();
    if (reaction.message.author?.id !== client.user.id || reaction.me) return;
    await reaction.message.react(LOVE.includes(reaction.emoji.name) ? '💖' : reaction.emoji);
  } catch { /* emoji from another server or no permission: ignore */ }
});

/* ── Welcome new members (optional, needs the Server Members intent) ── */
client.on(Events.GuildMemberAdd, async member => {
  if (!config.welcomeChannel) return;
  const channel = member.guild.channels.cache.get(config.welcomeChannel);
  if (!channel?.isTextBased()) return;
  wander.settleIn(member.guild, channel);
  await channel.send({
    content: pick([`¡Bienvenid@, ${member}! Soy ${config.name}, la mascota de por aquí 👋`, `*viene corriendo* ¡Hola ${member}! ¡Qué bien que hayas llegado!`]),
    files: [gif('arrive')],
    allowedMentions: { users: [member.id] },
  }).catch(() => {});
});

process.on('unhandledRejection', err => console.error('[error]', err));
if (config.token) {
  client.login(config.token).catch(err => {
    console.error('No he podido conectar con Discord:', err.message);
    process.exit(1);
  });
}
