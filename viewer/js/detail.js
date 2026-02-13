/**
 * Detail view – full-res image + interactive bounding boxes on Canvas.
 */
import { CLASS_NAMES, CLASS_COLORS } from "./classes.js";
import { parseYOLO } from "./annotations.js";

let canvas, ctx;
let currentItem = null;
let currentList = [];
let currentIdx  = -1;
let boxes = [];
let imgObj = null;

let showBoxes  = true;
let showLabels = true;
let hoveredBox = null;

let onBack = null;

export function initDetail(backCallback) {
  onBack = backCallback;
  canvas = document.getElementById("pid-canvas");
  ctx = canvas.getContext("2d");

  canvas.addEventListener("mousemove", handleMouse);
  canvas.addEventListener("mouseleave", () => {
    hoveredBox = null;
    document.getElementById("tooltip").style.display = "none";
    draw();
  });

  document.getElementById("btn-back").addEventListener("click", back);
  document.getElementById("btn-boxes").addEventListener("click", toggleBoxes);
  document.getElementById("btn-labels").addEventListener("click", toggleLabels);
}

export function show(item, list, idx) {
  currentItem = item;
  currentList = list;
  currentIdx  = idx;
  boxes = [];
  hoveredBox = null;

  document.getElementById("detail").style.display = "block";
  document.getElementById("detail-title").textContent =
    `${item.id}  [${item.split}]`;

  loadImage(item);
}

export function hide() {
  document.getElementById("detail").style.display = "none";
  currentItem = null;
}

export function navigate(dir) {
  if (!currentList.length) return;
  currentIdx = (currentIdx + dir + currentList.length) % currentList.length;
  show(currentList[currentIdx], currentList, currentIdx);
}

/* ── Internal ──────────────────────────────────────────────── */

function back() {
  hide();
  if (onBack) onBack();
}

function toggleBoxes() {
  showBoxes = !showBoxes;
  document.getElementById("btn-boxes").classList.toggle("active", showBoxes);
  draw();
}

function toggleLabels() {
  showLabels = !showLabels;
  document.getElementById("btn-labels").classList.toggle("active", showLabels);
  draw();
}

async function loadImage(item) {
  imgObj = new Image();
  imgObj.onload = async () => {
    canvas.width  = imgObj.naturalWidth;
    canvas.height = imgObj.naturalHeight;
    if (item.label) {
      try {
        const resp = await fetch("../" + item.label);
        const text = await resp.text();
        boxes = parseYOLO(text, imgObj.naturalWidth, imgObj.naturalHeight);
      } catch { boxes = []; }
    } else {
      boxes = [];
    }
    draw();
    renderSidebar();
  };
  imgObj.src = "../" + item.image;
}

function draw() {
  if (!imgObj) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(imgObj, 0, 0);

  if (!showBoxes) return;

  for (const box of boxes) {
    const color = CLASS_COLORS[box.classId] || "#fff";
    const isHover = box === hoveredBox;

    ctx.strokeStyle = color;
    ctx.lineWidth = isHover ? 3 : 2;
    ctx.strokeRect(box.x, box.y, box.w, box.h);

    if (isHover) {
      ctx.fillStyle = color + "33"; // 20% opacity
      ctx.fillRect(box.x, box.y, box.w, box.h);
    }

    if (showLabels || isHover) {
      const label = CLASS_NAMES[box.classId] || `Class ${box.classId}`;
      ctx.font = `${isHover ? "bold " : ""}13px sans-serif`;
      const tw = ctx.measureText(label).width;
      const lx = box.x;
      const ly = box.y - 4;
      ctx.fillStyle = "rgba(0,0,0,0.7)";
      ctx.fillRect(lx - 1, ly - 13, tw + 6, 16);
      ctx.fillStyle = color;
      ctx.fillText(label, lx + 2, ly);
    }
  }
}

function handleMouse(e) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width  / rect.width;
  const scaleY = canvas.height / rect.height;
  const mx = (e.clientX - rect.left) * scaleX;
  const my = (e.clientY - rect.top)  * scaleY;

  let found = null;
  for (const box of boxes) {
    if (mx >= box.x && mx <= box.x + box.w &&
        my >= box.y && my <= box.y + box.h) {
      found = box;
    }
  }

  if (found !== hoveredBox) {
    hoveredBox = found;
    draw();
  }

  const tooltip = document.getElementById("tooltip");
  if (found) {
    tooltip.textContent = CLASS_NAMES[found.classId] || `Class ${found.classId}`;
    tooltip.style.display = "block";
    tooltip.style.left = (e.clientX - canvas.parentElement.getBoundingClientRect().left + 12) + "px";
    tooltip.style.top  = (e.clientY - canvas.parentElement.getBoundingClientRect().top  + 12) + "px";
  } else {
    tooltip.style.display = "none";
  }
}

function renderSidebar() {
  const sidebar = document.getElementById("sidebar");
  const counts = {};
  for (const box of boxes) {
    counts[box.classId] = (counts[box.classId] || 0) + 1;
  }
  const sorted = Object.entries(counts)
    .map(([id, n]) => ({ id: +id, n }))
    .sort((a, b) => b.n - a.n);

  sidebar.innerHTML = `
    <h3>Annotations (${boxes.length})</h3>
    ${sorted.map(({ id, n }) => `
      <div class="class-row">
        <span class="class-swatch" style="background:${CLASS_COLORS[id] || '#fff'}"></span>
        <span class="class-name">${CLASS_NAMES[id] || "Class " + id}</span>
        <span class="class-count">${n}</span>
      </div>
    `).join("")}
  `;
}
