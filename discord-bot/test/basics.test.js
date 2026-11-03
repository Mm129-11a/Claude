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

import { respond, normalize } from '../src/chat.js';

test('free chat engine understands common messages', () => {
  assert.equal(normalize('¡Holaaa NETVI!'), '¡hola netvi!');
  assert.equal(respond('@Netvi', 'Ana').anim, 'wave');                       // just called by name
  assert.match(respond('Oye netvy', 'Jomm').text, /Jomm|Aquí|Presente/);
  assert.equal(respond('hola netvi', 'Ana').anim, 'wave');
  assert.match(respond('netvi tira un dado', 'Ana').text, /🎲 .*\*\*[1-6]\*\*/);
  assert.match(respond('netvi pizza o tacos?', 'Ana').text, /pizza|tacos/);
  assert.equal(respond('cuentame un chiste netvi', 'Ana').anim, 'dance');
  assert.match(respond('oye netvi, eres un bot?', 'Ana').text, /bot|muñeco/);
  assert.match(respond('netvi por que el cielo es azul?', 'Ana').text, /cielo|pensar/);
  assert.ok(respond('netvi ayer fui al estadio', 'Ana').text.length > 0);
});

test('"A or B" questions answer with one of the options, not the lead-in words', () => {
  for (let i = 0; i < 20; i++) {
    const text = respond('Pero cuál sushi o tacos', 'Jomm').text;
    assert.match(text, /\*\*(sushi|tacos)\*\*/);
    assert.ok(!/\*\*[^*]*(pero|cual)[^*]*\*\*/.test(text), text);   // the chosen option has no lead-in words
  }
  assert.match(respond('qué prefieres, playa o montaña?', 'Ana').text, /playa|montaña/);
});

import { solveMath } from '../src/math.js';
import { knowledgeTopic } from '../src/knowledge.js';
import { cleanText } from '../src/chat.js';

test('solves maths written with words or symbols', () => {
  const r = t => solveMath(cleanText(t))?.result;
  assert.equal(r('netvi cuánto es 12 por 7?'), '84');
  assert.equal(r('raíz de 81'), '9');
  assert.equal(r('20% de 150'), '30');
  assert.equal(r('(3+4)*2'), '14');
  assert.equal(r('2 elevado a 10'), '1024');
  assert.equal(r('100 entre 8'), '12,5');
  assert.equal(solveMath(cleanText('10 / 0')).result, null);
  assert.equal(solveMath(cleanText('tengo 3 perros')), null);
  assert.equal(solveMath(cleanText('pizza o tacos?')), null);
});

test('spots general-knowledge questions and their topic', () => {
  const k = t => knowledgeTopic(cleanText(t));
  assert.equal(k('netvi qué es un agujero negro?'), 'agujero negro');
  assert.equal(k('quién fue Albert Einstein'), 'albert einstein');
  assert.equal(k('cuál es la capital de Japón?'), 'capital de japon');
  assert.equal(k('netvi quién eres'), null);
  assert.equal(k('cuántos años tienes netvi'), null);
  assert.equal(k('cómo estás'), null);
});
