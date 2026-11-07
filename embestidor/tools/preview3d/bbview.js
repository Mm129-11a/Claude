// Uso: node bbview.js trabajos.json   ->  [{"bbmodel": ruta, "view": {...}, "out": ruta.png}, ...]
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch({ args: ['--allow-file-access-from-files', '--use-gl=swiftshader'] });
  for (const j of jobs) {
    const p = await b.newPage({ viewport: { width: j.view.width, height: j.view.height } });
    p.on('pageerror', e => console.log('error', e.message));
    await p.goto('file://' + __dirname + '/bbview.html');
    await p.waitForFunction('window.ready === true');
    const url = await p.evaluate(([bb, v]) => window.draw(bb, v), [JSON.parse(fs.readFileSync(j.bbmodel, 'utf8')), j.view]);
    fs.writeFileSync(j.out, Buffer.from(url.split(',')[1], 'base64'));
    await p.close();
  }
  await b.close();
})();
