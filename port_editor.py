#!/usr/bin/env python3
"""port_editor.py — browser-based snap-point editor for P&ID SVG symbols.

Starts a local HTTP server and opens the editor in the default browser.

Usage
-----
    python port_editor.py                           # ./symbols root, port 7421
    python port_editor.py --symbols /path/to/syms
    python port_editor.py --port 8080
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import pathlib
import threading
import urllib.parse
import webbrowser

# ── globals set in main() ─────────────────────────────────────────────────────
SYMBOLS_ROOT: pathlib.Path
SERVER_PORT: int

# ── single-page app HTML/CSS/JS ───────────────────────────────────────────────
# (raw string — no f-string interpolation; the JS template literals are fine)
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Port Editor</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { display: flex; height: 100vh; font-family: 'Consolas', monospace;
       font-size: 13px; background: #1e1e1e; color: #d4d4d4; overflow: hidden; }

/* ── panels ── */
#left   { width: 230px; border-right: 1px solid #444;
          display: flex; flex-direction: column; }
#center { flex: 1; display: flex; flex-direction: column;
          align-items: center; justify-content: center; background: #2a2a2a; }
#right  { width: 280px; border-left: 1px solid #444;
          overflow-y: auto; padding: 10px; }

/* ── left panel ── */
#left-header { padding: 8px; font-weight: bold; border-bottom: 1px solid #444; }
#sym-search  { width: 100%; margin-top: 6px; padding: 3px 6px;
               background: #3c3c3c; border: 1px solid #555;
               color: #d4d4d4; border-radius: 3px; }
#sym-list    { flex: 1; overflow-y: auto; padding: 4px; }
.grp-head    { font-size: 10px; color: #888; margin: 8px 0 2px 4px;
               text-transform: uppercase; letter-spacing: 1px; }
.sym-item    { padding: 3px 8px; border-radius: 3px; cursor: pointer;
               font-size: 12px; white-space: nowrap;
               overflow: hidden; text-overflow: ellipsis; }
.sym-item:hover  { background: #3c3c3c; }
.sym-item.active { background: #094771; color: #fff; }

/* ── center ── */
#status-bar  { font-size: 11px; color: #888; margin-bottom: 8px;
               max-width: 90%; text-align: center; }
#canvas-wrap { background: white; box-shadow: 0 0 24px rgba(0,0,0,.6);
               line-height: 0; }
#canvas-hint { font-size: 10px; color: #666; margin-top: 6px; }

/* ── right panel ── */
#right h3    { font-size: 11px; color: #9cdcfe; margin: 10px 0 4px;
               text-transform: uppercase; letter-spacing: .5px; }
#right hr    { border: none; border-top: 1px solid #3c3c3c; margin: 8px 0; }
.row         { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
.row label   { flex: 1; display: flex; align-items: center;
               gap: 6px; cursor: pointer; }
input[type=checkbox], input[type=radio] { accent-color: #0e9ef7; cursor: pointer; }
input[type=number]  { width: 72px; background: #3c3c3c; border: 1px solid #555;
                      color: #d4d4d4; padding: 2px 5px; border-radius: 3px; }
input[type=text]    { width: 100%; background: #3c3c3c; border: 1px solid #555;
                      color: #d4d4d4; padding: 2px 5px; border-radius: 3px; }

/* ── port list ── */
#port-list    { margin: 4px 0; }
.port-row     { display: flex; align-items: center; gap: 6px;
                padding: 3px 5px; border-radius: 3px; cursor: pointer; }
.port-row:hover  { background: #3c3c3c; }
.port-row.active { background: #094771; }
.port-dot     { width: 11px; height: 11px; border-radius: 50%;
                border: 1.5px solid rgba(255,255,255,.35); flex-shrink: 0; }
.port-name    { flex: 1; font-size: 12px; }
.port-xy      { font-size: 10px; color: #888; }

/* ── buttons ── */
.btn          { padding: 4px 10px; background: #3c3c3c; border: 1px solid #555;
                color: #d4d4d4; border-radius: 3px; cursor: pointer; font-size: 12px; }
.btn:hover    { background: #4c4c4c; }
.btn:disabled { opacity: .4; cursor: default; }
.btn-save     { width: 100%; padding: 7px; margin-top: 4px;
                background: #0e5a8a; border-color: #0e9ef7; color: #fff; }
.btn-save:hover   { background: #1070a8; }
.btn-debug    { width: 100%; margin-top: 4px; }
.btn-danger   { background: #5c1a1a; border-color: #e04040; color: #f48771; }
.btn-danger:hover { background: #7c2020; }
.btn-match    { background: #3a3a1a; border-color: #cc9900; color: #ffcc00; }
.btn-match.armed { background: #5a5a10; }
#save-msg     { font-size: 11px; min-height: 16px; margin-top: 4px; }
.ok  { color: #4ec994; }
.err { color: #f48771; }

/* ── symbol info ── */
#sym-info     { font-size: 10px; color: #888; word-break: break-all;
                margin-bottom: 2px; line-height: 1.4; }
</style>
</head>
<body>

<!-- ── LEFT: symbol browser ──────────────────────────────────────────── -->
<div id="left">
  <div id="left-header">
    Symbols
    <input id="sym-search" type="search" placeholder="Filter…"
           oninput="filterSymbols()">
  </div>
  <div id="sym-list"></div>
</div>

<!-- ── CENTRE: canvas ────────────────────────────────────────────────── -->
<div id="center">
  <div id="status-bar">No symbol loaded — select one on the left.</div>
  <div id="canvas-wrap">
    <svg id="editor-svg" xmlns="http://www.w3.org/2000/svg"
         width="480" height="480" viewBox="0 0 80 80"
         style="display:block; cursor:crosshair;">
      <defs>
        <pattern id="grid-pat" patternUnits="userSpaceOnUse" width="10" height="10">
          <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#bbb" stroke-width="0.3"/>
        </pattern>
      </defs>
      <!-- grid background (toggled) -->
      <rect id="grid-bg" width="100%" height="100%"
            fill="url(#grid-pat)" display="none"/>
      <!-- symbol image (data-URI, no ID conflicts) -->
      <image id="sym-img" x="0" y="0" width="80" height="80"
             preserveAspectRatio="none"/>
      <!-- axis guide lines shown while dragging with a lock -->
      <line id="guide-h" stroke="#FF8800" stroke-width="0.4"
            stroke-dasharray="2,2" display="none" pointer-events="none"/>
      <line id="guide-v" stroke="#FF8800" stroke-width="0.4"
            stroke-dasharray="2,2" display="none" pointer-events="none"/>
      <!-- draggable port markers -->
      <g id="port-layer"></g>
    </svg>
  </div>
  <div id="canvas-hint">
    Drag ports • Double-click canvas to add • Right-click port to delete •
    Delete key removes selected
  </div>
</div>

<!-- ── RIGHT: controls ───────────────────────────────────────────────── -->
<div id="right">

  <h3>Symbol</h3>
  <div id="sym-info">—</div>

  <hr/>
  <h3>Grid</h3>
  <div class="row"><label><input type="checkbox" id="show-grid"
       onchange="toggleGrid()"> Show Grid</label></div>
  <div class="row"><label><input type="checkbox" id="snap-grid">
       Snap to Grid</label></div>
  <div class="row"><label>Grid size
    <input type="number" id="grid-size" value="10" min="1" max="200"
           onchange="updateGridPattern()">
  </label></div>

  <hr/>
  <h3>Axis Lock</h3>
  <div class="row"><label>
    <input type="radio" name="axis" value="FREE" checked> Free
  </label></div>
  <div class="row"><label>
    <input type="radio" name="axis" value="LOCK_X">
    Lock X &mdash; vertical drag only
  </label></div>
  <div class="row"><label>
    <input type="radio" name="axis" value="LOCK_Y">
    Lock Y &mdash; horizontal drag only
  </label></div>

  <hr/>
  <h3>Ports</h3>
  <div id="port-list"></div>
  <div style="display:flex; gap:4px; flex-wrap:wrap; margin-top:6px;">
    <button class="btn" onclick="addPortCenter()">+ Add</button>
    <button class="btn btn-match" id="btn-match" disabled
            onclick="toggleMatchY()">Match Y</button>
    <button class="btn btn-danger" id="btn-del" disabled
            onclick="deleteSelected()">Delete</button>
  </div>

  <!-- per-port field editor -->
  <div style="margin-top:8px; display:flex; flex-direction:column; gap:4px;">
    <div class="row" style="gap:4px;">
      <span style="width:20px; font-size:11px; color:#888;">ID</span>
      <input type="text" id="f-id" placeholder="process / signal / …"
             oninput="applyId()">
    </div>
    <div class="row">
      <span style="width:20px; font-size:11px; color:#888;">X</span>
      <input type="number" id="f-x" step="0.5" oninput="applyXY()">
    </div>
    <div class="row">
      <span style="width:20px; font-size:11px; color:#888;">Y</span>
      <input type="number" id="f-y" step="0.5" oninput="applyXY()">
    </div>
  </div>

  <hr/>
  <button class="btn btn-save" onclick="saveJSON()">&#x1F4BE; Save JSON</button>
  <div id="save-msg"></div>
  <button class="btn btn-debug" onclick="generateDebug()">
    &#x1F50D; Generate _debug.svg
  </button>

</div>

<script>
// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────
let allSymbols  = [];    // [{path, name, standard, category}]
let currentPath = null;  // relative path (no extension) from symbols root
let symbolMeta  = null;  // parsed JSON metadata
let ports       = [];    // [{id, x, y}]  — working copy
let selIdx      = null;  // selected port index | null
let drag        = null;  // {idx, origX, origY} while dragging
let matchArmed  = false; // true while "Match Y" awaiting click
let vw = 80, vh = 80;   // current symbol viewBox dimensions
let portR = 4;           // port circle radius (viewBox units, set on load)
let labelSz = 4.5;       // port label font size (viewBox units)

// ─────────────────────────────────────────────────────────────────────────────
// Port colour map
// ─────────────────────────────────────────────────────────────────────────────
const PORT_COLORS = {
  process: '#2288ff',
  signal:  '#22cc66',
  power:   '#ffaa00',
  drain:   '#cc6622',
  vent:    '#cc6622',
  control: '#cc44cc',
};
function portColor(id) {
  return PORT_COLORS[(id || '').toLowerCase()] || '#ee3333';
}

// ─────────────────────────────────────────────────────────────────────────────
// Grid helpers
// ─────────────────────────────────────────────────────────────────────────────
function gridSz() { return parseFloat(document.getElementById('grid-size').value) || 10; }

function snap(v) {
  if (!document.getElementById('snap-grid').checked) return v;
  const g = gridSz();
  return Math.round(v / g) * g;
}

function toggleGrid() {
  const on = document.getElementById('show-grid').checked;
  document.getElementById('grid-bg').setAttribute('display', on ? '' : 'none');
}

function updateGridPattern() {
  const g = gridSz();
  const pat = document.getElementById('grid-pat');
  pat.setAttribute('width',  g);
  pat.setAttribute('height', g);
  pat.innerHTML =
    `<path d="M ${g} 0 L 0 0 0 ${g}" fill="none" stroke="#bbb"` +
    ` stroke-width="${(g * 0.035).toFixed(2)}"/>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Symbol list
// ─────────────────────────────────────────────────────────────────────────────
async function loadSymbolList() {
  const res   = await fetch('/api/symbols');
  allSymbols  = await res.json();
  renderSymbolList(allSymbols);
}

function filterSymbols() {
  const q = document.getElementById('sym-search').value.toLowerCase();
  renderSymbolList(
    allSymbols.filter(s =>
      s.name.toLowerCase().includes(q) || s.path.toLowerCase().includes(q))
  );
}

function renderSymbolList(list) {
  const el = document.getElementById('sym-list');
  el.innerHTML = '';
  let lastGrp = null;
  for (const s of list) {
    const grp = s.standard + ' / ' + s.category;
    if (grp !== lastGrp) {
      const h = document.createElement('div');
      h.className = 'grp-head';
      h.textContent = grp;
      el.appendChild(h);
      lastGrp = grp;
    }
    const d = document.createElement('div');
    d.className = 'sym-item' + (s.path === currentPath ? ' active' : '');
    d.textContent = s.name;
    d.title = s.path;
    d.onclick = () => loadSymbol(s.path);
    el.appendChild(d);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Symbol loading
// ─────────────────────────────────────────────────────────────────────────────
async function loadSymbol(relPath) {
  if (drag) return; // don't interrupt a drag
  currentPath = relPath;
  selIdx      = null;
  matchArmed  = false;

  const res  = await fetch('/api/symbol?path=' + encodeURIComponent(relPath));
  if (!res.ok) { setStatus('Error loading ' + relPath); return; }
  const data = await res.json();

  symbolMeta = data.meta;
  ports      = JSON.parse(JSON.stringify(data.meta.snap_points || []));

  // Parse viewBox from SVG header
  const vbMatch = data.svg.match(/viewBox=["']([^"']+)["']/);
  if (vbMatch) {
    const parts = vbMatch[1].trim().split(/[\s,]+/);
    vw = parseFloat(parts[2]) || 80;
    vh = parseFloat(parts[3]) || 80;
  } else {
    vw = 80; vh = 80;
  }

  // Compute port radius proportional to symbol size
  portR   = Math.max(3, Math.min(vw, vh) * 0.04);
  labelSz = portR * 1.15;

  // Resize editor SVG (fit within 480×480, preserve aspect ratio)
  const MAX = 480;
  const scale = Math.min(MAX / vw, MAX / vh);
  const svg   = document.getElementById('editor-svg');
  svg.setAttribute('viewBox', `0 0 ${vw} ${vh}`);
  svg.setAttribute('width',  Math.round(vw * scale));
  svg.setAttribute('height', Math.round(vh * scale));

  // Update grid pattern to match new viewBox scale
  updateGridPattern();

  // Update guide line extents
  document.getElementById('guide-h').setAttribute('x1', 0);
  document.getElementById('guide-h').setAttribute('x2', vw);
  document.getElementById('guide-v').setAttribute('y1', 0);
  document.getElementById('guide-v').setAttribute('y2', vh);

  // Update grid background size
  document.getElementById('grid-bg').setAttribute('width',  vw);
  document.getElementById('grid-bg').setAttribute('height', vh);

  // Embed symbol SVG as data URI (avoids ID conflicts with clip-paths, etc.)
  const dataUri =
    'data:image/svg+xml,' + encodeURIComponent(data.svg);
  const img = document.getElementById('sym-img');
  img.setAttribute('href',   dataUri);
  img.setAttribute('width',  vw);
  img.setAttribute('height', vh);

  // Info panel
  document.getElementById('sym-info').textContent =
    (symbolMeta.display_name || symbolMeta.id || relPath) + '\n' + relPath;

  setStatus('Loaded: ' + relPath);
  renderPorts();
  renderPortList();
  clearFields();
  renderSymbolList(allSymbols); // refresh active highlight
}

// ─────────────────────────────────────────────────────────────────────────────
// Port rendering (SVG canvas)
// ─────────────────────────────────────────────────────────────────────────────
function renderPorts() {
  const ns    = 'http://www.w3.org/2000/svg';
  const layer = document.getElementById('port-layer');
  layer.innerHTML = '';

  ports.forEach((p, i) => {
    const col   = portColor(p.id);
    const isSel = (i === selIdx);

    // Selection halo
    if (isSel) {
      const halo = document.createElementNS(ns, 'circle');
      halo.setAttribute('cx', p.x);
      halo.setAttribute('cy', p.y);
      halo.setAttribute('r',  portR + portR * 0.6);
      halo.setAttribute('fill', 'none');
      halo.setAttribute('stroke', '#FFD700');
      halo.setAttribute('stroke-width', portR * 0.15);
      layer.appendChild(halo);
    }

    // Port circle
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('cx',            p.x);
    c.setAttribute('cy',            p.y);
    c.setAttribute('r',             portR);
    c.setAttribute('fill',          col);
    c.setAttribute('stroke',        'white');
    c.setAttribute('stroke-width',  portR * 0.15);
    c.style.cursor = 'grab';
    c.addEventListener('mousedown',    e => onPortDown(e, i));
    c.addEventListener('contextmenu',  e => { e.preventDefault(); ctxDelete(i); });
    // Tooltip
    const title = document.createElementNS(ns, 'title');
    title.textContent = `${p.id}  (${p.x.toFixed(2)}, ${p.y.toFixed(2)})`;
    c.appendChild(title);
    layer.appendChild(c);

    // Label
    const t = document.createElementNS(ns, 'text');
    t.setAttribute('x',           p.x + portR + labelSz * 0.2);
    t.setAttribute('y',           p.y + labelSz * 0.38);
    t.setAttribute('font-size',   labelSz);
    t.setAttribute('fill',        col);
    t.setAttribute('font-family', 'monospace');
    t.setAttribute('pointer-events', 'none');
    t.textContent = p.id;
    layer.appendChild(t);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Port list (right panel)
// ─────────────────────────────────────────────────────────────────────────────
function renderPortList() {
  const el = document.getElementById('port-list');
  el.innerHTML = '';
  ports.forEach((p, i) => {
    const row  = document.createElement('div');
    row.className = 'port-row' + (i === selIdx ? ' active' : '');
    row.innerHTML =
      `<span class="port-dot" style="background:${portColor(p.id)}"></span>` +
      `<span class="port-name">${p.id}</span>` +
      `<span class="port-xy">${p.x.toFixed(1)}, ${p.y.toFixed(1)}</span>`;
    row.onclick = () => {
      if (matchArmed && selIdx !== null && i !== selIdx) {
        // Apply match-Y: selected port inherits this port's Y
        ports[selIdx].y = p.y;
        cancelMatchY();
        renderPorts(); renderPortList(); populateFields(selIdx);
        return;
      }
      selectPort(i);
    };
    el.appendChild(row);
  });
  const hasSel = selIdx !== null;
  document.getElementById('btn-match').disabled = !hasSel;
  document.getElementById('btn-del').disabled   = !hasSel;
}

// ─────────────────────────────────────────────────────────────────────────────
// Selection helpers
// ─────────────────────────────────────────────────────────────────────────────
function selectPort(idx) {
  selIdx = idx;
  renderPorts();
  renderPortList();
  if (idx !== null) populateFields(idx); else clearFields();
}

function ctxDelete(idx) {
  selIdx = idx;
  deleteSelected();
}

// ─────────────────────────────────────────────────────────────────────────────
// Field sync
// ─────────────────────────────────────────────────────────────────────────────
function populateFields(idx) {
  const p = ports[idx];
  document.getElementById('f-id').value = p.id;
  document.getElementById('f-x').value  = p.x;
  document.getElementById('f-y').value  = p.y;
}

function clearFields() {
  ['f-id','f-x','f-y'].forEach(id => document.getElementById(id).value = '');
}

function applyId() {
  if (selIdx === null) return;
  const v = document.getElementById('f-id').value.trim();
  if (v) ports[selIdx].id = v;
  renderPorts(); renderPortList();
}

function applyXY() {
  if (selIdx === null) return;
  const x = parseFloat(document.getElementById('f-x').value);
  const y = parseFloat(document.getElementById('f-y').value);
  if (!isNaN(x)) ports[selIdx].x = +x.toFixed(2);
  if (!isNaN(y)) ports[selIdx].y = +y.toFixed(2);
  renderPorts(); renderPortList();
}

// ─────────────────────────────────────────────────────────────────────────────
// SVG coordinate helper
// ─────────────────────────────────────────────────────────────────────────────
function svgPt(e) {
  const svg = document.getElementById('editor-svg');
  const pt  = svg.createSVGPoint();
  pt.x = e.clientX; pt.y = e.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

// ─────────────────────────────────────────────────────────────────────────────
// Drag
// ─────────────────────────────────────────────────────────────────────────────
function onPortDown(e, idx) {
  if (matchArmed) return;
  e.preventDefault();
  e.stopPropagation();
  selectPort(idx);
  drag = { idx, origX: ports[idx].x, origY: ports[idx].y };
}

document.addEventListener('mousemove', e => {
  if (!drag) return;
  const pt   = svgPt(e);
  const lock = document.querySelector('input[name=axis]:checked').value;

  // Apply axis constraint BEFORE snap so snap works on the constrained axis
  let nx = (lock === 'LOCK_X') ? drag.origX : snap(pt.x);
  let ny = (lock === 'LOCK_Y') ? drag.origY : snap(pt.y);

  nx = +nx.toFixed(2);
  ny = +ny.toFixed(2);

  ports[drag.idx].x = nx;
  ports[drag.idx].y = ny;

  renderPorts();
  renderPortList();
  populateFields(drag.idx);
  updateGuides(nx, ny, lock);
  setStatus(`"${ports[drag.idx].id}"  x=${nx}  y=${ny}`);
});

document.addEventListener('mouseup', () => {
  if (!drag) return;
  drag = null;
  hideGuides();
});

// ─────────────────────────────────────────────────────────────────────────────
// Axis guide lines
// ─────────────────────────────────────────────────────────────────────────────
function updateGuides(nx, ny, lock) {
  const gh = document.getElementById('guide-h');
  const gv = document.getElementById('guide-v');
  if (lock === 'LOCK_Y') {
    // Y is fixed → port moves left/right → show horizontal guide at locked Y
    gh.setAttribute('x1', 0);  gh.setAttribute('x2', vw);
    gh.setAttribute('y1', ny); gh.setAttribute('y2', ny);
    gh.removeAttribute('display');
    gv.setAttribute('display', 'none');
  } else if (lock === 'LOCK_X') {
    // X is fixed → port moves up/down → show vertical guide at locked X
    gv.setAttribute('x1', nx); gv.setAttribute('x2', nx);
    gv.setAttribute('y1', 0);  gv.setAttribute('y2', vh);
    gv.removeAttribute('display');
    gh.setAttribute('display', 'none');
  } else {
    hideGuides();
  }
}

function hideGuides() {
  document.getElementById('guide-h').setAttribute('display', 'none');
  document.getElementById('guide-v').setAttribute('display', 'none');
}

// ─────────────────────────────────────────────────────────────────────────────
// Add / Delete / Match Y
// ─────────────────────────────────────────────────────────────────────────────

// Double-click on canvas → add port at that position
document.getElementById('editor-svg').addEventListener('dblclick', e => {
  if (!currentPath) return;
  if (e.target.tagName.toLowerCase() === 'circle') return; // ignore existing ports
  const pt = svgPt(e);
  const x  = +snap(pt.x).toFixed(2);
  const y  = +snap(pt.y).toFixed(2);
  ports.push({ id: 'process', x, y });
  selIdx = ports.length - 1;
  renderPorts(); renderPortList(); populateFields(selIdx);
  setStatus(`Added port at (${x}, ${y})`);
});

function addPortCenter() {
  if (!currentPath) return;
  ports.push({ id: 'process', x: +(vw / 2).toFixed(2), y: +(vh / 2).toFixed(2) });
  selIdx = ports.length - 1;
  renderPorts(); renderPortList(); populateFields(selIdx);
}

function deleteSelected() {
  if (selIdx === null) return;
  ports.splice(selIdx, 1);
  selIdx = ports.length ? Math.min(selIdx, ports.length - 1) : null;
  renderPorts(); renderPortList();
  if (selIdx !== null) populateFields(selIdx); else clearFields();
}

function toggleMatchY() {
  if (selIdx === null) return;
  matchArmed = !matchArmed;
  document.getElementById('btn-match').classList.toggle('armed', matchArmed);
  setStatus(matchArmed
    ? 'Click another port to copy its Y coordinate to the selected port…'
    : 'Match Y cancelled.');
}

function cancelMatchY() {
  matchArmed = false;
  document.getElementById('btn-match').classList.remove('armed');
}

// ─────────────────────────────────────────────────────────────────────────────
// Keyboard shortcuts
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (matchArmed) cancelMatchY();
  }
  if (e.key === 'Delete' && selIdx !== null && !matchArmed) {
    // Don't intercept Delete while typing in an input
    if (document.activeElement.tagName.toLowerCase() === 'input') return;
    deleteSelected();
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Save JSON
// ─────────────────────────────────────────────────────────────────────────────
async function saveJSON() {
  if (!currentPath || !symbolMeta) return;
  symbolMeta.snap_points = ports.map(p => ({
    id: p.id,
    x:  +p.x.toFixed(2),
    y:  +p.y.toFixed(2),
  }));
  const res = await fetch('/api/save', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ path: currentPath, meta: symbolMeta }),
  });
  showMsg(res.ok ? { ok: '✓ Saved' } : { err: '✗ ' + await res.text() });
}

// ─────────────────────────────────────────────────────────────────────────────
// Generate _debug.svg
// ─────────────────────────────────────────────────────────────────────────────
async function generateDebug() {
  if (!currentPath) return;
  const res = await fetch('/api/debug', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      path:  currentPath,
      ports: ports.map(p => ({
        id: p.id, x: +p.x.toFixed(2), y: +p.y.toFixed(2),
      })),
    }),
  });
  showMsg(res.ok
    ? { ok: '✓ _debug.svg written' }
    : { err: '✗ ' + await res.text() });
}

// ─────────────────────────────────────────────────────────────────────────────
// UI helpers
// ─────────────────────────────────────────────────────────────────────────────
function setStatus(msg) {
  document.getElementById('status-bar').textContent = msg;
}

function showMsg(obj) {
  const el = document.getElementById('save-msg');
  if (obj.ok)  { el.className = 'ok';  el.textContent = obj.ok;  }
  if (obj.err) { el.className = 'err'; el.textContent = obj.err; }
  setTimeout(() => { el.textContent = ''; }, 3500);
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────────────────
loadSymbolList();
</script>
</body>
</html>
"""


# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, *_):
        pass  # silence request logging

    # ── helpers ───────────────────────────────────────────────────────────────

    def _send(self, body: str | bytes,
              ctype: str = "text/html; charset=utf-8",
              status: int = 200) -> None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, status: int = 200) -> None:
        self._send(json.dumps(obj, ensure_ascii=False),
                   "application/json; charset=utf-8", status)

    def _error(self, msg: str, status: int = 400) -> None:
        self._send(msg, "text/plain; charset=utf-8", status)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length))

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        qs     = urllib.parse.parse_qs(parsed.query)
        p      = parsed.path

        if p in ("/", "/index.html"):
            self._send(HTML)

        elif p == "/api/symbols":
            self._json(_list_symbols())

        elif p == "/api/symbol":
            rel = qs.get("path", [None])[0]
            if not rel:
                self._error("missing ?path="); return
            result = _load_symbol(rel)
            if result is None:
                self._error(f"Symbol not found: {rel}", 404); return
            self._json(result)

        else:
            self._error("Not found", 404)

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self) -> None:
        body = self._read_body()
        p    = urllib.parse.urlparse(self.path).path

        if p == "/api/save":
            ok, msg = _save_symbol(body.get("path"), body.get("meta"))
            if ok: self._send("ok")
            else:  self._error(msg, 500)

        elif p == "/api/debug":
            ok, msg = _generate_debug(body.get("path"), body.get("ports", []))
            if ok: self._send("ok")
            else:  self._error(msg, 500)

        else:
            self._error("Not found", 404)


