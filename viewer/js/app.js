/**
 * App entry-point – loads manifest, wires gallery & detail views.
 */
import { initGallery, setFilter, setSearch, getVisibleItems } from "./gallery.js";
import { initDetail, show as showDetail, hide as hideDetail, navigate } from "./detail.js";

async function boot() {
  const loading = document.getElementById("loading");

  // Load manifest
  let manifest;
  try {
    const resp = await fetch("../manifest.json");
    if (!resp.ok) throw new Error(resp.statusText);
    manifest = await resp.json();
  } catch (err) {
    loading.textContent = `Failed to load manifest.json – ${err.message}. Run generate_manifest.py first.`;
    return;
  }

  loading.style.display = "none";

  // Show counts
  const countParts = [`${manifest.train_count} train`, `${manifest.val_count} val`];
  if (manifest.generated_count) countParts.push(`${manifest.generated_count} generated`);
  document.getElementById("count-info").textContent =
    `${manifest.total} images (${countParts.join(" / ")})`;

  // Init views
  initGallery(manifest, (item, list, idx) => showDetail(item, list, idx));
  initDetail(() => {/* back to gallery – detail is simply hidden */});

  // Filter buttons
  document.querySelectorAll("[data-filter]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-filter]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      setFilter(btn.dataset.filter);
    });
  });

  // Search box
  document.getElementById("searchBox").addEventListener("input", e => {
    setSearch(e.target.value);
  });

  // Keyboard navigation
  document.addEventListener("keydown", e => {
    if (document.getElementById("detail").style.display === "block") {
      if (e.key === "Escape")      { hideDetail(); e.preventDefault(); }
      else if (e.key === "ArrowRight") { navigate(1);  e.preventDefault(); }
      else if (e.key === "ArrowLeft")  { navigate(-1); e.preventDefault(); }
    }
  });
}

boot();
