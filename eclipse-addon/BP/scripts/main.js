// Eclipse solar para Minecraft Bedrock.
// Comando: /eclipse  (solo operadores). Una vez lo empieza, otra vez lo termina.
//
// Cómo funciona: a cada jugador se le monta en el hombro una entidad invisible ("eclipse:sky"),
// como un loro. Esa entidad dibuja el sol, la luna y el cielo naranja/oscuro justo arriba de él.
// Como va montada, el juego la mueve con el jugador en cada cuadro: se ve suave aunque corras o vueles.
// Todo el dibujo lo calcula el celular de cada jugador con la línea de tiempo de tools/build.py.
// Este script solo pone la hora (mediodía y luego medianoche), la niebla y monta la entidad.
import { world, system, CommandPermissionLevel, CustomCommandStatus } from "@minecraft/server";
import { PARTIAL_SECONDS, SUN_DEG, MOON_DEG, MAX_VARIANT } from "./timeline.js";

const NOON = 6000; // el sol del juego queda justo arriba, escondido detrás de nuestro sol redondo
const MIDNIGHT = 18000; // salen las estrellas; la luna del juego queda arriba, detrás de la nuestra
const SKY = "eclipse:sky";
const SAVE_KEY = "eclipse:saved";

let state = null;
const warned = new Set();

function warnOnce(key, text) {
  if (warned.has(key)) return;
  warned.add(key);
  world.sendMessage(`§cEclipse: ${text}`);
}

const isValid = (e) => !!e && (typeof e.isValid === "function" ? e.isValid() : e.isValid);
const clamp01 = (v) => Math.max(0, Math.min(1, v));
const smooth = (v) => v * v * (3 - 2 * v);

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
function removeSky(sky) {
  try {
    if (isValid(sky)) sky.remove();
  } catch {}
}

function skyFor(player) {
  let sky = state.sky.get(player.id);
  if (!isValid(sky) || sky.dimension.id !== player.dimension.id) {
    removeSky(sky);
    try {
      sky = player.dimension.spawnEntity(SKY, player.getHeadLocation());
    } catch (e) {
      warnOnce("spawn", `no se pudo crear el cielo: ${e}`);
      return undefined;
    }
    // Si el eclipse ya iba avanzado (alguien que entró tarde), que empiece en ese segundo
    const elapsed = Math.min(MAX_VARIANT, Math.floor(state.tick / 20));
    if (elapsed >= 1) {
      try {
        sky.triggerEvent(`eclipse:at_${elapsed}`);
      } catch (e) {
        warnOnce("event", `no se pudo adelantar el eclipse: ${e}`);
      }
    }
    state.sky.set(player.id, sky);
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
      warnOnce("ride", "no se pudo montar en el hombro; se moverá a saltos");
      try {
        sky.teleport(player.getHeadLocation());
      } catch {}
    }
  }
  return sky;
}

function removeAllSkies() {
  try {
    for (const e of world.getDimension("overworld").getEntities({ type: SKY })) e.remove();
  } catch {}
}

// ---------- empezar / terminar ----------
function start() {
  removeAllSkies();
  if (typeof world.getDynamicProperty(SAVE_KEY) !== "string") {
    world.setDynamicProperty(
      SAVE_KEY,
      JSON.stringify({ time: world.getTimeOfDay(), cycle: world.gameRules.doDayLightCycle })
    );
  }
  world.gameRules.doDayLightCycle = false;
  world.setTimeOfDay(NOON);
  state = { tick: 0, fog: new Map(), sky: new Map() };
  world.sendMessage("§6☀ Empieza el eclipse... mira hacia arriba");
}

function stop() {
  for (const p of world.getAllPlayers()) {
    cmd(p, "fog @s remove eclipse");
    cmd(p, "camera @s fade time 0.2 0.1 1.2 color 255 255 255");
  }
  for (const sky of state.sky.values()) removeSky(sky);
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

function update() {
  if (!state) return;
  const t = state.tick++;
  const P = PARTIAL_SECONDS * 20; // momento en que se hace de noche

  // Lo mismo que calcula el celular, para la niebla del horizonte
  const off = t < P ? 2.45 - 2.33 * smooth(t / P) : 0;
  const dark = t < P ? Math.pow(clamp01((covered(off) - 0.05) / 0.9), 1.2) : 1;
  if (t === P) world.setTimeOfDay(MIDNIGHT);
  const fog =
    t >= P ? "totality" : dark > 0.8 ? "dark4" : dark > 0.55 ? "dark3" : dark > 0.3 ? "dark2" : dark > 0.08 ? "dark1" : null;

  for (const p of world.getAllPlayers()) {
    if (p.dimension.id !== "minecraft:overworld") {
      removeSky(state.sky.get(p.id));
      state.sky.delete(p.id);
      continue;
    }
    skyFor(p);
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

// Si el mundo se cerró a mitad del eclipse, devuelve la hora normal y quita lo que quedó
world.afterEvents.worldLoad.subscribe(() => {
  restoreTime();
  removeAllSkies();
});
system.runInterval(update, 1);