# ── business logic ────────────────────────────────────────────────────────────

def _safe_path(rel: str) -> pathlib.Path | None:
    """Resolve a relative symbol path safely (prevent path traversal)."""
    rel_clean = rel.replace("/", os.sep).replace("\\", os.sep)
    try:
        abs_path = (SYMBOLS_ROOT / rel_clean).resolve()
        abs_path.relative_to(SYMBOLS_ROOT.resolve())
    except (ValueError, OSError):
        return None
    return abs_path


def _list_symbols() -> list[dict]:
    """Return all symbol JSON files as a sorted list of descriptor dicts."""
    results = []
    for json_path in sorted(SYMBOLS_ROOT.rglob("*.json")):
        if "_debug" in json_path.stem:
            continue
        rel   = json_path.relative_to(SYMBOLS_ROOT)
        parts = rel.parts
        results.append({
            "path":     "/".join(rel.with_suffix("").parts),
            "name":     json_path.stem,
            "standard": parts[0] if len(parts) >= 1 else "",
            "category": parts[1] if len(parts) >= 2 else "",
        })
    return results


def _load_symbol(rel: str) -> dict | None:
    """Load and return {meta, svg} for a symbol, or None if not found."""
    base = _safe_path(rel)
    if base is None:
        return None
    json_path = base.with_suffix(".json")
    svg_path  = base.with_suffix(".svg")
    if not json_path.exists() or not svg_path.exists():
        return None
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    svg  = svg_path.read_text(encoding="utf-8")
    return {"meta": meta, "svg": svg}


