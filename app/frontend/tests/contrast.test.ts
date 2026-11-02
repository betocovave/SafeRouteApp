import test from 'node:test';
import assert from 'node:assert/strict';
import { palettes } from '../src/theme/colors';

// Razón de contraste WCAG 2.x entre dos colores #RRGGBB.
function luminance(hex: string) {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255).map(c => c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const ratio = (a: string, b: string) => { const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };

for (const [name, p] of Object.entries(palettes)) {
  test(`${name}: el texto de los botones primarios (onBlue sobre blue) es legible`, () => {
    assert.ok(ratio(p.onBlue, p.blue) >= 4.5, `contraste ${ratio(p.onBlue, p.blue).toFixed(2)}`);
  });
  test(`${name}: texto principal, secundario y azul de enlaces son legibles sobre fondo y tarjeta`, () => {
    for (const bg of [p.background, p.surface]) for (const fg of [p.text, p.muted, p.blue]) assert.ok(ratio(fg, bg) >= 4.5, `${fg} sobre ${bg}: ${ratio(fg, bg).toFixed(2)}`);
  });
  test(`${name}: el azul de botones secundarios se lee sobre pale y las alertas sobre tarjeta`, () => {
    assert.ok(ratio(p.blue, p.pale) >= 4.5, `blue/pale ${ratio(p.blue, p.pale).toFixed(2)}`);
    assert.ok(ratio(p.danger, p.surface) >= 4.5 && ratio(p.green, p.surface) >= 4.5);
  });
}
