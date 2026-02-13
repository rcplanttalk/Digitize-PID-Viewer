# Digitize-PID Viewer

Interactive web viewer for the **Digitize-PID** dataset — 500 synthetic Piping & Instrumentation Diagrams (P&IDs) with YOLO bounding-box annotations for 32 symbol classes.

## Quick start

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install huggingface_hub

# 2. Download the dataset (~1.29 GB)
python3 scripts/download_dataset.py

# 3. Generate the image/label manifest
python3 scripts/generate_manifest.py

# 4. Start the local server
python3 server.py          # default port 8080

# 5. Open in browser
#    http://localhost:8080/viewer/
```

## Features

- **Gallery** — responsive grid of lazy-loaded thumbnails
- **Split filter** — toggle All / Train / Val
- **Search** — filter images by ID
- **Detail view** — full-resolution P&ID with interactive bounding boxes
- **Hover tooltips** — symbol class name on mouse-over
- **Toggle controls** — show/hide boxes and labels
- **Keyboard navigation** — `←` / `→` to browse, `Esc` to go back
- **Sidebar** — annotation summary per class for the current image

## Dataset

| | |
|---|---|
| **Name** | Digitize-PID YOLO |
| **Source** | [hamzas/digitize-pid-yolo](https://huggingface.co/datasets/hamzas/digitize-pid-yolo) on Hugging Face |
| **Size** | ~1.29 GB |
| **Images** | 400 train + 100 validation (JPEG) |
| **Annotations** | 32 YOLO classes — format: `classId x_center y_center width height` (normalized 0-1) |
| **Paper** | [arXiv:2109.03794](https://arxiv.org/abs/2109.03794) — *Digitize-PID: Automatic Digitization of Piping and Instrumentation Diagrams* |

Download with:

```bash
python3 scripts/download_dataset.py
```

## Project structure

```
├── docs/                   Reference papers
├── data/                   Dataset (git-ignored, ~1.29 GB)
│   └── DigitizePID_Dataset/
│       ├── images/{train,val}/
│       └── labels/{train,val}/
├── viewer/                 Web app (pure HTML/CSS/JS)
│   ├── index.html
│   ├── css/styles.css
│   └── js/
├── scripts/
│   ├── download_dataset.py
│   └── generate_manifest.py
├── manifest.json           Auto-generated
├── server.py               Dev server with CORS
└── .gitignore
```

## References

- Paliwal, S., Jain, A., Sharma, M., & Vig, L. (2021). *Digitize-PID: Automatic Digitization of Piping and Instrumentation Diagrams*. [arXiv:2109.03794](https://arxiv.org/abs/2109.03794)
- Dataset: [hamzas/digitize-pid-yolo](https://huggingface.co/datasets/hamzas/digitize-pid-yolo) on Hugging Face
