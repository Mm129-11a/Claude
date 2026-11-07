import { world, system, MolangVariableMap } from "@minecraft/server";
import { PIEZAS, ATLAS, STAR_TEXTURE, STAR_HALF } from "./piezas.js";

// Se lanza con /function supernova (que ejecuta: scriptevent supernova:iniciar)
const EVENT_ID = "supernova:iniciar";

const DISTANCE = 32;   // bloques delante de quien ejecuta el comando
const HEIGHT = 9;      // bloques por encima de los pies (como en la foto: unos 14° por encima de la vista)
const EYE = 1.62;      // altura de los ojos

// Momentos de la secuencia, en ticks (20 ticks = 1 segundo)
const T = {
  oscurecer: 10,     // se hace de noche y aparece el núcleo
  piezasInicio: 14,  // empiezan a llegar las piezas, una tras otra
  piezasFin: 74,     // sale la última pieza
  estrella: 96,      // la última pieza encaja: la estrella está completa
  temblor: 136,      // la estrella se hincha
  explosion: 160,    // explota
  destello: 180,     // llega el destello
  restaurar: 195,    // vuelve la hora de antes (el destello tapa el cielo)
  fin: 270,          // se quita la niebla del destello
};
const FLIGHT = (T.estrella - T.piezasFin) / 20;   // segundos que vuela cada pieza

let running = false;

function cmd(dimension, command) {
  try {
    dimension.runCommand(command);
  } catch (e) {
    console.warn(`[supernova] ${command}: ${e}`);
  }
}

function soundAll(id, volume = 1, pitch = 1) {
  for (const player of world.getAllPlayers()) {
    try {
      player.playSound(id, { volume, pitch });
    } catch {
      // jugador saliendo del mundo
    }
  }
}

function at(ticks, fn) {
  system.runTimeout(() => {
    try {
      fn();
    } catch (e) {
      console.warn(`[supernova] ${e}`);
    }
  }, ticks);
}

function spawn(dimension, id, pos, vars) {
  try {
    dimension.spawnParticle(id, pos, vars);
  } catch (e) {
    console.warn(`[supernova] partícula ${id}: ${e}`);
  }
}

function molang(values) {
  const m = new MolangVariableMap();
  for (const [k, v] of Object.entries(values)) m.setFloat(`variable.${k}`, v);
  return m;
}

const add = (a, b, k = 1) => ({ x: a.x + b.x * k, y: a.y + b.y * k, z: a.z + b.z * k });
const cross = (a, b) => ({ x: a.y * b.z - a.z * b.y, y: a.z * b.x - a.x * b.z, z: a.x * b.y - a.y * b.x });
function norm(v) {
  const l = Math.hypot(v.x, v.y, v.z) || 1;
  return { x: v.x / l, y: v.y / l, z: v.z / l };
}

// La estrella se forma pieza por pieza: cada pieza sale de lejos, vuela girando y encaja en su sitio
function formStar(dimension, center, eye) {
  const d = norm({ x: center.x - eye.x, y: center.y - eye.y, z: center.z - eye.z });   // hacia la estrella
  let right = cross(d, { x: 0, y: 1, z: 0 });
  if (Math.hypot(right.x, right.y, right.z) < 0.05) right = { x: 1, y: 0, z: 0 };
  right = norm(right);
  const up = norm(cross(right, d));
  const px = (2 * STAR_HALF) / STAR_TEXTURE;          // bloques por píxel de la textura de la estrella

  const total = PIEZAS.length;
  PIEZAS.forEach((p, i) => {
    const tick = T.piezasInicio + Math.round((i / Math.max(1, total - 1)) * (T.piezasFin - T.piezasInicio));
    at(tick - T.oscurecer, () => {   // formStar se llama en T.oscurecer
      // sitio final de la pieza, en el plano que mira al jugador
      const target = add(add(center, right, p.x * px), up, -p.y * px);
      // de dónde viene: hacia afuera de la bola, lejos, un poco al azar y a distinta profundidad
      let ax = p.x;
      let ay = -p.y;
      if (Math.hypot(ax, ay) < 1) {
        const a = Math.random() * Math.PI * 2;
        ax = Math.cos(a);
        ay = Math.sin(a);
      }
      const ang = Math.atan2(ay, ax) + (Math.random() - 0.5) * 0.9;
      const dist = 14 + Math.random() * 10;
      const off = add(add(add({ x: 0, y: 0, z: 0 }, right, Math.cos(ang) * dist), up, Math.sin(ang) * dist),
        d, -6 + Math.random() * 14);
      const life = (T.estrella - tick) / 20 + 0.3;
      spawn(dimension, "supernova:pieza", target, molang({
        ox: off.x, oy: off.y, oz: off.z,
        rot: (Math.random() < 0.5 ? -1 : 1) * (120 + Math.random() * 200),
        flight: FLIGHT, life,
        sw: (p.w / 2) * px, sh: (p.h / 2) * px,
        pu: p.u, pv: p.v, pw: p.w, ph: p.h,
      }));
      // al encajar, un golpe de piedra
      if (i % 2 === 0) {
        at(Math.round(FLIGHT * 20), () => soundAll("dig.stone", 0.6, 0.6 + Math.random() * 0.4));
      }
    });
  });
  // el núcleo brilla detrás mientras se forma
  spawn(dimension, "supernova:nucleo", add(center, d, 0.6), molang({ life: (T.estrella - T.oscurecer) / 20 + 0.3 }));
  return d;
}

