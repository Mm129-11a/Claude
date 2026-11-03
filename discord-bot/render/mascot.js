/* Netvi mascot for the Discord bot GIFs: the same blocky character as the
   website (logo head, black shirt with the colour stripe), standing on a
   grass block. Every animation is a pose function of time, built to loop. */
(function () {
  const T = window.THREE;
  const TAU = Math.PI * 2;
  const W = 256, H = 256;

  const canvas = document.createElement('canvas');
  canvas.width = W; canvas.height = H;
  document.body.append(canvas);
  const renderer = new T.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H, false);
  renderer.outputEncoding = T.sRGBEncoding;
  renderer.setClearColor(new T.Color('#23272f'));

  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(24, W / H, 1, 600);
  camera.position.set(0, 42, 150);
  camera.lookAt(0, 20, 0);
  scene.add(new T.AmbientLight(0xffffff, 0.5));
  const key = new T.DirectionalLight(0xffffff, 0.8);
  key.position.set(-3, 5, 8);
  scene.add(key);

  const lambert = p => new T.MeshLambertMaterial(p);
  const color = hex => new T.Color(hex).convertSRGBToLinear();
  const texFrom = (w, h, draw, pixel) => {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    draw(c.getContext('2d'));
    const tex = new T.CanvasTexture(c);
    tex.encoding = T.sRGBEncoding;
    if (pixel) { tex.magFilter = T.NearestFilter; tex.minFilter = T.NearestFilter; tex.generateMipmaps = false; }
    return tex;
  };

  // Head faces: the Netvi logo on the front, black with a white edge elsewhere.
  const LOGO = [['#393838', '#fedc13', '#121112'], ['#24d2c5', '#f0030f', '#004ede'], ['#980fb3', '#fe5302', '#f9b36f']];
  const side = lambert({ map: texFrom(256, 256, g => {
    g.fillStyle = '#0b0b0b'; g.fillRect(0, 0, 256, 256);
    g.strokeStyle = '#fefefe'; g.lineWidth = 8; g.strokeRect(4, 4, 248, 248);
  }) });
  const logo = lambert({ map: texFrom(256, 256, g => {
    g.fillStyle = '#0b0b0b'; g.fillRect(0, 0, 256, 256);
    g.fillStyle = '#fefefe'; g.fillRect(10, 10, 236, 236);
    g.fillStyle = '#0b0b0b'; g.fillRect(30, 30, 196, 196);
    LOGO.forEach((row, r) => row.forEach((col, k) => {
      const x = 35 + k * 64, y = 35 + r * 64;
      g.fillStyle = col; g.fillRect(x, y, 58, 58);
      const s = g.createLinearGradient(x, y, x + 58, y + 58);
      s.addColorStop(0, 'rgba(255,255,255,0.22)'); s.addColorStop(0.6, 'rgba(255,255,255,0)'); s.addColorStop(1, 'rgba(0,0,0,0.12)');
      g.fillStyle = s; g.fillRect(x, y, 58, 58);
    }));
  }) });
  const shirt = lambert({ color: color('#1e1e1e') });
  const pants = lambert({ color: color('#2c2c2c') });
  const white = lambert({ color: color('#f2f2f2') });
  const yellow = lambert({ color: color('#fedc13') });
  const shirtFront = lambert({ map: texFrom(16, 24, g => {
    g.fillStyle = '#1e1e1e'; g.fillRect(0, 0, 16, 24);
    ['#fedc13', '#f0030f', '#004ede', '#24d2c5', '#980fb3', '#fe5302'].forEach((c, i) => { g.fillStyle = c; g.fillRect(2 + i * 2, 7, 2, 2); });
  }, true) });

  // Grass block the character stands on.
  const grassTop = lambert({ map: texFrom(16, 16, g => {
    const greens = ['#5fa83a', '#6bbf44', '#559a33', '#74c94c'];
    for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) { g.fillStyle = greens[(x * 7 + y * 13 + x * y) % 4]; g.fillRect(x, y, 1, 1); }
  }, true) });
  const grassSide = lambert({ map: texFrom(16, 16, g => {
    const dirt = ['#8b5a2b', '#7a4e25', '#996633', '#6e4420'];
    for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) {
      const edge = 3 + ((x * 5) % 3 === 0 ? 1 : 0);
      g.fillStyle = y < edge ? ['#5fa83a', '#6bbf44'][(x + y) % 2] : dirt[(x * 3 + y * 7 + x * y) % 4];
      g.fillRect(x, y, 1, 1);
    }
  }, true) });
  const dirtBottom = lambert({ color: color('#6e4420') });

  const box = (w, h, d, mat, x = 0, y = 0, z = 0) => { const m = new T.Mesh(new T.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); return m; };
  scene.add(box(64, 10, 26, [grassSide, grassSide, grassTop, dirtBottom, grassSide, grassSide], 0, -5, 0));

  const root = new T.Group();   // feet at y = 0
  const body = new T.Group();
  root.add(body); scene.add(root);
  body.add(box(8, 12, 4, [shirt, shirt, shirt, shirt, shirtFront, shirt], 0, 18, 0));
  const neck = new T.Group(); neck.position.y = 24; body.add(neck);
  neck.add(box(11, 11, 11, [side, side, side, side, logo, side], 0, 5.5, 0));
  const arm = x => { const g = new T.Group(); g.position.set(x, 22, 0); g.add(box(4, 8, 4, shirt, 0, -2, 0), box(4, 4, 4, white, 0, -8, 0)); body.add(g); return g; };
  const leg = x => { const g = new T.Group(); g.position.set(x, 12, 0); g.add(box(4, 9, 4, pants, 0, -4.5, 0), box(4, 3, 4, white, 0, -10.5, 0)); root.add(g); return g; };
  const armL = arm(6), armR = arm(-6);   // armL is on the viewer's right
  const legL = leg(2), legR = leg(-2);

  // Floating symbols ("!", "?", "z", hearts, notes) drawn as sprites.
  const symbolMat = (ch, col) => new T.SpriteMaterial({ map: texFrom(64, 64, g => {
    g.font = 'bold 54px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.lineWidth = 8; g.strokeStyle = '#0b0b0b'; g.strokeText(ch, 32, 35);
    g.fillStyle = col; g.fillText(ch, 32, 35);
  }), transparent: true, depthTest: false });
  const SYMBOLS = { bang: symbolMat('!', '#fedc13'), ask: symbolMat('?', '#24d2c5'), zzz: symbolMat('z', '#ffffff'), heart: symbolMat('♥', '#f0030f'), note: symbolMat('♪', '#fedc13') };
  // Anger vein (the cartoon "💢"): four thick red brackets bending towards the centre.
  SYMBOLS.anger = new T.SpriteMaterial({ map: texFrom(96, 96, g => {
    g.lineCap = 'round'; g.lineJoin = 'round';
    [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sy]) => {
      const c = v => 48 + v;
      g.beginPath();
      g.moveTo(c(sx * 8), c(sy * 34));
      g.quadraticCurveTo(c(sx * 10), c(sy * 10), c(sx * 34), c(sy * 8));
      g.lineWidth = 17; g.strokeStyle = '#0b0b0b'; g.stroke();
      g.lineWidth = 10; g.strokeStyle = '#ff2a2a'; g.stroke();
    });
  }), transparent: true, depthTest: false });
  // Tear drop: light blue with a white shine.
  SYMBOLS.tear = new T.SpriteMaterial({ map: texFrom(64, 64, g => {
    g.beginPath();
    g.moveTo(32, 6); g.bezierCurveTo(44, 26, 52, 36, 52, 44); g.arc(32, 44, 20, 0, Math.PI); g.bezierCurveTo(12, 36, 20, 26, 32, 6);
    g.lineWidth = 5; g.strokeStyle = '#0b3a6e'; g.stroke();
    g.fillStyle = '#4fb4ff'; g.fill();
    g.fillStyle = 'rgba(255,255,255,.8)'; g.beginPath(); g.ellipse(25, 42, 4, 7, -0.4, 0, Math.PI * 2); g.fill();
  }), transparent: true, depthTest: false });
  const sprites = [0, 1, 2, 3, 4, 5].map(() => { const s = new T.Sprite(SYMBOLS.bang); s.visible = false; scene.add(s); return s; });

  const BASE = { x: 0, hop: 0, rotY: 0, bodyY: 0, bodyZ: 0, headX: 0, headY: 0, headZ: 0, aLx: 0, aLz: 0.08, aRx: 0, aRz: -0.08, lLx: 0, lRx: 0, fx: [] };
  const breathe = t => ({ bodyY: Math.sin(t * TAU / 2) * 0.25, aLz: 0.08 + Math.sin(t * TAU / 2) * 0.04, aRz: -0.08 - Math.sin(t * TAU / 2) * 0.04 });
  const stride = (t, period) => {
    const s = Math.sin(t * TAU / period);
    return { lLx: s * 0.6, lRx: -s * 0.6, aLx: -s * 0.55, aRx: s * 0.55, bodyY: Math.abs(Math.cos(t * TAU / period)) * 0.6, hop: Math.abs(Math.cos(t * TAU / period)) * 0.5 };
  };
  const waving = t => ({ aRx: -0.15, aRz: -2.6 + Math.sin(t * TAU * 1.6) * 0.32, headZ: 0.12, headY: -0.12 });
  const ease = p => p * p * (3 - 2 * Math.max(0, Math.min(1, p)));
  const clamp01 = p => Math.max(0, Math.min(1, p));

  // name: [loop seconds, pose(t)]
  const ANIMS = {
    idle: [2, t => ({ ...breathe(t), headY: Math.sin(t * TAU / 2) * 0.15 })],
    walk: [1, t => ({ ...stride(t, 1), rotY: 0.55 })],
    wave: [1.25, t => ({ ...breathe(t), ...waving(t) })],
    wow: [2, t => {
      const p = t % 2;
      const jump = p < 0.5 ? Math.sin(p / 0.5 * Math.PI) * 6 : 0;
      return p < 0.9
        ? { hop: jump, aLz: 2.4, aRz: -2.4, headX: -0.3, fx: [{ s: 'bang', x: 9, y: 41, k: Math.min(1, p / 0.12) }] }
        : { ...breathe(t), aLx: -0.35, aLz: 1.15, aRx: -0.35, aRz: -1.15, headX: 0.12, fx: [{ s: 'bang', x: 9, y: 41, k: p < 1.7 ? 1 : 0 }] };
    }],
    shrug: [2, t => ({ ...breathe(t), aLx: -0.55, aLz: 0.5, aRx: -0.55, aRz: -0.5, headZ: 0.22 + Math.sin(t * TAU / 2) * 0.05, bodyY: Math.max(0, Math.sin(t * TAU / 2)) * 0.9 })],
    dance: [1, t => {
      const s = Math.sin(t * TAU), c = Math.cos(t * TAU * 2);
      return { hop: Math.abs(c) * 2, bodyZ: s * 0.12, rotY: s * 0.35, headZ: -s * 0.2, aLz: 2.2 + s * 0.4, aRz: -0.6 + s * 0.4, lLx: s * 0.3, lRx: -s * 0.3,
        fx: [{ s: 'note', x: -14 + s * 2, y: 34 + (t % 1) * 10, k: 1 - (t % 1) * 0.6 }] };
    }],
    talk: [1.5, t => ({ ...breathe(t), headX: Math.sin(t * TAU / 0.375) * 0.07, headY: Math.sin(t * TAU / 1.5) * 0.18,
      aLx: -0.9 + Math.sin(t * TAU / 0.75) * 0.25, aLz: 0.35 + Math.sin(t * TAU / 1.5) * 0.15 })],
    think: [2, t => ({ ...breathe(t), aRx: -1.75, aRz: 0.45, headZ: 0.18, headX: -0.08 + Math.sin(t * TAU / 2) * 0.04,
      fx: [{ s: 'ask', x: 9, y: 41 + Math.sin(t * TAU / 2) * 1.2, k: 1 }] })],
    sleep: [3, t => ({ bodyY: Math.sin(t * TAU / 3) * 0.35, headX: 0.38, headZ: 0.12, aLz: 0.05, aRz: -0.05,
      fx: [0, 1, 2].map(i => { const p = ((t / 3) + i / 3) % 1; return { s: 'zzz', x: 8 + p * 8, y: 34 + p * 14, k: (0.5 + p * 0.7) * (p < 0.85 ? 1 : (1 - p) / 0.15) }; }) })],
    // Stamping and shaking fists, leaning forward, with an anger vein above the head.
    angry: [1, t => {
      const p = t % 1, s1 = Math.sin(p * TAU), shake = Math.sin(p * TAU * 8);
      return { bodyZ: shake * 0.05, headX: -0.25, headZ: shake * 0.06,
        aRx: -0.15, aRz: -2.75 + Math.sin(p * TAU * 4) * 0.3,          // fist shaking in the air
        aLx: 0.25, aLz: 0.18 + shake * 0.05,                             // other fist clenched at the side
        lLx: Math.max(0, s1) * 0.6, lRx: Math.max(0, -s1) * 0.6, hop: Math.abs(s1) * 1.2,   // stamping
        fx: [{ s: 'anger', x: 9, y: 40 + shake * 0.3, k: 1.5 + Math.max(0, Math.sin(p * TAU * 2)) * 0.35 }] };
    }],
    // Hands over the face, sobbing, with tears streaming down both sides.
    cry: [1.6, t => {
      const p = (t % 1.6) / 1.6;
      const tears = [0, 1, 2].flatMap(i => {
        const q = (p * 2 + i / 3) % 1;
        return [-1, 1].map(side => ({ s: 'tear', x: side * (6.5 + q * 2.5), y: 30 - q * 22, k: 0.55 * (q < 0.85 ? 1 : (1 - q) / 0.15) }));
      });
      return { bodyY: Math.abs(Math.sin(p * TAU * 2)) * 0.5, headX: 0.32 + Math.sin(p * TAU * 2) * 0.05, headZ: Math.sin(p * TAU) * 0.06,
        aLx: -2.15, aLz: -0.4, aRx: -2.15, aRz: 0.4, fx: tears };
    }],
    love: [1.5, t => {
      const p = (t % 1.5) / 1.5;
      return { ...breathe(t), hop: Math.max(0, Math.sin(p * TAU)) * 2, aLx: -0.9, aLz: -0.45, aRx: -0.9, aRz: 0.45, headZ: Math.sin(p * TAU) * 0.15,
        fx: [{ s: 'heart', x: -9 + p * 3, y: 36 + p * 10, k: 1 - p * 0.5 }, { s: 'heart', x: 10 - p * 2, y: 38 + ((p + 0.5) % 1) * 10, k: 0.8 - ((p + 0.5) % 1) * 0.4 }] };
    }],
    // One-shot scenes (the GIF still loops, so they end where they start: off frame / centre).
    arrive: [2.6, t => {
      if (t < 1.4) { const p = t / 1.4; return { ...stride(t, 0.5), x: -46 + 46 * ease(p), rotY: 1.2 * (1 - clamp01((p - 0.8) / 0.2)) }; }
      return { ...breathe(t), ...waving(t), x: 0 };
    }],
    leave: [2.6, t => {
      if (t < 1.1) return { ...breathe(t), ...waving(t) };
      const p = (t - 1.1) / 1.5;
      return { ...stride(t, 0.5), x: 50 * ease(p), rotY: -1.2 * clamp01(p / 0.15) };
    }],
  };

  function pose(name, t) {
    const target = { ...BASE, ...ANIMS[name][1](t) };
    root.position.set(target.x, target.hop, 0);
    root.rotation.y = target.rotY;
    body.position.y = target.bodyY;
    body.rotation.z = target.bodyZ;
    neck.rotation.set(target.headX, target.headY, target.headZ);
    armL.rotation.set(target.aLx, 0, target.aLz);
    armR.rotation.set(target.aRx, 0, target.aRz);
    legL.rotation.x = target.lLx;
    legR.rotation.x = target.lRx;
    sprites.forEach((s, i) => {
      const f = target.fx[i];
      s.visible = !!f && f.k > 0.02;
      if (!s.visible) return;
      s.material = SYMBOLS[f.s];
      s.position.set(target.x + f.x, f.y + target.hop, 4);
      s.scale.setScalar(7 * f.k);
    });
    renderer.render(scene, camera);
  }

  // Renders frame i of n for an animation and returns its RGBA pixels as base64.
  const buf = new Uint8Array(W * H * 4), flipped = new Uint8Array(W * H * 4);
  window.renderFrame = (name, i, fps) => {
    const len = ANIMS[name][0];
    pose(name, (i / Math.round(len * fps)) * len);
    const g = renderer.getContext();
    g.readPixels(0, 0, W, H, g.RGBA, g.UNSIGNED_BYTE, buf);
    for (let y = 0; y < H; y++) flipped.set(buf.subarray((H - 1 - y) * W * 4, (H - y) * W * 4), y * W * 4);   // WebGL rows are bottom-up
    let bin = '';
    for (let k = 0; k < flipped.length; k += 0x8000) bin += String.fromCharCode.apply(null, flipped.subarray(k, k + 0x8000));
    return btoa(bin);
  };
  window.animInfo = (name, fps) => ({ width: W, height: H, count: Math.round(ANIMS[name][0] * fps) });
  window.ANIM_NAMES = Object.keys(ANIMS);
})();
