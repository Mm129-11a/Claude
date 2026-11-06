// Eclipse solar para Minecraft Bedrock.
// Comando: /eclipse  (solo operadores). Una vez lo empieza, otra vez lo termina.
import {
  world,
  system,
  CommandPermissionLevel,
  CustomCommandStatus,
  MolangVariableMap,
} from "@minecraft/server";

// ---------------- Ajustes (puedes cambiarlos) ----------------
const CONFIG = {
  sunTime: 9600, // hora del día del eclipse: el sol queda al oeste, a unos 40° de altura
  totalityTime: 13000, // hora a la que pasa en la totalidad (cielo oscuro, horizonte naranja)
  partialSeconds: 20, // cuánto tarda la luna en tapar el sol
  flashSeconds: 2, // cuánto dura el destello antes de la totalidad
  distance: 40, // a cuántos bloques se dibuja el eclipse
  sunRadiusDeg: 4.6, // tamaño de la luna (en grados). Súbelo si se asoma el sol en los bordes
  moonSizeScale: 1.0, // multiplica el tamaño de luna y corona si en tu versión se ven chicos/grandes
  coronaSize: 2.6, // tamaño de la corona comparado con la luna
};
// --------------------------------------------------------------

const SAVE_KEY = "eclipse:saved";
let state = null; // { tick, sunDir, moonR, from, players: Map<id, fogLevel> }

function celestialAngle(time) {
  // Misma fórmula que usa Minecraft para colocar el sol
  let f = (time % 24000) / 24000 - 0.25;
  if (f < 0) f += 1;
  const eased = 1 - (Math.cos(f * Math.PI) + 1) / 2;
  return f + (eased - f) / 3;
}

const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
const mul = (a, k) => ({ x: a.x * k, y: a.y * k, z: a.z * k });

function particle(player, id, pos, size, alpha) {
  const vars = new MolangVariableMap();
  vars.setFloat("variable.size", size);
  vars.setFloat("variable.alpha", alpha);
  try {
    player.spawnParticle(id, pos, vars);
  } catch {}
}

function cmd(player, text) {
  try {
    player.runCommand(text);
  } catch {}
}

function setFog(player, level) {
  if (state.players.get(player.id) === level) return;
  state.players.set(player.id, level);
  cmd(player, "fog @s remove eclipse");
  if (level) cmd(player, `fog @s push eclipse:${level} eclipse`);
}

function start() {
  world.setDynamicProperty(
    SAVE_KEY,
    JSON.stringify({ time: world.getTimeOfDay(), cycle: world.gameRules.doDayLightCycle })
  );
  world.gameRules.doDayLightCycle = false;
  world.setTimeOfDay(CONFIG.sunTime);

  const a = 2 * Math.PI * celestialAngle(CONFIG.sunTime);
  const sunDir = { x: -Math.sin(a), y: Math.cos(a), z: 0 };
  const across = { x: Math.cos(a), y: Math.sin(a), z: 0 }; // a lo ancho del cielo
  const side = { x: 0, y: 0, z: 1 };
  const moonR = CONFIG.distance * Math.tan((CONFIG.sunRadiusDeg * Math.PI) / 180);
  // La luna entra desde arriba a la derecha, como en el video
  let from = add(mul(across, 0.55), mul(side, -0.85)); // arriba + norte (a tu derecha mirando al oeste)
  from = mul(from, 1 / Math.hypot(from.x, from.y, from.z));

  state = { tick: 0, sunDir, moonR, from, players: new Map() };
  world.sendMessage("§6☀ Empieza el eclipse...");
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

function update() {
  if (!state) return;
  const t = state.tick++;
  const partial = CONFIG.partialSeconds * 20;
  const flash = CONFIG.flashSeconds * 20;
  const r = state.moonR * CONFIG.moonSizeScale;

  // Qué tan lejos está la luna del centro del sol (1 = recién empieza, 0 = centrada)
  const k = Math.min(1, t / partial);
  const left = Math.pow(1 - k, 1.6);
  const offset = mul(state.from, left * r * 2.3);
  const covered = Math.max(0, 1 - left * 1.15); // 0..1 cuánto sol está tapado

  if (t === partial) {
    world.setTimeOfDay(CONFIG.totalityTime);
  }

  for (const p of world.getAllPlayers()) {
    if (p.dimension.id !== "minecraft:overworld") continue;
    const sun = add(p.getHeadLocation(), mul(state.sunDir, CONFIG.distance));

    if (t < partial) {
      particle(p, "eclipse:moon", add(sun, offset), r, 1);
      setFog(p, covered > 0.85 ? "dark4" : covered > 0.7 ? "dark3" : covered > 0.5 ? "dark2" : covered > 0.3 ? "dark1" : null);
    } else {
      // Totalidad: luna negra con su anillo de luz
      const pulse = 1 + 0.025 * Math.sin(t / 9);
      particle(p, "eclipse:corona", sun, r * CONFIG.coronaSize * pulse, 1);
      particle(p, "eclipse:moon", sun, r * 1.0, 1);
      setFog(p, "totality");
    }

    // Destello justo antes y al empezar la totalidad (el "anillo de diamante")
    if (t > partial - flash && t < partial + flash / 2) {
      const f = 1 - Math.abs(t - partial) / flash;
      const edge = add(sun, mul(state.from, -r * 0.95));
      particle(p, "eclipse:flash", edge, r * (2.5 + 4 * f), Math.min(1, f * 1.4));
    }

    if (t === partial) {
      cmd(p, "camera @s fade time 0.25 0.1 1.6 color 8 10 24");
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

// Si el mundo se cerró a mitad del eclipse, devuelve la hora normal al abrirlo
world.afterEvents.worldLoad.subscribe(() => restoreTime());
system.runInterval(update, 1);
