/**
 * Parse YOLO-format annotation text into pixel-space bounding boxes.
 *
 * YOLO format per line: classId x_center y_center width height
 * All values normalised to [0, 1].
 */

/**
 * @param {string} text   Raw contents of a .txt label file.
 * @param {number} imgW   Image width in pixels.
 * @param {number} imgH   Image height in pixels.
 * @returns {Array<{classId:number, x:number, y:number, w:number, h:number}>}
 */
export function parseYOLO(text, imgW, imgH) {
  const boxes = [];
  const lines = text.trim().split("\n");
  for (const line of lines) {
    const parts = line.trim().split(/\s+/);
    if (parts.length < 5) continue;
    const classId = parseInt(parts[0], 10);
    const cx = parseFloat(parts[1]);
    const cy = parseFloat(parts[2]);
    const bw = parseFloat(parts[3]);
    const bh = parseFloat(parts[4]);
    boxes.push({
      classId,
      x: (cx - bw / 2) * imgW,
      y: (cy - bh / 2) * imgH,
      w: bw * imgW,
      h: bh * imgH,
    });
  }
  return boxes;
}
