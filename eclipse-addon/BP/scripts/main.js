// Eclipse solar para Minecraft Bedrock.
// Comando: /eclipse  (solo operadores). Una vez lo empieza, otra vez lo termina.
//
// Cómo funciona: a cada jugador se le monta en el hombro una entidad invisible ("eclipse:sky"),
// como un loro. Esa entidad dibuja el sol, la luna y el cielo oscuro justo arriba de él, y como
// va montada, el juego la mueve con el jugador en cada cuadro: se ve suave aunque corras o vueles.
// Se pone mediodía, así el sol del juego queda exactamente arriba y lo tapa nuestro sol redondo.
// Al final se hace medianoche (salen las estrellas) y la luna del juego queda arriba,
// escondida detrás de nuestra luna negra.
import { world, system, CommandPermissionLevel, CustomCommandStatus } from "@minecraft/server";

// ---------------- Ajustes (puedes cambiarlos) ----------------
const CONFIG = {
  partialSeconds: 22, // cuánto tarda la luna en tapar el sol
  moonFrom: { x: 1, z: -1 }, // de qué lado viene la luna
};
// --------------------------------------------------------------

// Alturas en bloques (iguales que en tools/build.py)
const H = { flash: 23.5, moon: 24.0 };
const SUN_DEG = 5.5;
const MOON_DEG = 5.72;
const STAGES = 12;
const NOON = 6000;
const MIDNIGHT = 18000;
const SKY = "eclipse:sky";
const SAVE_KEY = "eclipse:saved";
const rad = (d) => (d * Math.PI) / 180;
const lenFrom = Math.hypot(CONFIG.moonFrom.x, CONFIG.moonFrom.z);
const FROM = { x: CONFIG.moonFrom.x / lenFrom, z: CONFIG.moonFrom.z / lenFrom };

let state = null;
let warned = false;

function warnOnce(text) {
  if (warned) return;
  warned = true;
  world.sendMessage(`§cEclipse: ${text}`);
}

const isValid = (e) => !!e && (typeof e.isValid === "function" ? e.isValid() : e.isValid);

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

// ---------- la entidad montada en el hombro ----------
function hideFromOthers(sky, owner) {
  for (const other of world.getAllPlayers()) {
    if (other.id === owner.id || typeof other.setPropertyOverrideForEntity !== "function") continue;
    try {
      other.setPropertyOverrideForEntity(sky, "eclipse:hide", true);
    } catch {}
  }
}

function skyFor(player) {
  let sky = state.sky.get(player.id);
  if (!isValid(sky) || sky.dimension.id !== player.dimension.id) {
    try {
      if (isValid(sky)) sky.remove();
    } catch {}
    try {
      sky = player.dimension.spawnEntity(SKY, player.getHeadLocation());
    } catch (e) {
      warnOnce(`no se pudo crear el cielo: ${e}`);
      return undefined;
    }
    state.sky.set(player.id, sky);
    state.props.set(sky.id, {});
    hideFromOthers(sky, player);
  }

  // Que vaya montada en este jugador; si no se puede, la movemos a mano
  const ridingOn = sky.getComponent("minecraft:riding")?.entityRidingOn;
  if (!ridingOn || ridingOn.id !== player.id) {
    try {
      ridingOn?.getComponent("minecraft:rideable")?.ejectRider(sky);
    } catch {}
    let ok = false;
    try {
      ok = !!player.getComponent("minecraft:rideable")?.addRider(sky);
    } catch {}
    if (!ok) {
      try {
        sky.teleport(player.getHeadLocation());
      } catch {}
    }
  }
  return sky;
}

function setProps(sky, values) {
  const cache = state.props.get(sky.id) ?? {};
  for (const [k, v] of Object.entries(values)) {
    if (cache[k] === v) continue;
    try {
      sky.setProperty(`eclipse:${k}`, v);
      cache[k] = v;
    } catch (e) {
      warnOnce(`no se pudo cambiar ${k}: ${e}`);
    }
  }
  state.props.set(sky.id, cache);
}

function removeAllSkies() {
  try {
    for (const e of world.getDimension("overworld").getEntities({ type: SKY })) e.remove();
  } catch {}
}

