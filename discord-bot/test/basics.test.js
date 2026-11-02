import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { inQuietHours } from '../src/config.js';
import { parseReply } from '../src/brain.js';
import { ANIMS } from '../src/anims.js';

test('reads the animation tag Claude puts first', () => {
  assert.deepEqual(parseReply('[anim:dance] ¡A bailar!'), { anim: 'dance', text: '¡A bailar!' });
  assert.deepEqual(parseReply('Sin etiqueta'), { anim: 'talk', text: 'Sin etiqueta' });
  assert.equal(parseReply('[anim:volar] hola').anim, 'talk');   // unknown animation
});

test('never lets a reply ping everyone', () => {
  assert.ok(!/@everyone/.test(parseReply('[anim:talk] hola @everyone').text));
});

test('quiet hours, including ranges past midnight', () => {
  const at = h => new Date(Date.UTC(2026, 0, 15, h, 30));
  assert.equal(inQuietHours(at(3), '1-9', 'UTC'), true);
  assert.equal(inQuietHours(at(12), '1-9', 'UTC'), false);
  assert.equal(inQuietHours(at(23), '22-7', 'UTC'), true);
  assert.equal(inQuietHours(at(6), '22-7', 'UTC'), true);
  assert.equal(inQuietHours(at(15), '22-7', 'UTC'), false);
  assert.equal(inQuietHours(at(3), '', 'UTC'), false);
});

test('every animation has its GIF', () => {
  for (const a of ANIMS) assert.ok(existsSync(new URL(`../assets/${a}.gif`, import.meta.url)), a);
});