def _save_symbol(rel: str | None, meta: dict | None) -> tuple[bool, str]:
    """Write updated metadata JSON back to disk."""
    if not rel or meta is None:
        return False, "missing path or meta"
    base = _safe_path(rel)
    if base is None:
        return False, "invalid path"
    json_path = base.with_suffix(".json")
    if not json_path.exists():
        return False, f"JSON not found: {json_path}"
    try:
        json_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return False, str(exc)
    return True, ""


def _generate_debug(rel: str | None, ports: list[dict]) -> tuple[bool, str]:
    """Overlay labelled port markers on the symbol SVG and save as *_debug.svg."""
    if not rel:
        return False, "missing path"
    base = _safe_path(rel)
    if base is None:
        return False, "invalid path"
    svg_path   = base.with_suffix(".svg")
    debug_path = base.parent / (base.stem + "_debug.svg")
    if not svg_path.exists():
        return False, f"SVG not found: {svg_path}"

    original = svg_path.read_text(encoding="utf-8")

    # Detect viewBox to size port radius proportionally
    import re as _re
    m = _re.search(r'viewBox=["\']\s*[\d.+-]+\s+[\d.+-]+\s+([\d.]+)\s+([\d.]+)',
                   original)
    vw, vh = (float(m.group(1)), float(m.group(2))) if m else (80.0, 80.0)
    r    = max(3.0, min(vw, vh) * 0.04)
    fsz  = round(r * 1.15, 2)

    _PORT_COLORS = {
        "process": "#2288ff", "signal": "#22cc66", "power": "#ffaa00",
        "drain":   "#cc6622", "vent":   "#cc6622", "control": "#cc44cc",
    }

    def _col(pid: str) -> str:
        return _PORT_COLORS.get(pid.lower(), "#ee3333")

    parts = []
    for p in ports:
        pid  = p.get("id", "?")
        x, y = p.get("x", 0), p.get("y", 0)
        col  = _col(pid)
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" '
            f'stroke="white" stroke-width="{r*0.15:.2f}" opacity="0.9"/>'
        )
        parts.append(
            f'<text x="{x + r + fsz*0.2}" y="{y + fsz*0.4}" '
            f'font-size="{fsz}" fill="{col}" font-family="monospace"'
            f'>{pid}</text>'
        )

    overlay   = "\n".join(parts)
    debug_svg = original.replace("</svg>", f"<!-- port debug -->\n{overlay}\n</svg>")
    try:
        debug_path.write_text(debug_svg, encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, ""


# ── entry point ───────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    global SYMBOLS_ROOT, SERVER_PORT

    parser = argparse.ArgumentParser(
        description="Browser-based snap-point editor for P&ID SVG symbols."
    )
    parser.add_argument(
        "--symbols",
        default=str(pathlib.Path(__file__).parent / "symbols"),
        help="Path to the symbols root directory (default: ./symbols).",
    )
    parser.add_argument(
        "--port", type=int, default=7421,
        help="Local HTTP port (default: 7421).",
    )
    args = parser.parse_args(argv)

    SYMBOLS_ROOT = pathlib.Path(args.symbols).resolve()
    SERVER_PORT  = args.port

    if not SYMBOLS_ROOT.is_dir():
        print(f"Error: symbols directory not found: {SYMBOLS_ROOT}")
        return

    url    = f"http://127.0.0.1:{SERVER_PORT}"
    server = http.server.HTTPServer(("127.0.0.1", SERVER_PORT), Handler)

    print(f"Port Editor  →  {url}")
    print(f"Symbols root →  {SYMBOLS_ROOT}")
    print("Press Ctrl+C to stop.")

    # Open browser slightly after server starts
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
