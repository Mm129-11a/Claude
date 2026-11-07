import { world, system, MolangVariableMap, EntityDamageCause } from "@minecraft/server";
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

// Onda expansiva: sale de la estrella al explotar y quita vida según la distancia a la estrella.
// Puntos (distancia en bloques, corazones que quita); entre puntos se reparte en línea recta.
//   cerca: la mitad de la vida · 100 bloques: 3 corazones · 200: 1 corazón · 300 o más: nada
const DANIO = [
  [40, "mitad"],      // hasta 40 bloques: la mitad de la vida máxima
  [100, 3],
  [200, 1],
  [300, 0],
];
const ONDA = {
  velocidad: 4,       // bloques por tick (80 por segundo): llega a 300 bloques en menos de 4 s
  radio: 300,
  empuje: true,
};
const RADIO_EFECTOS = 300;   // oscuridad, temblor y sonidos: jugadores a menos de esto
const RADIO_DESTELLO = 201;  // el destello blanco: jugadores hasta 200 bloques (incluidos)

let running = false;

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
        at(Math.round(FLIGHT * 20), () =>
          soundTo(playersNear(dimension, center, RADIO_EFECTOS), "dig.stone", 0.6, 0.6 + Math.random() * 0.4));
      }
    });
  });
  // el núcleo brilla detrás mientras se forma
  spawn(dimension, "supernova:nucleo", add(center, d, 0.6), molang({ life: (T.estrella - T.oscurecer) / 20 + 0.3 }));
  return { d, right, up, px };
}

// Al explotar, las piezas de la estrella salen disparadas hacia afuera, al rojo vivo
function blastPieces(dimension, center, frame) {
  const { d, right, up, px } = frame;
  const swell = 1.3;                                   // la estrella está hinchada al explotar
  for (const p of PIEZAS) {
    const start = add(add(center, right, p.x * px * swell), up, -p.y * px * swell);
    let ax = p.x;
    let ay = -p.y;
    if (Math.hypot(ax, ay) < 1) {
      const a = Math.random() * Math.PI * 2;
      ax = Math.cos(a);
      ay = Math.sin(a);
    }
    const ang = Math.atan2(ay, ax) + (Math.random() - 0.5) * 0.5;
    const dist = 22 + Math.random() * 22;
    const off = add(add(add({ x: 0, y: 0, z: 0 }, right, Math.cos(ang) * dist), up, Math.sin(ang) * dist),
      d, -12 + Math.random() * 20);
    spawn(dimension, "supernova:pieza_estalla", start, molang({
      ox: off.x, oy: off.y, oz: off.z,
      rot: (Math.random() < 0.5 ? -1 : 1) * (80 + Math.random() * 220),
      flight: 1.4,
      sw: (p.w / 2) * px * swell, sh: (p.h / 2) * px * swell,
      pu: p.u, pv: p.v, pw: p.w, ph: p.h,
    }));
  }
}

// Corazones que quita la onda a esta distancia (maxHearts = corazones de vida máxima)
function heartsAt(dist, maxHearts) {
  const pts = DANIO.map(([d, h]) => [d, h === "mitad" ? maxHearts / 2 : h]);
  if (dist <= pts[0][0]) return pts[0][1];
  for (let i = 1; i < pts.length; i++) {
    const [d0, h0] = pts[i - 1];
    const [d1, h1] = pts[i];
    if (dist <= d1) return h0 + (h1 - h0) * ((dist - d0) / (d1 - d0));
  }
  return 0;
}

// Quita exactamente esa vida (aunque lleve armadura o le acaben de pegar)
function hurt(entity, hp) {
  const health = entity.getComponent("minecraft:health");
  if (!health || hp <= 0) return;
  const before = health.currentValue;
  const target = Math.max(0, before - hp);
  try {
    entity.applyDamage(hp, { cause: EntityDamageCause.entityExplosion });   // animación y sonido de daño
  } catch {
    // modo creativo o entidad que no recibe daño
  }
  try {
    if (!entity.isValid()) return;
    if (health.currentValue > target + 0.01) {
      if (target <= 0) entity.kill();
      else health.setCurrentValue(target);
    }
  } catch {
    // la entidad ya no existe
  }
}

// La onda expansiva: cada tick crece y quita vida (una sola vez) a lo que alcanza
function shockwave(dimension, center) {
  const hit = new Set();
  let radius = 0;
  const id = system.runInterval(() => {
    const prev = radius;
    radius = Math.min(ONDA.radio, radius + ONDA.velocidad);
    let entities = [];
    try {
      entities = dimension.getEntities({ location: center, maxDistance: radius, minDistance: prev });
    } catch (e) {
      console.warn(`[supernova] onda: ${e}`);
    }
    for (const e of entities) {
      try {
        if (hit.has(e.id)) continue;
        const health = e.getComponent("minecraft:health");
        if (!health) continue;
        if (e.typeId === "minecraft:player") {
          const mode = e.getGameMode ? String(e.getGameMode()).toLowerCase() : "";
          if (mode === "creative" || mode === "spectator") continue;
        }
        hit.add(e.id);
        const loc = e.location;
        const dist = Math.hypot(loc.x - center.x, loc.y - center.y, loc.z - center.z);
        const hp = Math.round(heartsAt(dist, health.effectiveMax / 2) * 2);   // en medios corazones
        hurt(e, hp);
        if (ONDA.empuje && dist < 120) {
          let hx = loc.x - center.x;
          let hz = loc.z - center.z;
          const hl = Math.hypot(hx, hz) || 1;
          const k = 1 - dist / 120;
          try {
            e.applyKnockback(hx / hl, hz / hl, 0.4 + 1.6 * k, 0.25);              // @minecraft/server 1.x
          } catch {
            try {
              e.applyKnockback({ x: (hx / hl) * (0.4 + 1.6 * k), z: (hz / hl) * (0.4 + 1.6 * k) }, 0.25);   // 2.x
            } catch {
              // hay entidades que no se pueden empujar
            }
          }
        }
      } catch {
        // la entidad ya no existe
      }
    }
    if (radius >= ONDA.radio) system.clearRun(id);
  }, 1);
}

