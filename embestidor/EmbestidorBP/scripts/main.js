import { world, system, EntityDamageCause } from "@minecraft/server";

// El Embestidor: persigue a los jugadores y los embiste. Al morir explota.
const ID = "embestidor:embestidor";

const EMBESTIDA = {
  danio: 5,            // 2,5 corazones (en medios corazones)
  alcance: 7,          // embiste si el jugador está a menos de esto (bloques); de más lejos se acerca andando
  preparar: 7,         // ticks que se agacha antes de lanzarse
  duracion: 12,        // ticks que dura la carrera
  velocidad: 0.6,      // bloques por tick durante la carrera (unos 7 bloques en total)
  golpe: 1.7,          // distancia a la que te golpea
  espera: 40,          // ticks de descanso entre embestidas
  empuje: 1.4,         // cuánto te empuja
};
const EXPLOSION = {
  danio: 4,            // 2 corazones
  radio: 4,            // bloques
};

const states = new Map();   // id del mob -> { fase, t, espera, dir }

// Quita exactamente esa vida (aunque lleve armadura o le acaben de golpear)
function hurt(entity, hp, source) {
  const health = entity.getComponent("minecraft:health");
  if (!health || hp <= 0) return;
  const target = Math.max(0, health.currentValue - hp);
  try {
    const opts = { cause: source ? EntityDamageCause.entityAttack : EntityDamageCause.entityExplosion };
    if (source) opts.damagingEntity = source;
    entity.applyDamage(hp, opts);
  } catch {
    // modo creativo o entidad que no recibe daño
  }
  try {
    if (entity.isValid() && health.currentValue > target + 0.01) {
      if (target <= 0) entity.kill();
      else health.setCurrentValue(target);
    }
  } catch {
    // ya no existe
  }
}

function push(entity, dx, dz, h, v) {
  const l = Math.hypot(dx, dz) || 1;
  try {
    entity.applyKnockback(dx / l, dz / l, h, v);                     // @minecraft/server 1.x
  } catch {
    try {
      entity.applyKnockback({ x: (dx / l) * h, z: (dz / l) * h }, v);   // 2.x
    } catch {
      // no se puede empujar
    }
  }
}

function canBeHit(player) {
  try {
    const mode = String(player.getGameMode()).toLowerCase();
    return mode !== "creative" && mode !== "spectator";
  } catch {
    return true;
  }
}

function nearestPlayer(mob) {
  let best;
  let bestD = Infinity;
  for (const p of mob.dimension.getPlayers({ location: mob.location, maxDistance: EMBESTIDA.alcance })) {
    if (!canBeHit(p)) continue;
    const d = Math.hypot(p.location.x - mob.location.x, p.location.z - mob.location.z);
    if (d < bestD) {
      best = p;
      bestD = d;
    }
  }
  return best ? { player: best, dist: bestD } : undefined;
}

function sound(mob, id, pitch = 1) {
  try {
    mob.dimension.playSound(id, mob.location, { volume: 1, pitch });
  } catch {
    // sonido no disponible
  }
}

function tick(mob) {
  let s = states.get(mob.id);
  if (!s) {
    s = { fase: "libre", t: 0, espera: 20, dir: { x: 0, z: 1 }, objetivo: undefined };
    states.set(mob.id, s);
  }
  s.t++;
  if (s.espera > 0) s.espera--;

  if (s.fase === "libre") {
    if (s.espera > 0) return;
    const near = nearestPlayer(mob);
    if (!near) return;
    // se prepara: mira al jugador y se agacha
    const dx = near.player.location.x - mob.location.x;
    const dz = near.player.location.z - mob.location.z;
    const l = Math.hypot(dx, dz) || 1;
    s.dir = { x: dx / l, z: dz / l };
    s.objetivo = near.player;
    s.fase = "preparar";
    s.t = 0;
    try {
      mob.setRotation({ x: 0, y: (Math.atan2(-s.dir.x, s.dir.z) * 180) / Math.PI });
    } catch {
      // sin giro
    }
    try {
      mob.playAnimation("animation.embestidor.embestir");
    } catch {
      // versión sin playAnimation
    }
    sound(mob, "mob.goat.prepare_ram", 0.8);
    return;
  }

  if (s.fase === "preparar") {
    if (s.t >= EMBESTIDA.preparar) {
      s.fase = "carrera";
      s.t = 0;
      sound(mob, "mob.ravager.roar", 1.4);
    }
    return;
  }

  if (s.fase === "carrera") {
    try {
      // velocidad constante en la dirección del jugador (el rozamiento no la frena)
      const v = mob.getVelocity();
      mob.clearVelocity();
      mob.applyImpulse({ x: s.dir.x * EMBESTIDA.velocidad, y: Math.min(v.y, 0), z: s.dir.z * EMBESTIDA.velocidad });
    } catch {
      // sin impulso
    }
    const p = s.objetivo;
    if (p && p.isValid()) {
      const d = Math.hypot(p.location.x - mob.location.x, p.location.y - mob.location.y, p.location.z - mob.location.z);
      if (d < EMBESTIDA.golpe && canBeHit(p)) {
        hurt(p, EMBESTIDA.danio, mob);
        push(p, s.dir.x, s.dir.z, EMBESTIDA.empuje, 0.4);
        sound(mob, "mob.goat.ram_impact", 1);
        s.fase = "libre";
        s.espera = EMBESTIDA.espera;
        return;
      }
    }
    if (s.t >= EMBESTIDA.duracion) {
      s.fase = "libre";
      s.espera = EMBESTIDA.espera - 10;
    }
  }
}

system.runInterval(() => {
  for (const dimId of ["overworld", "nether", "the_end"]) {
    let mobs = [];
    try {
      mobs = world.getDimension(dimId).getEntities({ type: ID });
    } catch {
      continue;
    }
    for (const mob of mobs) {
      try {
        tick(mob);
      } catch (e) {
        console.warn(`[embestidor] ${e}`);
      }
    }
  }
}, 1);

// Al morir explota: quita 2 corazones a todo lo que esté cerca (sin romper bloques)
world.afterEvents.entityDie.subscribe(
  (event) => {
    const mob = event.deadEntity;
    let dim;
    let at;
    try {
      dim = mob.dimension;
      at = { ...mob.location };
    } catch {
      return;
    }
    states.delete(mob.id);
    try {
      dim.spawnParticle("minecraft:huge_explosion_emitter", { x: at.x, y: at.y + 0.6, z: at.z });
    } catch {
      // sin partícula
    }
    try {
      dim.playSound("random.explode", at, { volume: 4, pitch: 1 });
    } catch {
      // sin sonido
    }
    for (const e of dim.getEntities({ location: at, maxDistance: EXPLOSION.radio })) {
      try {
        if (e.id === mob.id || !e.getComponent("minecraft:health")) continue;
        if (e.typeId === "minecraft:player" && !canBeHit(e)) continue;
        hurt(e, EXPLOSION.danio);
        push(e, e.location.x - at.x, e.location.z - at.z, 0.8, 0.35);
      } catch {
        // ya no existe
      }
    }
  },
  { entityTypes: [ID] }
);
