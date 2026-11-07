import { world, system } from "@minecraft/server";

// Se lanza con /function supernova (que ejecuta: scriptevent supernova:iniciar)
const EVENT_ID = "supernova:iniciar";

const DISTANCE = 32;   // bloques delante de quien ejecuta el comando
const HEIGHT = 16;     // bloques por encima

// Momentos de la secuencia, en ticks (20 ticks = 1 segundo)
const T = {
  oscurecer: 10,     // se hace de noche y aparece la estrella
  temblor: 110,      // la estrella se hincha
  explosion: 130,    // explota
  destello: 150,     // llega el destello
  restaurar: 165,    // vuelve la hora de antes (el destello tapa el cielo)
  fin: 240,          // se quita la niebla del destello
};

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

function spawn(dimension, id, pos) {
  try {
    dimension.spawnParticle(id, pos);
  } catch (e) {
    console.warn(`[supernova] partícula ${id}: ${e}`);
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
  // la explosión un poco más cerca y el destello un poco más lejos, para que no se mezclen
  const near = { x: center.x - dx, y: center.y, z: center.z - dz };
  const far = { x: center.x + dx * 3, y: center.y, z: center.z + dz * 3 };

  const previousTime = world.getTimeOfDay();

  // 1. Todo se pone oscuro y nace la estrella
  cmd(dimension, "camera @a fade time 0.5 0.3 1.2 color 0 0 0");
  soundAll("ambient.weather.thunder", 0.4, 0.5);
  at(T.oscurecer, () => {
    world.setTimeOfDay(18000);
    cmd(dimension, "fog @a push supernova:oscuro supernova_oscuro");
    spawn(dimension, "supernova:estrella", center);
    soundAll("beacon.activate", 1, 0.6);
  });
  for (const t of [45, 80, 110]) at(t, () => soundAll("ambient.weather.thunder", 0.6, 0.6));
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
