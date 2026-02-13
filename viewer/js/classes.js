/**
 * 32 P&ID symbol classes from the Digitize-PID dataset.
 * Index 0–31 corresponds to YOLO class IDs (paper symbols 1–32).
 * Symbols 0–24 (paper 1–25) are "complex" shapes detected via
 * the Complex Shape Extraction module; 25–31 (paper 26–32) are
 * "basic" shapes detected via the Basic Shape Extraction module.
 */

export const CLASS_NAMES = [
  /* 0  */ "Gate Valve",
  /* 1  */ "Globe Valve",
  /* 2  */ "Ball Valve",
  /* 3  */ "Butterfly Valve",
  /* 4  */ "Check Valve",
  /* 5  */ "Plug Valve",
  /* 6  */ "Relief Valve",
  /* 7  */ "Needle Valve",
  /* 8  */ "Diaphragm Valve",
  /* 9  */ "Angle Valve",
  /* 10 */ "Three-Way Valve",
  /* 11 */ "Control Valve",
  /* 12 */ "Solenoid Valve",
  /* 13 */ "Motor-Op. Valve",
  /* 14 */ "Pneumatic Valve",
  /* 15 */ "Hand Valve",
  /* 16 */ "Pressure Indicator",
  /* 17 */ "Temperature Indicator",
  /* 18 */ "Flow Indicator",
  /* 19 */ "Level Indicator",
  /* 20 */ "Instrument (Generic)",
  /* 21 */ "Transmitter",
  /* 22 */ "Controller",
  /* 23 */ "Centrifugal Pump",
  /* 24 */ "Compressor",
  /* 25 */ "Tank",
  /* 26 */ "Heat Exchanger",
  /* 27 */ "Vessel",
  /* 28 */ "Reducer",
  /* 29 */ "Flange",
  /* 30 */ "End Connector",
  /* 31 */ "Arrow",
];

/** Distinct, high-contrast colours for each class. */
export const CLASS_COLORS = [
  "#e6194b", "#3cb44b", "#ffe119", "#4363d8",
  "#f58231", "#911eb4", "#42d4f4", "#f032e6",
  "#bfef45", "#fabed4", "#469990", "#dcbeff",
  "#9A6324", "#fffac8", "#800000", "#aaffc3",
  "#808000", "#ffd8b1", "#000075", "#a9a9a9",
  "#e6beff", "#1abc9c", "#e74c3c", "#3498db",
  "#2ecc71", "#9b59b6", "#f1c40f", "#e67e22",
  "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
];
