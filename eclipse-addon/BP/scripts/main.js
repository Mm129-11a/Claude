// Eclipse solar para Minecraft Bedrock.
// Comando: /eclipse  (solo operadores). Una vez lo empieza, otra vez lo termina.
//
// Cómo funciona: el eclipse se dibuja justo arriba de cada jugador (todo el server lo ve).
// Se pone mediodía, así el sol del juego queda exactamente arriba y lo tapa nuestro sol redondo.
// Al final se hace medianoche (salen las estrellas) y la luna del juego queda
// exactamente arriba, escondida detrás de nuestra luna negra.
import { world, system, CommandPermissionLevel, CustomCommandStatus } from "@minecraft/server";

// ---------------- Ajustes (puedes cambiarlos) ----------------
const CONFIG = {
  partialSeconds: 22, // cuánto tarda la luna en tapar el sol
  moonFrom: { x: 1, z: -1 }, // de dónde viene la luna (x = este, z = sur; -z = norte)
};
// --------------------------------------------------------------

// Distancias en bloques. Si las cambias, cambia también tools/build.py (tamaños de las partículas).
const DIST = { flash: 22.4, moon: 23.2, sun: 24.0, corona: 24.3, glow: 25.0, sky: 30.4, skylow: 60.0 };
const SKY_STEPS = 24;
const SUN_DEG = 5.5;
const MOON_DEG = 5.72;
const NOON = 6000;
const MIDNIGHT = 18000;
const SAVE_KEY = "eclipse:saved";
const rad = (d) => (d * Math.PI) / 180;

// Manchas que pintan el cielo: 40 arriba (más de 15°) y dos anillos de 16 junto al horizonte.
// Las del horizonte van más lejos (60 bloques) para no pintar el suelo cercano.
const SKY_POINTS = (() => {
  const pts = [];
  const minY = Math.sin(rad(15));
  const ga = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < 40; i++) {
    const y = minY + ((1 - minY) * (i + 0.5)) / 40;
    const r = Math.sqrt(1 - y * y);
    pts.push({ x: r * Math.cos(ga * i), y, z: r * Math.sin(ga * i), kind: "sky", dist: DIST.sky });
  }
  [-2, 8].forEach((el, row) => {
    for (let i = 0; i < 16; i++) {
      const az = (2 * Math.PI * (i + 0.5 * row)) / 16;
      const e = rad(el);
      pts.push({ x: Math.cos(e) * Math.cos(az), y: Math.sin(e), z: Math.cos(e) * Math.sin(az), kind: "skylow", dist: DIST.skylow });
    }
  });
  return pts;
})();

let state = null;
let warned = false;

const lenFrom = Math.hypot(CONFIG.moonFrom.x, CONFIG.moonFrom.z);
const FROM = { x: CONFIG.moonFrom.x / lenFrom, z: CONFIG.moonFrom.z / lenFrom };

// Punto en el cielo: "angle" grados desde el cenit hacia "FROM" (negativo = lado contrario)
function skyPoint(head, dist, angleDeg) {
  const a = rad(angleDeg);
  return {
    x: head.x + dist * Math.sin(a) * FROM.x,
    y: head.y + dist * Math.cos(a),
    z: head.z + dist * Math.sin(a) * FROM.z,
  };
}

// Qué parte del sol tapa la luna (0..1). d = distancia entre centros en radios del sol.
function covered(d) {
  const r1 = 1;
  const r2 = MOON_DEG / SUN_DEG;
  if (d >= r1 + r2) return 0;
  if (d <= r2 - r1) return 1;
  const a1 = r1 * r1 * Math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1));
  const a2 = r2 * r2 * Math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2));
  const k = 0.5 * Math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2));
  return (a1 + a2 - k) / Math.PI;
}

function spawn(player, id, pos) {
  try {
    player.spawnParticle(id, pos);
  } catch (e) {
    if (!warned) {
      warned = true;
      world.sendMessage(`§cEclipse: no se pudo dibujar ${id}: ${e}`);
    }
  }
}

function cmd(player, text) {
  try {
    player.runCommand(text);
  } catch {}
}

function setFog(player, fog) {
  if (state.fog.get(player.id) === fog) return;
  state.fog.set(player.id, fog);
  cmd(player, "fog @s remove eclipse");
  if (fog) cmd(player, `fog @s push eclipse:${fog} eclipse`);
}

function start() {
  if (typeof world.getDynamicProperty(SAVE_KEY) !== "string") {
    world.setDynamicProperty(
      SAVE_KEY,
      JSON.stringify({ time: world.getTimeOfDay(), cycle: world.gameRules.doDayLightCycle })
    );
  }
  world.gameRules.doDayLightCycle = false;
  world.setTimeOfDay(NOON);
  state = { tick: 0, fog: new Map(), motion: new Map() };
  world.sendMessage("§6☀ Empieza el eclipse... mira hacia arriba");
}

function stop() {
  for (const p of world.getAllPlayers()) {
    cmd(p, "fog @s remove eclipse");
    cmd(p, "camera @s fade time 0.2 0.1 1.2 color 255 255 255");
  }
  restoreTime();
  state = null;
  world.sendMessage("§e☀ Terminó el eclipse.");
}

