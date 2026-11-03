// The pre-rendered 3D GIFs in ../assets (made by `npm run render`).
import { AttachmentBuilder } from 'discord.js';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'assets');

export const ANIMS = ['idle', 'walk', 'wave', 'wow', 'shrug', 'dance', 'talk', 'think', 'sleep', 'love', 'arrive', 'leave', 'angry', 'cry'];

export function gif(name) {
  const anim = ANIMS.includes(name) ? name : 'talk';
  return new AttachmentBuilder(path.join(dir, `${anim}.gif`), { name: `netvi-${anim}.gif` });
}

export const pick = arr => arr[Math.floor(Math.random() * arr.length)];
