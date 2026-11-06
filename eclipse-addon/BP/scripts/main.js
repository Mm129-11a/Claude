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
const DIST = { flash: 14.0, moon: 14.5, sun: 15.0, corona: 15.2, glow: 15.6, sky: 19.0 };
const SUN_DEG = 5.5;
const MOON_DEG = 5.72;
const NOON = 6000;
const MIDNIGHT = 18000;
const SAVE_KEY = "eclipse:saved";
const rad = (d) => (d * Math.PI) / 180;

// Manchas que oscurecen el cielo, repartidas en la mitad de arriba (más de 12° sobre el horizonte)
const SKY_POINTS = (() => {
  const pts = [];
  const n = 48;
  const minZ = Math.sin(rad(12));
  const ga = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = minZ + ((1 - minZ) * (i + 0.5)) / n;
    const r = Math.sqrt(1 - y * y);
    const el = (Math.asin(y) * 180) / Math.PI;
    pts.push({ x: r * Math.cos(ga * i), y, z: r * Math.sin(ga * i), band: el < 25 ? 0 : el < 50 ? 1 : 2 });
  }
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
  state = { tick: 0, fog: new Map() };
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
  const skyStage = Math.round(dark * 12);
  const fog =
    t >= P ? "totality" : dark > 0.8 ? "dark4" : dark > 0.55 ? "dark3" : dark > 0.3 ? "dark2" : dark > 0.08 ? "dark1" : null;

  // Destello: sube rápido al hacerse de noche y se apaga en 2.5 s
  let flash = 0;
  if (t >= P - 6 && t < P + 50) flash = t < P + 6 ? (t - (P - 6)) / 12 : 1 - (t - (P + 6)) / 44;
  const flashLevel = Math.round(clamp01(flash) * 4);
  const coronaLevel = t < P + 15 ? 0 : Math.round(clamp01((t - (P + 15)) / 45) * 4);

  for (const p of world.getAllPlayers()) {
    if (p.dimension.id !== "minecraft:overworld") continue;
    const head = p.getHeadLocation();

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
        spawn(p, `eclipse:sky_${skyStage}_${s.band}`, {
            x: head.x + s.x * DIST.sky,
            y: head.y + s.y * DIST.sky,
            z: head.z + s.z * DIST.sky,
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
