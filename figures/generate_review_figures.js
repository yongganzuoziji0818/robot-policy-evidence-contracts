const fs = require('fs');
const path = require('path');

const OUT = __dirname;
const W = 1800;
const H = 1000;
const C = {
  ink: '#1F2933', muted: '#52606D', grid: '#CBD5E1', paper: '#FFFFFF',
  blue: '#0072B2', sky: '#56B4E9', green: '#009E73', orange: '#E69F00',
  vermillion: '#D55E00', purple: '#CC79A7', yellow: '#F0E442', pale: '#F5F7FA'
};

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function wrap(text, maxChars) {
  const words = text.split(/\s+/);
  const lines = [];
  let line = '';
  for (const word of words) {
    if (!line || `${line} ${word}`.length <= maxChars) line = line ? `${line} ${word}` : word;
    else { lines.push(line); line = word; }
  }
  if (line) lines.push(line);
  return lines;
}

function textBlock(x, y, text, opts = {}) {
  const size = opts.size || 28;
  const weight = opts.weight || 400;
  const fill = opts.fill || C.ink;
  const anchor = opts.anchor || 'middle';
  const lines = Array.isArray(text) ? text : wrap(text, opts.maxChars || 30);
  const lineHeight = opts.lineHeight || size * 1.24;
  return `<text x="${x}" y="${y}" text-anchor="${anchor}" font-family="Arial, Helvetica, sans-serif" font-size="${size}" font-weight="${weight}" fill="${fill}">${lines.map((line, i) => `<tspan x="${x}" dy="${i === 0 ? 0 : lineHeight}">${esc(line)}</tspan>`).join('')}</text>`;
}

function rect(x, y, w, h, fill, stroke = C.ink, rx = 18, sw = 2) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
}

function arrow(x1, y1, x2, y2, color = C.muted, dash = '') {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="4" ${dash ? `stroke-dasharray="${dash}"` : ''} marker-end="url(#arrow)"/>`;
}

function shell(title, subtitle, body) {
  const compact = title.startsWith('Figure 1');
  const height = compact ? 900 : H;
  const shift = compact ? 135 : 90;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${height}" viewBox="0 0 ${W} ${height}">
  <defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="${C.muted}"/></marker></defs>
  <rect width="${W}" height="${height}" fill="${C.paper}"/>
  <g transform="translate(0 -${shift})">${body}</g>
  </svg>`;
}