// Jugadores a menos de 'radius' bloques de la estrella
function playersNear(dimension, center, radius) {
  try {
    return dimension.getPlayers({ location: center, maxDistance: radius });
  } catch {
    return [];
  }
}

// Ejecuta un comando como cada uno de esos jugadores (@s = el jugador)
function forPlayers(players, command) {
  for (const p of players) {
    try {
      p.runCommand(command);
    } catch {
      // jugador que se fue, o una niebla que ya no tiene
    }
  }
}

function soundTo(players, id, volume = 1, pitch = 1) {
  for (const p of players) {
    try {
      p.playSound(id, { volume, pitch });
    } catch {
      // jugador saliendo del mundo
    }
  }
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
  const front = { x: center.x - dx * 1.8, y: center.y, z: center.z - dz * 1.8 };   // relámpagos delante
  const far = { x: center.x + dx * 3, y: center.y, z: center.z + dz * 3 };

  const previousTime = world.getTimeOfDay();
  let frame = null;
  const near300 = () => playersNear(dimension, center, RADIO_EFECTOS);
  const near200 = () => playersNear(dimension, center, RADIO_DESTELLO);
  let darkened = near300();          // a quienes se les pone la niebla (para quitársela al final)

  // 1. Todo se pone oscuro y la estrella se forma pieza por pieza
  forPlayers(darkened, "camera @s fade time 0.5 0.3 1.2 color 0 0 0");
  soundTo(darkened, "ambient.weather.thunder", 0.4, 0.5);
  at(T.oscurecer, () => {
    world.setTimeOfDay(18000);
    darkened = near300();
    forPlayers(darkened, "fog @s push supernova:oscuro supernova_oscuro");
    frame = formStar(dimension, center, eye);
    soundTo(darkened, "beacon.ambient", 1, 0.5);
  });
  at(T.estrella, () => {
    // la estrella completa: la bola de lava en 3D girando, su resplandor y las brasas
    spawn(dimension, "supernova:estrella", center);
    if (frame) spawn(dimension, "supernova:halo", add(center, frame.d, 0.4));
    spawn(dimension, "supernova:brasas", center);
    soundTo(near300(), "beacon.activate", 1, 0.6);
  });
  for (const t of [60, 110, 140]) at(t, () => soundTo(near300(), "ambient.weather.thunder", 0.6, 0.6));
  at(T.temblor, () => forPlayers(near300(), "camerashake add @s 0.15 1 positional"));
  at(T.explosion + 6, () => spawn(dimension, "supernova:exp_anillo", near));   // segunda onda

  // 2. Explota
  at(T.explosion, () => {
    // por capas: cuerpo, núcleo blanco, rayos, relámpagos, anillo, chispas y las piezas
    spawn(dimension, "supernova:exp_cuerpo", near);
    spawn(dimension, "supernova:exp_nucleo", near);
    spawn(dimension, "supernova:exp_rayos", near);
    spawn(dimension, "supernova:exp_morados", front);
    spawn(dimension, "supernova:exp_anillo", near);
    spawn(dimension, "supernova:chispas", center);
    if (frame) blastPieces(dimension, center, frame);
    shockwave(dimension, center);
    const all = near300();
    soundTo(all, "random.explode", 4, 0.6);
    soundTo(all, "mob.wither.spawn", 1, 0.8);
    // el temblor es más fuerte cuanto más cerca
    for (const p of all) {
      const l = p.location;
      const k = Math.max(0.15, 1 - Math.hypot(l.x - center.x, l.y - center.y, l.z - center.z) / RADIO_EFECTOS);
      forPlayers([p], `camerashake add @s ${(0.9 * k).toFixed(2)} ${(1 + 1.5 * k).toFixed(1)} positional`);
    }
    forPlayers(darkened, "fog @s pop supernova_oscuro");
    darkened = all;
    forPlayers(darkened, "fog @s push supernova:explosion supernova_explosion");
  });

  // 3. El destello blanco: solo a los jugadores a menos de 200 bloques
  let flashed = [];
  at(T.destello, () => {
    spawn(dimension, "supernova:destello", far);
    flashed = near200();
    forPlayers(flashed, "camera @s fade time 0.1 0.05 0.6 color 255 236 248");   // parpadeo corto
    forPlayers(flashed, "fog @s push supernova:destello supernova_destello");
    soundTo(flashed, "ambient.weather.lightning.impact", 1, 0.5);
    forPlayers(darkened, "fog @s pop supernova_explosion");
  });
  at(T.restaurar, () => world.setTimeOfDay((previousTime + T.restaurar) % 24000));
  at(T.fin, () => {
    forPlayers(flashed, "fog @s pop supernova_destello");
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