function restoreTime() {
  const raw = world.getDynamicProperty(SAVE_KEY);
  if (typeof raw !== "string") return;
  try {
    const saved = JSON.parse(raw);
    world.setTimeOfDay(saved.time);
    world.gameRules.doDayLightCycle = saved.cycle;
  } catch {}
  world.setDynamicProperty(SAVE_KEY, undefined);
}

// El eclipse se redibuja 20 veces por segundo. Lo ponemos medio paso adelante de hacia donde
// te mueves, así queda centrado entre una actualización y otra en vez de quedarse atrás.
function leadHead(player, head) {
  const prev = state.motion.get(player.id);
  let step = { x: 0, y: 0, z: 0 };
  if (prev) {
    const d = { x: head.x - prev.head.x, y: head.y - prev.head.y, z: head.z - prev.head.z };
    if (Math.hypot(d.x, d.y, d.z) < 4) {
      const k = 0.5; // suavizado para que no brinque si un tick llega tarde
      step = { x: prev.step.x * (1 - k) + d.x * k, y: prev.step.y * (1 - k) + d.y * k, z: prev.step.z * (1 - k) + d.z * k };
    }
  }
  state.motion.set(player.id, { head, step });
  return { x: head.x + step.x * 0.5, y: head.y + step.y * 0.5, z: head.z + step.z * 0.5 };
}

const clamp01 = (v) => Math.max(0, Math.min(1, v));
const smooth = (v) => v * v * (3 - 2 * v);

function update() {
  if (!state) return;
  const t = state.tick++;
  const P = CONFIG.partialSeconds * 20; // momento en que se hace de noche

  // Distancia de la luna al centro del sol (en radios del sol)
  let off;
  if (t < P) off = 2.45 - 2.33 * smooth(t / P); // llega hasta dejar una rayita de sol
  else off = 0.12 * (1 - clamp01((t - P) / 40)); // y termina de taparlo
  const cov = covered(off);
  const dark = t < P ? Math.pow(clamp01((cov - 0.05) / 0.9), 1.2) : 1; // 0 azul, 0.5 naranja, 1 negro

  if (t === P) world.setTimeOfDay(MIDNIGHT);

  const moonLevel = Math.round(dark * 7);
  const glowIn = Math.round(Math.pow(1 - cov, 0.3) * 6); // el sol brilla fuerte hasta casi taparse
  const glowOut = Math.round(Math.pow(1 - cov, 0.6) * 6);
  const skyStage = Math.round(dark * SKY_STEPS);
  const fog =
    t >= P ? "totality" : dark > 0.8 ? "dark4" : dark > 0.55 ? "dark3" : dark > 0.3 ? "dark2" : dark > 0.08 ? "dark1" : null;

  // Destello: sube rápido al hacerse de noche y se apaga en 2.5 s
  let flash = 0;
  if (t >= P - 6 && t < P + 50) flash = t < P + 6 ? (t - (P - 6)) / 12 : 1 - (t - (P + 6)) / 44;
  const flashLevel = Math.round(clamp01(flash) * 4);
  const coronaLevel = t < P + 15 ? 0 : Math.round(clamp01((t - (P + 15)) / 45) * 4);

  for (const p of world.getAllPlayers()) {
    if (p.dimension.id !== "minecraft:overworld") continue;
    const head = leadHead(p, p.getHeadLocation());

    spawn(p, `eclipse:moon_${moonLevel}`, skyPoint(head, DIST.moon, off * SUN_DEG));
    if (t < P + 40) spawn(p, "eclipse:sun", skyPoint(head, DIST.sun, 0));
    if (t < P + 10) {
      if (glowIn > 0) spawn(p, `eclipse:glowin_${glowIn}`, skyPoint(head, DIST.glow, 0));
      if (glowOut > 0) spawn(p, `eclipse:glowout_${glowOut}`, skyPoint(head, DIST.glow, 0));
    }
    if (coronaLevel > 0) spawn(p, `eclipse:corona_${coronaLevel}`, skyPoint(head, DIST.corona, 0));
    if (flashLevel > 0) spawn(p, `eclipse:flash_${flashLevel}`, skyPoint(head, DIST.flash, -SUN_DEG * 0.92));

    // Cielo: se pone naranja y luego negro (solo de día; de noche ya está oscuro)
    if (t < P && skyStage > 0) {
      for (const s of SKY_POINTS) {
        spawn(p, `eclipse:${s.kind}_${skyStage}`, {
            x: head.x + s.x * s.dist,
            y: head.y + s.y * s.dist,
            z: head.z + s.z * s.dist,
          });
      }
    }

    setFog(p, fog);
    if (t === P) cmd(p, "camera @s fade time 0.15 0.1 0.8 color 4 5 10");
  }
}

system.beforeEvents.startup.subscribe((init) => {
  init.customCommandRegistry.registerCommand(
    {
      name: "eclipse:eclipse",
      description: "Empieza o termina el eclipse solar",
      permissionLevel: CommandPermissionLevel.GameDirectors, // solo operadores
      cheatsRequired: false,
    },
    () => {
      system.run(() => (state ? stop() : start()));
      return { status: CustomCommandStatus.Success };
    }
  );
});

// Si el mundo se cerró a mitad del eclipse, devuelve la hora normal al abrirlo
world.afterEvents.worldLoad.subscribe(() => restoreTime());
system.runInterval(update, 1);