// ---------- empezar / terminar ----------
function start() {
  if (typeof world.getDynamicProperty(SAVE_KEY) !== "string") {
    world.setDynamicProperty(
      SAVE_KEY,
      JSON.stringify({ time: world.getTimeOfDay(), cycle: world.gameRules.doDayLightCycle })
    );
  }
  world.gameRules.doDayLightCycle = false;
  world.setTimeOfDay(NOON);
  state = { tick: 0, fog: new Map(), sky: new Map(), props: new Map() };
  world.sendMessage("§6☀ Empieza el eclipse... mira hacia arriba");
}

function stop() {
  for (const p of world.getAllPlayers()) {
    cmd(p, "fog @s remove eclipse");
    cmd(p, "camera @s fade time 0.2 0.1 1.2 color 255 255 255");
  }
  for (const sky of state.sky.values()) {
    try {
      if (isValid(sky)) sky.remove();
    } catch {}
  }
  removeAllSkies();
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
const round2 = (v) => Math.round(v * 100) / 100;

function update() {
  if (!state) return;
  const t = state.tick++;
  const P = CONFIG.partialSeconds * 20; // momento en que se hace de noche

  // Distancia de la luna al centro del sol (en radios del sol)
  const off = t < P ? 2.45 - 2.33 * smooth(t / P) : 0.12 * (1 - clamp01((t - P) / 40));
  const cov = covered(off);
  const dark = t < P ? Math.pow(clamp01((cov - 0.05) / 0.9), 1.2) : 1; // 0 azul, 0.5 naranja, 1 negro
  if (t === P) world.setTimeOfDay(MIDNIGHT);

  // Luna y destello: cuánto se apartan del centro (en píxeles del modelo)
  const moonPx = Math.tan(rad(off * SUN_DEG)) * H.moon * 16;
  const flashPx = -Math.tan(rad(SUN_DEG * 0.92)) * H.flash * 16;
  let flash = 0;
  if (t >= P - 6 && t < P + 50) flash = t < P + 6 ? (t - (P - 6)) / 12 : 1 - (t - (P + 6)) / 44;
  const corona = t < P + 15 ? 0 : (0.85 + 0.15 * smooth(clamp01((t - (P + 15)) / 45))) * (1 + 0.02 * Math.sin(t / 9));

  const values = {
    mx: round2(moonPx * FROM.x),
    mz: round2(moonPx * FROM.z),
    fx: round2(flashPx * FROM.x),
    fz: round2(flashPx * FROM.z),
    stage: t < P ? Math.round(dark * STAGES) : 0,
    moon: Math.round(dark * 7),
    sun: t < P + 40,
    glow: t < P + 10 ? round2(0.35 + 0.65 * Math.pow(1 - cov, 0.3)) : 0,
    corona: round2(corona),
    flash: round2(clamp01(flash) * 1.0),
  };
  const fog =
    t >= P ? "totality" : dark > 0.8 ? "dark4" : dark > 0.55 ? "dark3" : dark > 0.3 ? "dark2" : dark > 0.08 ? "dark1" : null;

  for (const p of world.getAllPlayers()) {
    if (p.dimension.id !== "minecraft:overworld") {
      const sky = state.sky.get(p.id);
      try {
        if (isValid(sky)) sky.remove();
      } catch {}
      state.sky.delete(p.id);
      continue;
    }
    const sky = skyFor(p);
    if (sky) setProps(sky, values);
    setFog(p, fog);
    if (t === P) cmd(p, "camera @s fade time 0.15 0.1 0.8 color 4 5 10");
  }

  // Cada 2 segundos: que los que entraron nuevos no vean el cielo de los demás
  if (t % 40 === 0) {
    for (const p of world.getAllPlayers()) {
      const sky = state.sky.get(p.id);
      if (isValid(sky)) hideFromOthers(sky, p);
    }
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

// Si el mundo se cerró a mitad del eclipse, devuelve la hora normal y quita lo que quedó
world.afterEvents.worldLoad.subscribe(() => {
  restoreTime();
  removeAllSkies();
});
system.runInterval(update, 1);
