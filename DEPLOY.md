# ORBIT-HAR Deployment Guide — Cloud (Vercel & Render) & Offline

This guide provides end-to-end instructions for deploying the ORBIT-HAR platform to the cloud (**Vercel** for the frontend and **Render** for the backend), while maintaining 100% compatibility with your **offline Windows deployment** for physical demonstrations.

---

## 🏗️ Deployment Architecture

| Component | Target Platform | Directory | Notes |
|---|---|---|---|
| **Frontend** | [Vercel](https://vercel.com) | `orbit-har-dashboard/` | React 19 + Vite. Reads API endpoints from `VITE_*` environment variables. |
| **Backend** | [Render](https://render.com) | `backend/` | FastAPI + WebSockets. Managed via `render.yaml` with dynamic `$PORT`. |
| **Offline System** | Windows Laptop | Root (`./`) | Self-contained, works with zero internet connection via `start.bat`. |

---

## ⚡ Cloud vs. Offline Feature Matrix

| Feature | Local Windows (Offline) | Cloud (Render + Vercel) | Reason |
|---|---|---|---|
| Dashboard UI & Navigation | ✅ Full | ✅ Full | Pure web client |
| Experiment Logs & History | ✅ Full | ✅ Full | API endpoints `/logs` |
| Text Files / Telemetry Viewer | ✅ Full | ✅ Full | API endpoints `/text-files` |
| Recorded Videos Viewer | ✅ Full | ✅ Full | API endpoints `/videos` |
| WebSocket Event Broadcaster | ✅ Full | ✅ Full | Supported via `wss://` |
| Live Webcam Feed (`/video`) | ✅ Full | ⚠️ Disabled | Cloud server cannot access laptop webcam |
| Real-Time AI Detection (YOLO/MediaPipe) | ✅ Full | ⚠️ Disabled | Local hardware required for physical interaction |
| 3D Human Mesh (`:8010`) | ✅ Full | ⚠️ Disabled | Requires local MediaPipe Pose & display hardware |
| Subprocess Experiment Launch | ✅ Full | ⚠️ Disabled | Requires local camera hardware |

---

## 🚀 Step 1: Push Code to GitHub

From your local machine terminal:

```bash
git add .
git commit -m "feat: configure cloud deployment for Vercel and Render with offline fallback"
git push origin main
```
*Repository URL*: `https://github.com/Ozair-aly/orbit-har`

---

## 🖥️ Step 2: Deploy Backend to Render

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Select **Build and deploy from a Git repository** and connect `https://github.com/Ozair-aly/orbit-har`.
4. Configure the service settings:
   - **Name**: `orbit-har-backend`
   - **Language / Runtime**: `Python`
   - **Region**: Choose closest to you (e.g., `Singapore` or `Frankfurt`)
   - **Branch**: `main`
   - **Root Directory**: *(leave blank)*
   - **Build Command**: `pip install -r requirements-cloud.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. Under **Environment Variables**, add:
   | Key | Value | Description |
   |---|---|---|
   | `CLOUD_MODE` | `true` | Enables cloud-safe mode for hardware endpoints |
   | `PYTHONIOENCODING` | `utf-8` | Prevents encoding issues in logs |
6. Click **Create Web Service**.
7. Wait for the build and deployment to complete. Copy your Render service URL:
   - Example: `https://orbit-har-backend.onrender.com`

> **Note on Free Tier**: Render free instances spin down after 15 minutes of inactivity. The first request after idling may take 30–60 seconds to wake up.

---

## 🌐 Step 3: Deploy Frontend to Vercel

1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository (`Ozair-aly/orbit-har`).
4. Configure the project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `orbit-har-dashboard`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
5. Expand **Environment Variables** and add:
   | Key | Value (Example) | Notes |
   |---|---|---|
   | `VITE_BACKEND_URL` | `https://orbit-har-backend.onrender.com` | Your Render backend HTTPS URL (no trailing slash) |
   | `VITE_WS_URL` | `wss://orbit-har-backend.onrender.com/ws` | Your Render WebSocket WSS URL |
   | `VITE_HUMAN_MESH_URL` | *(leave empty or omitted)* | Disabled in cloud |
6. Click **Deploy**.
7. Once deployed, open your public Vercel URL (e.g., `https://orbit-har.vercel.app`).

---

## 🔍 Step 4: Verification & Testing

### 1. Test Backend API
Run in a browser or terminal:
```bash
# Health check / status
curl https://<your-render-url>/camera/status

# Logs endpoint
curl https://<your-render-url>/logs
```

### 2. Test Frontend
1. Open your Vercel URL in your browser.
2. Check the header status badge — it should show connection status.
3. Open **Logs**, **Videos**, and **Text Files** pages to confirm API data loads.
4. Try clicking **Start Experiment** or **3D Human Mesh** — it will display a clear notification explaining that physical camera features require local/offline mode.

---

## 💻 Local / Offline Windows Deployment (Unchanged)

Your offline demonstration setup remains 100% operational and untouched:

```bat
:: 1. Initial Setup (One-Time)
setup.bat

:: 2. Launch Local System (FastAPI on :8000, Vite preview on :5173, Camera AI)
start.bat

:: 3. Stop System
stop.bat
```

No environment variables are needed locally; the dashboard automatically defaults to `http://127.0.0.1:8000` when `VITE_*` variables are unset.
