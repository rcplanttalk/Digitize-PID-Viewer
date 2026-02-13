/**
 * Gallery view – renders thumbnail cards from the manifest.
 */

let allItems = [];
let currentFilter = "all";    // "all" | "train" | "val"
let searchQuery = "";
let onSelect = null;          // callback(item)

/** Initialise gallery. */
export function initGallery(manifest, selectCallback) {
  allItems = manifest.items;
  onSelect = selectCallback;
  render();
}

/** Set split filter. */
export function setFilter(filter) {
  currentFilter = filter;
  render();
}

/** Set search query. */
export function setSearch(q) {
  searchQuery = q.trim().toLowerCase();
  render();
}

/** Return currently visible (filtered) items. */
export function getVisibleItems() {
  return filtered();
}

function filtered() {
  let items = allItems;
  if (currentFilter !== "all") {
    items = items.filter(i => i.split === currentFilter);
  }
  if (searchQuery) {
    items = items.filter(i => i.id.toLowerCase().includes(searchQuery));
  }
  return items;
}

function render() {
  const container = document.getElementById("gallery");
  const items = filtered();

  if (items.length === 0) {
    container.innerHTML = '<div id="empty">No images match the current filter.</div>';
    return;
  }

  container.innerHTML = items.map((item, idx) => `
    <div class="thumb-card" data-idx="${idx}">
      <img src="../${item.image}" loading="lazy" alt="${item.id}">
      <div class="caption">
        <span>${item.id}</span>
        <span class="split-badge">${item.split}</span>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".thumb-card").forEach(card => {
    card.addEventListener("click", () => {
      const idx = parseInt(card.dataset.idx, 10);
      if (onSelect) onSelect(items[idx], items, idx);
    });
  });
}