function figure1() {
  const claims = [
    ['C0', 'Trace plausibility'], ['C1', 'Fixed-policy value'], ['C2', 'Prespecified ranking'],
    ['C3', 'Policy selection'], ['C4', 'Policy optimization'], ['C5', 'Safety / deployment']
  ];
  const contracts = [
    ['K1', 'Execution'], ['K2', 'Intervention'], ['K3', 'Outcome'], ['K4', 'Support'],
    ['K5', 'Decision'], ['K6', 'Selection uncertainty'], ['K7', 'Transport']
  ];
  const witnesses = [
    'versions, seeds, solver envelope', 'counterfactual actions, closed loop',
    'validated reward / safety judge', 'coverage, OOD, overlap',
    'value error, rank, regret, FN loss', 'simultaneous intervals, held-out anchor',
    'paired target trials, shift assumptions'
  ];
  let b = '';
  b += textBlock(70, 180, ['Decision claims'], {size: 25, weight: 700, anchor: 'start', fill: C.blue});
  const cw = 250, gap = 26, cx0 = 80, cy = 215;
  claims.forEach((d, i) => {
    const x = cx0 + i * (cw + gap);
    b += rect(x, cy, cw, 105, i < 3 ? '#E6F4FA' : '#FFF3E0', i < 3 ? C.blue : C.orange);
    b += textBlock(x + 24, cy + 38, [d[0]], {size: 25, weight: 700, anchor: 'start', fill: i < 3 ? C.blue : C.vermillion});
    b += textBlock(x + cw / 2, cy + 75, d[1], {size: 22, maxChars: 20});
    if (i < claims.length - 1) b += arrow(x + cw, cy + 52, x + cw + gap - 6, cy + 52, C.grid);
  });
  b += textBlock(70, 395, ['Evidence contracts'], {size: 25, weight: 700, anchor: 'start', fill: C.green});
  const kw = 205, kgap = 35, kx0 = 80, ky = 430;
  contracts.forEach((d, i) => {
    const x = kx0 + i * (kw + kgap);
    b += rect(x, ky, kw, 95, '#EAF7F2', C.green);
    b += textBlock(x + 22, ky + 35, [d[0]], {size: 23, weight: 700, anchor: 'start', fill: C.green});
    b += textBlock(x + kw / 2, ky + 68, d[1], {size: 20, maxChars: 18});
  });
  b += arrow(900, ky - 18, 900, cy + 116, C.muted);
  b += textBlock(930, 382, ['Claim-dependent coverage; contracts are not mapped one-to-one to levels'], {size: 20, anchor: 'start', fill: C.muted});
  b += textBlock(70, 610, ['Representative witnesses'], {size: 25, weight: 700, anchor: 'start', fill: C.purple});
  const wy = 650;
  witnesses.forEach((d, i) => {
    const x = kx0 + i * (kw + kgap);
    b += rect(x, wy, kw, 112, '#FBF0F7', C.purple);
    b += textBlock(x + kw / 2, wy + 38, d, {size: 19, maxChars: 21, lineHeight: 23});
    b += `<line x1="${x + kw / 2}" y1="${wy - 8}" x2="${x + kw / 2}" y2="${ky + 106}" stroke="${C.grid}" stroke-width="4" stroke-dasharray="8 7"/>`;
  });
  b += rect(80, 850, 1640, 145, C.pale, C.grid, 14, 2);
  b += textBlock(110, 895, ['Interpretation rule'], {size: 24, weight: 700, anchor: 'start', fill: C.ink});
  b += textBlock(110, 936, ['Stronger decisions add obligations, but the ordering is partial: correct ranking does not imply calibrated value,', 'and internal verification does not imply target-domain transport.'], {size: 23, anchor: 'start', lineHeight: 30});
  return shell('Figure 1 | Claim–contract–witness architecture', 'Evidence strength is defined relative to a prespecified decision and context of use.', b);
}

function figure2() {
  const rows = [
    ['Visual realism', 'Unseen action has opposite consequence', 'K2 intervention', 'C0 only'],
    ['Action replay', 'Closed-loop state drift changes later actions', 'K4 support', 'Bounded intervention test'],
    ['High correlation', 'One consequential top-pair reversal', 'K5 decision', 'Aggregate association'],
    ['Perfect finite ranking', 'New selected policy lies outside tested set', 'K4 + K6', 'Fixed-set C2'],
    ['Pointwise interval', 'Winner selected from many noisy candidates', 'K6 selection uncertainty', 'Fixed-policy C1'],
    ['Calibration fit', 'Equivalent fits disagree on target quantity', 'K7 transport', 'Measured quantities only'],
    ['Numerical convergence', 'Omitted target mechanism reverses order', 'K7 transport', 'Stable synthetic result']
  ];
  let b = '';
  const cols = [80, 430, 955, 1310];
  const widths = [300, 470, 305, 410];
  const labels = ['Common proxy', 'Counterexample mechanism', 'Missing contract', 'Strongest defensible claim'];
  labels.forEach((l, i) => {
    b += rect(cols[i], 185, widths[i], 66, i === 0 ? '#E6F4FA' : i === 1 ? '#FFF3E0' : i === 2 ? '#EAF7F2' : '#FBF0F7', C.grid, 8, 1.5);
    b += textBlock(cols[i] + widths[i] / 2, 226, [l], {size: 22, weight: 700});
  });
  rows.forEach((r, idx) => {
    const y = 275 + idx * 105;
    const fill = idx % 2 === 0 ? C.paper : C.pale;
    for (let i = 0; i < 4; i++) {
      b += rect(cols[i], y, widths[i], 82, fill, C.grid, 5, 1.2);
      b += textBlock(cols[i] + 18, y + 30, r[i], {size: 19, anchor: 'start', maxChars: i === 1 ? 42 : 28, lineHeight: 23, weight: i === 0 ? 700 : 400});
    }
    b += arrow(cols[0] + widths[0] + 6, y + 41, cols[1] - 9, y + 41, C.muted);
    b += arrow(cols[1] + widths[1] + 6, y + 41, cols[2] - 9, y + 41, C.muted);
    b += arrow(cols[2] + widths[2] + 6, y + 41, cols[3] - 9, y + 41, C.muted);
  });
  b += textBlock(90, 1045, ['A proxy remains useful as a diagnostic; the map limits the stronger claim that cannot be inferred without an additional witness.'], {size: 22, anchor: 'start', fill: C.muted, maxChars: 125});
  return shell('Figure 2 | Proxy insufficiency map', 'Elementary counterexamples identify the first unsupported link in common evaluator arguments.', b);
}

