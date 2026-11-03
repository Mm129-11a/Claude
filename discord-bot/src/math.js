// Solves the maths in a message: "cuánto es 12 por 7", "raíz de 81",
// "20% de 150", "(3+4)*2", "2 elevado a 10", "100 entre 8"…
// Uses its own small parser (never eval), so nothing in a message can run as code.

const WORDS = [
  [/\braiz cubica de\b/g, ' ∛ '],
  [/\braiz cuadrada de\b|\braiz de\b/g, ' √ '],
  [/\bal cuadrado\b/g, ' ^ 2 '],
  [/\bal cubo\b/g, ' ^ 3 '],
  [/\belevado a(?: la)?\b|\ba la potencia\b|\*\*/g, ' ^ '],
  [/\bmas\b/g, ' + '],
  [/\bmenos\b/g, ' - '],
  [/\bmultiplicado por\b|\bpor\b|×|·/g, ' * '],
  [/\bdividido (?:entre|por|en)\b|\bentre\b|÷|:/g, ' / '],
  [/(\d)\s*x\s*(?=\d)/g, '$1 * '],
  [/\bmodulo\b|\bmod\b/g, ' % '],
  [/(\d+(?:\.\d+)?)\s*% de\s*/g, ' $1 / 100 * '],
  [/\bpi\b/g, ' π '],
];

function tokenize(src) {
  const tokens = [];
  const re = /\s*(\d+(?:\.\d+)?|[-+*/^%()√∛π])/y;
  let m;
  re.lastIndex = 0;
  while (re.lastIndex < src.length && (m = re.exec(src))) tokens.push(m[1]);
  if (src.slice(re.lastIndex).trim()) return null;   // something it does not understand
  return tokens;
}

/** Recursive-descent parser: + - , * / % , ^ , unary -, functions, parentheses. */
function evaluate(tokens) {
  let i = 0;
  const peek = () => tokens[i];
  const take = t => (tokens[i] === t ? (i++, true) : false);
  function primary() {
    const t = tokens[i++];
    if (t === undefined) throw new Error('fin');
    if (/^\d/.test(t)) return Number(t);
    if (t === 'π') return Math.PI;
    if (t === '(') { const v = expr(); if (!take(')')) throw new Error(')'); return v; }
    if (t === '√' || t === '∛') { const v = unary(); return t === '√' ? Math.sqrt(v) : Math.cbrt(v); }
    throw new Error(t);
  }
  function power() { const b = primary(); return take('^') ? b ** unary() : b; }
  function unary() { if (take('-')) return -unary(); if (take('+')) return unary(); return power(); }
  function term() {
    let v = unary();
    for (;;) {
      if (take('*')) v *= unary();
      else if (take('/')) v /= unary();
      else if (take('%')) v %= unary();
      else if (peek() === '(' || peek() === '√' || peek() === 'π') v *= unary();   // 2(3+4), 2π
      else return v;
    }
  }
  function expr() {
    let v = term();
    for (;;) {
      if (take('+')) v += term();
      else if (take('-')) v -= term();
      else return v;
    }
  }
  const v = expr();
  if (i !== tokens.length) throw new Error('sobra');
  return v;
}

const fmt = n => (Number.isInteger(n) ? n.toLocaleString('es') : Number(n.toPrecision(10)).toLocaleString('es', { maximumFractionDigits: 6 }));

/**
 * Returns { expression, result } if the message contains a calculation, else null.
 * `norm` is the message already lowercased and without accents.
 */
export function solveMath(norm) {
  let s = ` ${norm.replace(/(\d),(\d)/g, '$1.$2')} `;   // 3,5 -> 3.5
  for (const [re, to] of WORDS) s = s.replace(re, to);
  // Keep the longest stretch made only of maths characters (drops "cuánto es", "?"…).
  const pool = s.split(/[^\d.\s+\-*/^%()√∛π]+/).map(x => x.trim())
    .filter(x => /[\dπ]/.test(x) && /[+\-*/^%√∛]/.test(x))
    .sort((a, b) => b.length - a.length);
  for (const expression of pool) {
    const tokens = tokenize(expression);
    if (!tokens || tokens.length < 2) continue;
    try {
      const result = evaluate(tokens);
      if (!Number.isFinite(result)) return { expression: pretty(tokens), result: null };
      return { expression: pretty(tokens), result: fmt(result) };
    } catch { /* try the next candidate */ }
  }
  return null;
}

function pretty(tokens) {
  return tokens.map(t => ({ '*': '×', '/': '÷' }[t] || t)).join(' ')
    .replace(/\( /g, '(').replace(/ \)/g, ')').replace(/([√∛]) /g, '$1');
}
