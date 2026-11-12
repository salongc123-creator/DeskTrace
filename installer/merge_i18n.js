// Build step (2.7.0 O7): fold the layered translation blocks of desktop_watch/static/i18n.js into one table.
//   node installer/merge_i18n.js <source i18n.js> <merged output>
// The window then parses one object per language instead of ~50 Object.assign blocks. The layered source
// stays the file to edit; the merged one is what the installer and the version licenses carry.
'use strict';
const fs = require('fs');
const vm = require('vm');
const [src, out] = process.argv.slice(2);
const code = fs.readFileSync(src, 'utf8');
const cut = code.indexOf('\nlet LANG');
if (cut < 0) throw new Error('no "let LANG" in ' + src);
const ctx = {};
vm.createContext(ctx);
vm.runInContext(code.slice(0, cut) + '\nthis.LANGS = LANGS; this.I18N = I18N;', ctx);
for (const lang of Object.keys(ctx.I18N))
  for (const [k, v] of Object.entries(ctx.I18N[lang]))
    if (typeof v !== 'string' && (typeof v !== 'object' || v === null)) throw new Error(`${lang}.${k}: not text`);
const merged = "'use strict';\n/* UI translations, merged at build time from the layered source (2.7.0 O7). Edit the source, not this file. */\n"
  + 'const LANGS = ' + JSON.stringify(ctx.LANGS) + ';\n'
  + 'const I18N = ' + JSON.stringify(ctx.I18N) + ';\n'
  + code.slice(cut + 1);
fs.writeFileSync(out, merged, 'utf8');
console.log(`merged ${Object.keys(ctx.I18N.en).length} en + ${Object.keys(ctx.I18N.zh).length} zh keys: ${(code.length / 1024) | 0} KB -> ${(merged.length / 1024) | 0} KB`);
