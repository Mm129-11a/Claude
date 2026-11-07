import { world, system, Player } from "@minecraft/server";

// El paquete de recursos detecta este prefijo en el título y muestra la animación
// en lugar del título normal. Debe coincidir con el de ui/death_anim.json.
const MARKER = "_death_:";

// Duración de la animación (8,9 s, igual que el video) en ticks.
const SHOW_TICKS = 178;

const CAUSES = {
  anvil: "aplastado por un yunque",
  blockExplosion: "voló por los aires",
  campfire: "se quemó en una fogata",
  contact: "se pinchó hasta morir",
  drowning: "se ahogó",
  entityAttack: "fue asesinado",
  entityExplosion: "voló por los aires",
  fall: "cayó desde muy alto",
  fallingBlock: "aplastado por un bloque",
  fire: "ardió en llamas",
  fireTick: "se quemó vivo",
  fireworks: "explotó con un cohete",
  flyIntoWall: "se estampó contra una pared",
  freezing: "murió congelado",
  lava: "intentó nadar en lava",
  lightning: "le cayó un rayo",
  maceSmash: "aplastado por una maza",
  magic: "murió por magia",
  magma: "pisó un bloque de magma",
  piston: "aplastado por un pistón",
  projectile: "fue disparado",
  ramAttack: "embestido",
  sonicBoom: "destrozado por un grito sónico",
  soulCampfire: "se quemó en una fogata de almas",
  stalactite: "atravesado por una estalactita",
  stalagmite: "empalado en una estalagmita",
  starve: "murió de hambre",
  suffocation: "se asfixió en una pared",
  temperature: "murió de calor",
  thorns: "murió intentando herir a alguien",
  void: "cayó al vacío",
  wither: "se marchitó",
};

const MOBS = {
  "minecraft:zombie": "un Zombi",
  "minecraft:husk": "un Zombi momificado",
  "minecraft:drowned": "un Ahogado",
  "minecraft:skeleton": "un Esqueleto",
  "minecraft:stray": "un Esqueleto glacial",
  "minecraft:bogged": "un Esqueleto pantanoso",
  "minecraft:creeper": "un Creeper",
  "minecraft:spider": "una Araña",
  "minecraft:cave_spider": "una Araña de cueva",
  "minecraft:enderman": "un Enderman",
  "minecraft:witch": "una Bruja",
  "minecraft:slime": "un Slime",
  "minecraft:magma_cube": "un Cubo de magma",
  "minecraft:blaze": "un Blaze",
  "minecraft:ghast": "un Ghast",
  "minecraft:piglin": "un Piglin",
  "minecraft:piglin_brute": "un Piglin bruto",
  "minecraft:zombie_pigman": "un Piglin zombificado",
  "minecraft:hoglin": "un Hoglin",
  "minecraft:zoglin": "un Zoglin",
  "minecraft:wither_skeleton": "un Esqueleto del Wither",
  "minecraft:wither": "el Wither",
  "minecraft:ender_dragon": "el Dragón de Ender",
  "minecraft:warden": "el Warden",
  "minecraft:pillager": "un Saqueador",
  "minecraft:vindicator": "un Vindicador",
  "minecraft:evocation_illager": "un Invocador",
  "minecraft:vex": "un Vex",
  "minecraft:ravager": "un Devastador",
  "minecraft:phantom": "un Phantom",
  "minecraft:guardian": "un Guardián",
  "minecraft:elder_guardian": "un Guardián anciano",
  "minecraft:shulker": "un Shulker",
  "minecraft:silverfish": "un Lepisma",
  "minecraft:endermite": "un Endermite",
  "minecraft:breeze": "un Breeze",
  "minecraft:wolf": "un Lobo",
  "minecraft:iron_golem": "un Gólem de hierro",
  "minecraft:bee": "una Abeja",
  "minecraft:polar_bear": "un Oso polar",
  "minecraft:goat": "una Cabra",
  "minecraft:llama": "una Llama",
  "minecraft:pufferfish": "un Pez globo",
  "minecraft:tnt": "una dinamita",
  "minecraft:ender_crystal": "un Cristal del End",
};

function nameOf(entity) {
  if (!entity) return undefined;
  try {
    if (entity instanceof Player) return entity.name;
    if (entity.nameTag) return entity.nameTag;
    if (MOBS[entity.typeId]) return MOBS[entity.typeId];
    const id = entity.typeId.replace(/^[^:]+:/, "").replace(/_/g, " ");
    return "un " + id.charAt(0).toUpperCase() + id.slice(1);
  } catch {
    return undefined; // la entidad ya no es válida
  }
}

function deathReason(source) {
  const cause = source?.cause ?? "none";
  const killer = nameOf(source?.damagingEntity);

  if (killer) {
    switch (cause) {
      case "projectile": return `fue disparado por ${killer}`;
      case "entityExplosion":
      case "blockExplosion": return `voló por los aires por ${killer}`;
      case "magic": return `murió por la magia de ${killer}`;
      case "thorns": return `murió intentando herir a ${killer}`;
      case "fall": return `cayó al vacío por culpa de ${killer}`;
      case "sonicBoom": return `fue destrozado por ${killer}`;
      default: return `fue asesinado por ${killer}`;
    }
  }
  return CAUSES[cause] ?? "murió";
}

function playDeathAnimation(victimName, reason) {
  for (const player of world.getAllPlayers()) {
    try {
      player.onScreenDisplay.setTitle(MARKER + victimName, {
        subtitle: reason,
        fadeInDuration: 0,
        stayDuration: SHOW_TICKS,
        fadeOutDuration: 0,
      });
      player.playSound("death_anim.sound");
    } catch {
      // jugador saliendo del mundo, se ignora
    }
  }
}

world.afterEvents.entityDie.subscribe(
  (event) => {
    const victim = event.deadEntity;
    if (!(victim instanceof Player)) return;
    const victimName = victim.name;
    const reason = deathReason(event.damageSource);
    // Un tick después, para que no se pise con la pantalla de muerte.
    system.run(() => playDeathAnimation(victimName, reason));
  },
  { entityTypes: ["minecraft:player"] }
);
