// ============================================================
// ORBIT-HAR — Centralized URL Configuration
// ============================================================
//
// Cloud deployment (Vercel):
//   Set VITE_BACKEND_URL, VITE_WS_URL, VITE_HUMAN_MESH_URL
//   in the Vercel dashboard under Environment Variables.
//
// Local / Offline (SIH demo):
//   No env vars needed — defaults to 127.0.0.1 automatically.
// ============================================================

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

const WS_URL =
  import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/ws";

const HUMAN_MESH_URL =
  import.meta.env.VITE_HUMAN_MESH_URL || "http://127.0.0.1:8010";

export { BACKEND_URL, WS_URL, HUMAN_MESH_URL };