function startSupernova(dimension, origin, viewDir) {
  if (running) return;
  running = true;

  // Dirección horizontal hacia donde mira el jugador
  let dx = viewDir.x;
  let dz = viewDir.z;
  const len = Math.hypot(dx, dz);
  if (len < 0.1) {
    dx = 0;
    dz = 1;
  } else {
    dx /= len;
    dz /= len;
  }
  const maxY = dimension.heightRange.max - 8;
  const center = {
    x: origin.x + dx * DISTANCE,
    y: Math.min(origin.y + HEIGHT, maxY),
    z: origin.z + dz * DISTANCE,
  };
  const eye = { x: origin.x, y: origin.y + EYE, z: origin.z };
  // la explosión un poco más cerca y el destello un poco más lejos, para que no se mezclen
  const near = { x: center.x - dx, y: center.y, z: center.z - dz };
  const far = { x: center.x + dx * 3, y: center.y, z: center.z + dz * 3 };

  const previousTime = world.getTimeOfDay();

  // 1. Todo se pone oscuro y la estrella se forma pieza por pieza
  cmd(dimension, "camera @a fade time 0.5 0.3 1.2 color 0 0 0");
  soundAll("ambient.weather.thunder", 0.4, 0.5);
  at(T.oscurecer, () => {
    world.setTimeOfDay(18000);
    cmd(dimension, "fog @a push supernova:oscuro supernova_oscuro");
    formStar(dimension, center, eye);
    soundAll("beacon.ambient", 1, 0.5);
  });
  at(T.estrella, () => {
    spawn(dimension, "supernova:estrella", center);
    soundAll("beacon.activate", 1, 0.6);
  });
  for (const t of [60, 110, 140]) at(t, () => soundAll("ambient.weather.thunder", 0.6, 0.6));
  at(T.temblor, () => cmd(dimension, "camerashake add @a 0.15 1 positional"));

  // 2. Explota
  at(T.explosion, () => {
    spawn(dimension, "supernova:explosion", near);
    soundAll("random.explode", 4, 0.6);
    soundAll("mob.wither.spawn", 1, 0.8);
    cmd(dimension, "camerashake add @a 0.8 2.5 positional");
    cmd(dimension, "fog @a pop supernova_oscuro");
    cmd(dimension, "fog @a push supernova:explosion supernova_explosion");
  });

  // 3. El destello
  at(T.destello, () => {
    spawn(dimension, "supernova:destello", far);
    cmd(dimension, "camera @a fade time 0.1 0.05 0.6 color 255 236 248");   // parpadeo corto
    cmd(dimension, "fog @a pop supernova_explosion");
    cmd(dimension, "fog @a push supernova:destello supernova_destello");
    soundAll("ambient.weather.lightning.impact", 1, 0.5);
  });
  at(T.restaurar, () => world.setTimeOfDay((previousTime + T.restaurar) % 24000));
  at(T.fin, () => {
    cmd(dimension, "fog @a pop supernova_destello");
    running = false;
  });
}

system.afterEvents.scriptEventReceive.subscribe((event) => {
  if (event.id !== EVENT_ID) return;
  const source = event.sourceEntity;
  if (source) {
    startSupernova(source.dimension, source.location, source.getViewDirection());
  } else if (event.sourceBlock) {
    // desde un bloque de comandos: hacia el norte
    const b = event.sourceBlock;
    startSupernova(b.dimension, b.location, { x: 0, y: 0, z: -1 });
  } else {
    const player = world.getAllPlayers()[0];
    if (player) startSupernova(player.dimension, player.location, player.getViewDirection());
  }
});