function figure3() {
  const groups = [
    ['Direct robot-policy evaluators', 15, C.blue],
    ['Reviews, position papers, standards', 7, C.orange],
    ['Decision-aware model theory', 7, C.green],
    ['Selection, calibration, transport', 6, C.purple],
    ['Execution and co-simulation', 4, C.vermillion]
  ];
  let b = '';
  b += textBlock(85, 180, ['A  Corpus composition'], {size: 26, weight: 700, anchor: 'start'});
  const x0 = 110, maxW = 650, y0 = 225;
  groups.forEach((g, i) => {
    const y = y0 + i * 105;
    const w = maxW * g[1] / 15;
    b += textBlock(x0, y + 28, [g[0]], {size: 20, anchor: 'start'});
    b += rect(x0, y + 45, maxW, 35, C.pale, C.grid, 5, 1);
    b += rect(x0, y + 45, w, 35, g[2], g[2], 5, 1);
    b += textBlock(x0 + w + 18, y + 71, [`n = ${g[1]}`], {size: 20, anchor: 'start', weight: 700});
  });
  b += textBlock(920, 180, ['B  Evidence-role map'], {size: 26, weight: 700, anchor: 'start'});
  const nodes = [
    [970, 245, 270, 95, '#E6F4FA', 'Direct evaluator studies', 'paired outcomes, ranks, safety tests'],
    [1390, 245, 270, 95, '#FFF3E0', 'Context sources', 'reviews, standards, project records'],
    [970, 465, 270, 95, '#EAF7F2', 'Formal / methodological', 'model adequacy, selection, transport'],
    [1390, 465, 270, 95, '#FBF0F7', 'Execution evidence', 'solver, scheduler, coupling semantics'],
    [1180, 735, 310, 115, '#FFFBE6', 'Claim-relative synthesis', 'C0–C5 × K1–K7 × witnesses']
  ];
  nodes.forEach((n, i) => {
    b += rect(n[0], n[1], n[2], n[3], n[4], C.grid, 14, 2);
    b += textBlock(n[0] + n[2] / 2, n[1] + 35, [n[5]], {size: 21, weight: 700});
    b += textBlock(n[0] + n[2] / 2, n[1] + 67, n[6], {size: 18, maxChars: 30, fill: C.muted});
    if (i < 4) b += arrow(n[0] + n[2] / 2, n[1] + n[3] + 5, 1335, 720, C.muted);
  });
  b += rect(90, 900, 1620, 110, C.pale, C.grid, 14, 2);
  b += textBlock(120, 942, ['Reading boundary'], {size: 23, weight: 700, anchor: 'start'});
  b += textBlock(120, 978, ['Counts describe the purposive 39-record review corpus, not study quality or K1–K7 reporting frequency. Evidence classes remain distinct in the ledger.'], {size: 21, anchor: 'start', maxChars: 125});
  return shell('Figure 3 | Literature landscape of the structured review', 'The corpus combines direct evaluator evidence with theory, statistics, validation, and execution semantics.', b);
}

async function writeFigure(stem, svg) {
  const svgPath = path.join(OUT, `${stem}.svg`);
  fs.writeFileSync(svgPath, svg, 'utf8');
}

(async () => {
  await writeFigure('Fig1', figure1());
  await writeFigure('Fig2', figure2());
  await writeFigure('Fig3', figure3());
  console.log('Generated Fig1.svg, Fig2.svg, and Fig3.svg without visible titles.');
})().catch(err => { console.error(err); process.exit(1); });
