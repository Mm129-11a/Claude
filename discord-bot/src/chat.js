// Free conversation engine: works out what a message is about (greeting,
// question, joke request, a choice, the time, roleplay, feelings…) and builds
// an answer for it. Used whenever Claude is not configured.
import { config } from './config.js';

const pick = arr => arr[Math.floor(Math.random() * arr.length)];

/** Lowercase, no accents, no repeated letters ("Holaaa" -> "hola"), no mentions. */
export function normalize(text) {
  return text.toLowerCase()
    .normalize('NFD').replace(/n\u0303/g, 'ñ').replace(/[\u0300-\u036f]/g, '')
    .replace(/<[@#][!&]?\d+>/g, ' ')
    .replace(/@/g, ' ')
    .replace(/(.)\1{2,}/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

const STOP = new Set('que como cual cuales quien donde cuando porque para pero con sin por los las del una uno unos unas este esta esto eso esa ese ahi aqui algo muy mas menos tan tambien todo toda todos todas tiene tienes tengo eres estas esta estoy hay hace haces puedes puede quieres quiero sabes sobre entre desde hasta cosa cosas bien vale pues osea netvi netvy oye hola'.split(' '));

/** The most telling word in a message, to echo it back. */
function keyword(norm) {
  const words = norm.replace(/[^a-zñ0-9 ]/g, ' ').split(' ').filter(w => w.length > 3 && !STOP.has(w));
  return words.sort((a, b) => b.length - a.length)[0] || null;
}

function clockIn(tz, opts) {
  try { return new Intl.DateTimeFormat('es', { timeZone: tz, ...opts }).format(new Date()); } catch { return null; }
}

// Words that introduce an "A or B" question rather than being part of the options.
const CHOICE_FILLER = new Set('pero y entonces bueno vale oye cual cuales que quien elige escoge eliges escoges prefieres prefiere mejor entre de los las el la tu te ti a mas gusta dime netvi netvy'.split(' '));

const JOKES = [
  '¿Qué le dice un bloque de tierra a otro? ¡Qué bajo has caído! 🟫',
  '¿Por qué el agente del FBI se llevó una escalera? Porque el caso estaba en otro nivel 🕵️',
  '¿Cuál es el colmo de un bot? Que lo manden a la papelera de reciclaje 🤖',
  'Le pregunté a un creeper si quería ser mi amigo… y me explotó en la cara 💥',
  '¿Qué hace una abeja en el gimnasio? ¡Zum-ba! 🐝',
  '¿Por qué los pájaros no usan Discord? Porque ya tienen Twitter 🐦',
  'Mi cabeza es un logo de 9 colores. Mi peluquero dice que es imposible de peinar 💇',
];

const RULES = [
  // [test(norm, raw) -> match | null, (ctx, match) -> { anim, text }]
  [n => (/^(?:oye|oie|ey|eh|psst|escucha|mira|disculpa|perdona|amigo|bro)?[!?.,¿¡ ]*$/.test(n) ? true : null),
    c => ({ anim: 'wave', text: pick([`¿Sí, ${c.u}? ¿Me llamabas? 👀`, `¡Aquí estoy, ${c.u}!`, `¡Presente! ¿Qué pasa, ${c.u}?`]) })],

  // Short acknowledgements: "ok", "sí", "no", "vale"…
  [n => /^(ok|okay|oki|vale|va|si|sip|sep|simon|claro|bueno|dale|listo|no|nop|nel|nada|ah|aja|mm+|hmm+)[!?.,¿¡ ]*$/.test(n) || null,
    (c, _m) => ({ anim: 'talk', text: pick(['¡Vale! 👍', `Perfecto, ${c.u} 😄`, '¡Entendido!', 'Ajá 👀 ¿Algo más?']) })],

  // ── This server (FBI roleplay): point people to the right channel ──
  [n => /\b(como (entro|ingreso|me uno|unirme|entrar)|quiero (entrar|ingresar|unirme|ser agente)|postular|postulacion|examen|examenes|prueba de ingreso|ingreso)\b/.test(n) || null,
    c => ({ anim: 'wow', text: `Para entrar al FBI haz el examen en ${c.ref('examenes-de-ingreso')} 📝 Los resultados salen en ${c.ref('resultados')}. ¡Suerte, futuro agente!` })],

  [n => /\b(resultado|resultados|aprobe|aprobado|aprobada|suspendi|reprobe|nota|calificacion)\b/.test(n) || null,
    c => ({ anim: 'think', text: `Los resultados se publican en ${c.ref('resultados')} 🧐 ¡Crucemos los dedos de bloque!` })],

  [n => /\b(regla|reglas|norma|normas|reglamento|reglamentos|prohibido|se puede hacer)\b/.test(n) || null,
    c => ({ anim: 'talk', text: `Las normas están en ${c.ref('reglamentos')} 📖 Léelas bien, que un agente siempre cumple el reglamento 😎` })],

  [n => /\b10-?4\b/.test(n) || null,
    () => ({ anim: 'wave', text: pick(['¡10-4, recibido! 📻', '10-4, agente. Cambio y corto 📻']) })],

  [n => /\b(codigo|codigos|clave|claves|radio|frecuencia)\b/.test(n) || null,
    c => ({ anim: 'talk', text: `Los códigos de radio los tienes en ${c.ref('codigo-radio')} 📻 ¡10-4!` })],

  [n => /\b(permiso|permisos|ausencia|ausente|licencia|vacaciones|no podre venir|no voy a poder)\b/.test(n) || null,
    c => ({ anim: 'talk', text: `Los permisos y ausencias se piden en ${c.ref('permisos')} 🙋 Así los jefes lo tienen en cuenta.` })],

  [n => /\b(soporte|ticket|reportar|reporte|denunciar|tengo un problema|bug|ayuda con)\b/.test(n) || null,
    c => ({ anim: 'think', text: `Para eso mejor abre un ticket en ${c.ref('soporte')} 🛠️ El equipo te ayudará enseguida.` })],

  [n => /\b(formacion|entrenamiento|entrenar|curso|cursos|academia|capacitacion|clase|clases)\b/.test(n) || null,
    c => ({ anim: 'wow', text: `Las formaciones y entrenamientos se organizan en ${c.ref('formacion')} 🎓 ¡A ponerse en forma, agente!` })],

  [n => /\b(rango|rangos|ascenso|ascender|subir de rango|sargento|teniente|capitan|comisario|director|jerarquia)\b/.test(n) || null,
    c => ({ anim: 'think', text: pick([`Los rangos están en ${c.ref('rangos')} 🎖️ Con esfuerzo y buenas actuaciones se sube.`, `Mira ${c.ref('rangos')} para ver la jerarquía, ${c.u}. ¡Tú tienes pinta de futuro director! 😎`]) })],

  [n => /\b(soy nuevo|soy nueva|acabo de entrar|recien llegado|bienvenida|bienvenidas)\b/.test(n) || null,
    c => ({ anim: 'wave', text: `¡Bienvenid@, ${c.u}! 👋 Empieza por ${c.ref('reglamentos')} y, si quieres ser agente, el examen está en ${c.ref('examenes-de-ingreso')}.` })],

  [n => /\b(tonto|idiota|feo|fea|malo|callate|basura|inutil|estupido|pesado|odio)\b/.test(n) || null,
    c => ({ anim: 'shrug', text: pick(['Eso me ha dolido un poquito… pero te perdono 😌', `Vaya, ${c.u}, hoy vienes picante 🌶️`, 'Yo te sigo queriendo igual 💖', '*se pone a llorar en pixeles* 😢']) })],

  [n => /\b(chiste|broma|algo gracioso|hazme reir|cuentame algo)\b/.test(n) || null,
    () => ({ anim: 'dance', text: pick(JOKES) })],

  [n => /\b(dado|tira un dado)\b/.test(n) || null,
    () => ({ anim: 'wow', text: `🎲 ¡Ha salido un **${1 + Math.floor(Math.random() * 6)}**!` })],

  [n => /\b(moneda|cara o cruz|cara o sello)\b/.test(n) || null,
    () => ({ anim: 'wow', text: `🪙 ¡Ha salido **${pick(['cara', 'cruz'])}**!` })],

  // "¿pizza o hamburguesa?", "pero cuál, sushi o tacos?", "elige entre rojo o azul"
  [n => {
    const m = /([a-zñ0-9 ,]{2,60}?)\s+o\s+([a-zñ0-9 ]{2,40}?)\s*[?!.]*$/.exec(n.replace(/[¿¡]/g, ''));
    if (!m || !/\?|elige|escoge|prefieres|mejor|cual|que te gusta mas/.test(n)) return null;
    // Keep only the option itself: drop lead-in words ("pero cuál", "qué prefieres", "elige entre"…).
    const words = m[1].split(/[ ,]+/).filter(Boolean);
    let i = words.length;
    while (i > 0 && !CHOICE_FILLER.has(words[i - 1])) i--;
    const a = words.slice(i).slice(-3).join(' ');
    const b = m[2].trim().split(' ').filter(w => !CHOICE_FILLER.has(w)).join(' ');
    return a && b && a !== b ? [a, b] : null;
  }, (c, [a, b]) => {
    const choice = pick([a, b]);
    return { anim: 'think', text: pick([`Mmm… me quedo con **${choice}** 🤔`, `¡**${choice}**, sin dudarlo!`, `Entre ${a} y ${b}… **${choice}**, fijo.`, `Difícil… pero **${choice}** 😋`]) };
  }],

  // "¿te gusta X?"
  [n => { const m = /\bte gusta(?:n)? (?:el |la |los |las )?([a-zñ0-9 ]{2,30}?)\??$/.exec(n); return m ? m[1] : null; },
    (c, thing) => ({ anim: pick(['love', 'think']), text: pick([`¡Me encanta ${thing}! 😍`, `Mmm… ${thing} está bien, pero prefiero pasear 🚶`, `¿${thing}? ¡Claro que sí!`]) })],

  [n => /\b(que hora|hora es)\b/.test(n) || null,
    () => ({ anim: 'think', text: `Son las **${clockIn(config.timezone, { hour: '2-digit', minute: '2-digit' })}** ⏰` })],

  [n => /\b(que dia|que fecha|dia es hoy)\b/.test(n) || null,
    () => ({ anim: 'think', text: `Hoy es **${clockIn(config.timezone, { weekday: 'long', day: 'numeric', month: 'long' })}** 📅` })],

  [n => /\b(como estas|que tal estas|como te va|como andas|todo bien|que tal)\b/.test(n) || null,
    c => ({ anim: 'wave', text: pick([`¡Genial! Paseando por #${c.channel}. ¿Y tú, ${c.u}?`, '¡Muy bien! Con ganas de dar una vuelta. ¿Y tú qué tal?', 'Pues aquí, con mi cabeza de colores bien puesta 😄 ¿Tú qué tal?']) })],

  [n => /\b(quien eres|que eres|como te llamas|tu nombre|presentate)\b/.test(n) || null,
    () => ({ anim: 'wave', text: `¡Soy ${config.name}! La mascota de Netvy Studios: un muñeco de bloques con el logo como cabeza. Me paseo por los canales y charlo con quien me hable 👋` })],

  [n => /\beres (un |una )?(bot|robot|ia|humano|persona|real)\b/.test(n) || null,
    () => ({ anim: 'shrug', text: pick(['Soy un bot, sí… ¡pero con corazón de bloques! 🤖💖', 'Técnicamente soy un muñeco 3D que vive en Discord. ¿Cuenta como real? 🤔']) })],

  [n => /\b(que haces|que estas haciendo|en que andas)\b/.test(n) || null,
    c => ({ anim: 'idle', text: pick([`Dando una vuelta por #${c.channel} 🚶`, 'Mirando qué se cuece por aquí 👀', 'Nada, aquí paseando… ¿y tú?']) })],

  [n => /\b(donde estas|en que canal)\b/.test(n) || null,
    c => ({ anim: 'wave', text: `¡Estoy aquí, en #${c.channel}! Cada 25 minutos me voy a otro canal 🚶` })],

  [n => /\b(ayuda|comandos|que puedes hacer|que sabes hacer)\b/.test(n) || null,
    () => ({ anim: 'talk', text: 'Puedes usar `/llamar`, `/saludar`, `/bailar`, `/acariciar`, `/dormir`, `/despertar`, `/donde` y `/pasear`. También puedes pedirme un chiste, que tire un dado o una moneda, que elija entre dos cosas o preguntarme la hora 😉' })],

  [n => /\b(gracias|thx|thanks|te lo agradezco)\b/.test(n) || null,
    c => ({ anim: 'love', text: pick([`¡De nada, ${c.u}! 💖`, '¡Para eso estoy! 😄', '¡Cuando quieras!']) })],

  [n => /\b(te quiero|te amo|eres (el|la) mejor|guapo|lindo|bonito|crack|idolo|tqm)\b/.test(n) || null,
    c => ({ anim: 'love', text: pick([`¡Ayy, ${c.u}! Yo también te quiero 💖`, '*se pone rojo… bueno, de todos los colores* 🥰', `¡${c.u} es mi persona favorita del servidor!`]) })],

  [n => /\b(adios|chao|bye|me voy|hasta luego|nos vemos|buenas noches)\b/.test(n) || null,
    c => ({ anim: 'wave', text: pick([`¡Hasta luego, ${c.u}! 👋`, '¡Nos vemos! Pásalo bien 😄', `¡Chao, ${c.u}! Aquí estaré paseando.`]) })],

  [n => /\b(hola|buenas|buenos dias|buenas tardes|hey|ey|holi|saludos|hi|hello|que onda|wenas)\b/.test(n) || null,
    c => ({ anim: 'wave', text: pick([`¡Hola, ${c.u}! 👋`, `¡Buenas, ${c.u}! ¿Qué tal todo?`, `¡Eyy, ${c.u}! ¿Qué se cuenta?`]) })],

  [n => /\b(jaja|jajaja|jsjs|jeje|xd|lol|lmao|jajs)\b|😂|🤣/.test(n) || null,
    () => ({ anim: 'dance', text: pick(['¡Jajaja! 😂', 'JAJA me muero 🤣', '¡Eso ha estado bueno! 😆']) })],

  [n => /\b(triste|mal|deprimid|llorar|lloro|cansad)\w*/.test(n) || null,
    c => ({ anim: 'love', text: pick([`Ánimo, ${c.u}. Aquí tienes un abrazo de bloques 🫂`, 'Si necesitas hablar, aquí estoy 💖', 'Los días malos también pasan. ¡Tú puedes! 💪']) })],

  [n => /\b(feliz|genial|contento|contenta|increible|lo logre|gane)\b/.test(n) || null,
    c => ({ anim: 'wow', text: pick([`¡Qué bien, ${c.u}! 🎉`, '¡Eso hay que celebrarlo! 🥳', '¡Me alegro un montón!']) })],

  [n => /\b(aburrid|que hacemos|no hay nada)\w*/.test(n) || null,
    () => ({ anim: 'dance', text: pick(['¿Y si os pido un chiste? Bueno, os lo cuento yo: ' + pick(JOKES), '¡Hagamos una fiesta! Usad `/bailar` 🎶', 'Tirad un dado y el que saque menos invita 🎲']) })],

  [n => /\b(baila|bailar|fiesta|musica|cancion)\b/.test(n) || null,
    () => ({ anim: 'dance', text: pick(['¡A bailar! 🎶', 'Mira qué pasos 💃', '¡Música, maestro!']) })],

  [n => /\b(dormir|sueno|duerme|zzz|siesta)\b/.test(n) || null,
    () => ({ anim: 'sleep', text: pick(['Zzz… ¿eh? ¡Estoy despierto! 😴', 'Yo duermo de 1 a 9, como un campeón 💤']) })],

  [n => /\b(hambre|comer|comida|pizza|tacos|hamburguesa|cena|almuerzo|desayuno)\b/.test(n) || null,
    () => ({ anim: 'wow', text: pick(['¡Ñam! Yo solo como píxeles, pero eso suena delicioso 🍕', 'No me hables de comida que me da hambre 🤤', '¡Invítame! Bueno… no puedo comer, pero acompaño 😅']) })],

  [n => /\b(fbi|agente|caso|mision|sospechoso|arresto|arrestar|investigar|investigacion|operativo|criminal|detective|evidencia|placa|patrulla)\b/.test(n) || null,
    c => ({ anim: 'think', text: pick([`*se pone las gafas de agente* 🕶️ Cuéntame los detalles del caso, ${c.u}.`, 'El FBI nunca duerme… bueno, yo sí, de 1 a 9 😴🕵️', 'Recibido, agente. Me pongo a investigar 🔎', '¡Sospechoso a la vista! Ah no, es mi reflejo 😅']) })],

  [n => /\b(minecraft|juego|jugar|jugamos|partida|gta|roblox|fortnite|server|servidor)\b/.test(n) || null,
    c => ({ anim: 'wow', text: pick(['¡Yo me apunto! Aunque con estas manos de bloque no sé si apuntaré bien 🎮', `¿A qué jugamos, ${c.u}?`, '¡Partida! ¡Partida! 🎮']) })],

  [n => /\b(netvy studios|dedsafio|extremo|proyecto|proyectos|replica)\b/.test(n) || null,
    () => ({ anim: 'wow', text: 'Netvy Studios hace réplicas de proyectos muy famosos, como DEDsafio y Extremo. ¡Mira la web para ver los proyectos! 🌐' })],

  // Yes/no questions: "¿eres un bot?", "¿puedes…?", "¿vas a…?"
  [n => (/^(?:oye |ey |hey |y )?(eres|estas|puedes|podrias|vas|tienes|hay|es|sabes|crees|quieres|te|me|nos|seria|se puede)\b/.test(n) && /\?/.test(n) ? true : null),
    () => ({ anim: 'think', text: pick(['Mmm… yo diría que **sí** 👍', 'Pues… **no** creo 🤔', '**¡Claro que sí!**', 'Puede ser… pregúntame mañana 😏', 'Mi cabeza de colores dice que **sí** 🟨🟥🟦']) })],

  // Open questions: what / why / how / when / where / who
  [n => (/\?$|^(que|por que|porque|como|cuando|donde|quien|cual|cuanto)\b/.test(n) ? keyword(n) || true : null),
    (c, word) => ({ anim: 'think', text: typeof word === 'string'
      ? pick([`Buena pregunta sobre **${word}**… no lo sé seguro, ¿alguien del server sabe? 🤔`, `Mmm, de **${word}** sé poco. ¡Investiguemos juntos! 🔎`, `¿${word}? Esa me la tengo que pensar 🤔`])
      : pick(['Mmm… déjame pensarlo 🤔', 'Buena pregunta… no tengo ni idea 😅']) })],
];

/** Builds an answer to `text` from `author` in `channel`. */
export function respond(text, author, channel = 'general', ref = name => `#${name}`) {
  // Drop the bot's own name ("oye netvi, ...") so the rules see only what was said to it.
  const norm = normalize(text).replace(/\b(netvi|netvy)\b[,:!.]*/g, ' ').replace(/\s+/g, ' ').trim();
  const ctx = { u: author, channel, ref };
  for (const [test, make] of RULES) {
    const m = test(norm, text);
    if (m) return make(ctx, m);
  }
  const word = keyword(norm);
  return word
    ? { anim: pick(['talk', 'wow']), text: pick([`¿**${word}**? Cuéntame más 👀`, `Ajá, ${word}… ¡qué interesante!`, `Me has dejado pensando con lo de **${word}** 🤔`]) }
    : { anim: pick(['talk', 'wave']), text: pick([`¿Sí, ${author}? Cuéntame 👀`, `Te escucho, ${author} 👂`, '¿Qué pasa? Dime 😄']) };
}
