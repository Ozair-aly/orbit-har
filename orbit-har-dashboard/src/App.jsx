import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./App.css";

import Experiments from "./pages/Experiments";
import Sidebar from "./components/Sidebar";
import Monitoring from "./pages/Monitoring";
import Logs from "./pages/Logs";
import Videos from "./pages/Videos";
import TextFiles from "./pages/TextFiles";
import HumanMesh from "./pages/HumanMesh";

import { useOrbitSocket } from "./hooks/useOrbitSocket";

function App() {

  // =========================================================
  // THEME
  // =========================================================

  const [theme, setTheme] = useState(() => {

    const savedTheme =
      localStorage.getItem("orbit-theme");

    return savedTheme || "dark";
  });


  // =========================================================
  // SAVE THEME
  // =========================================================

  useEffect(() => {

    localStorage.setItem(
      "orbit-theme",
      theme
    );

  }, [theme]);


  // =========================================================
  // ORBIT SOCKET
  // =========================================================

  const {
    data,
    completedSteps,
    logs,
    connected,
    aiStatus,
    cameraOnline
  } = useOrbitSocket();


  // =========================================================
  // TOGGLE THEME
  // =========================================================

  const toggleTheme = () => {

    setTheme((currentTheme) =>
      currentTheme === "dark"
        ? "light"
        : "dark"
    );

  };


  // =========================================================
  // UI
  // =========================================================

  return (

    <BrowserRouter>

      <div
        className={
          theme === "light"
            ? "app-shell light-mode"
            : "app-shell"
        }
      >

        {/* SIDEBAR */}

        <Sidebar />


        <div className="main-content">

          {/* =============================================
              HEADER
          ============================================= */}

          <header className="header">

            {/* =========================================
                ISRO + ORBIT-HAR BRANDING
            ========================================= */}

            <div className="header-brand">

              

              <div>

                <h1>
                  <b>ORBIT-HAR</b>
                </h1>

                <p>
                  (Onboard Real-time Behavioural &
                  Interactional Tracking for Human
                  Activity Recognition)
                </p>

              </div>

            </div>


            {/* =========================================
                HEADER CONTROLS
            ========================================= */}

            <div className="header-controls">

              <div
                className={
                  connected
                    ? "online"
                    : "offline"
                }
              >

                ●{" "}
                {connected
                  ? "EDGE SYSTEM ONLINE"
                  : "BACKEND OFFLINE"}

              </div>


              {/* THEME BUTTON */}

              <button
                className="theme-toggle"
                onClick={toggleTheme}
                type="button"
              >

                {theme === "dark"
                  ? "☀️ LIGHT"
                  : "🌙 DARK"}

              </button>

            </div>

          </header>


          {/* =============================================
              ROUTED PAGE
          ============================================= */}

          <Routes>

            <Route
              path="/"
              element={
                <Monitoring
                  data={data}
                  completedSteps={completedSteps}
                  aiStatus={aiStatus}
                  cameraOnline={cameraOnline}
                  logs={logs}
                />
              }
            />

            <Route
              path="/experiments"
              element={
                <Experiments />
              }
            />

            <Route
              path="/logs"
              element={
                <Logs />
              }
            />

            <Route
              path="/videos"
              element={
                <Videos />
              }
            />
            <Route
              path="/text-files"
              element={
                <TextFiles />
              }
            />
            <Route
              path="/human-mesh"
              element={<HumanMesh />}
            />

          </Routes>


          {/* =============================================
              FOOTER
          ============================================= */}

          <footer>

            <span>
              🔊 VOICE ASSISTANT: READY
            </span>

            <span>
              💾 LOCAL EDGE PROCESSING
            </span>

            <span>
              {connected
                ? "🟢 SYSTEM OPERATIONAL"
                : "🔴 CONNECTION LOST"}
            </span>

          </footer>

        </div>

      </div>

    </BrowserRouter>

  );
}

export default App;