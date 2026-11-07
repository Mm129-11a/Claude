// Uso: node shot.js trabajos.json
// trabajos.json: {"geo": ruta, "anim": ruta, "tex": ruta, "width": W, "height": H,
//                 "jobs": [{"anims": [...], "t": segundos, "cam": {"pos": [...], "look": [...]}, "out": ruta.png}]}
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch({ args: ['--allow-file-access-from-files', '--use-gl=swiftshader'] });
  const p = await b.newPage({ viewport: { width: cfg.width, height: cfg.height } });
  p.on('pageerror', e => console.log('error', e.message));
  await p.goto('file://' + __dirname + '/model.html');
  await p.waitForFunction('window.ready === true', null, { timeout: 60000 });
  const tex = 'data:image/png;base64,' + fs.readFileSync(cfg.tex).toString('base64');
  await p.evaluate(([g, a, t, w, h]) => window.init(g, a, t, w, h),
    [JSON.parse(fs.readFileSync(cfg.geo, 'utf8')), JSON.parse(fs.readFileSync(cfg.anim, 'utf8')), tex, cfg.width, cfg.height]);
  for (const j of cfg.jobs) {
    const url = await p.evaluate(([n, t, c]) => window.renderAt(n, t, c), [j.anims, j.t, j.cam]);
    fs.writeFileSync(j.out, Buffer.from(url.split(',')[1], 'base64'));
  }
  await b.close();
})();
