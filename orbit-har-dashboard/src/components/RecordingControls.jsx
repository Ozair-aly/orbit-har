import { useEffect, useRef, useState } from "react";
import { BACKEND_URL } from "../config.js";

const BASE_URL = BACKEND_URL;

function formatElapsed(totalSeconds) {
  const m = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const s = String(totalSeconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

function RecordingControls({ cameraOnline }) {

  // "idle" | "recording" | "paused"
  const [status, setStatus] = useState("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const intervalRef = useRef(null);

  useEffect(() => {
    if (status === "recording") {
      intervalRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(intervalRef.current);
    }

    return () => clearInterval(intervalRef.current);
  }, [status]);

  const callEndpoint = async (path) => {
    setBusy(true);
    setError(null);

    try {
      const response = await fetch(`${BASE_URL}${path}`, { method: "POST" });

      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }

      return true;
    } catch (err) {
      console.error("Recording control error:", err);
      setError("Recording backend unavailable");
      return false;
    } finally {
      setBusy(false);
    }
  };

  const handleStart = async () => {
    const ok = await callEndpoint("/recording/start");
    if (ok) {
      setElapsed(0);
      setStatus("recording");
    }
  };

  const handlePauseResume = async () => {
    if (status === "recording") {
      const ok = await callEndpoint("/recording/pause");
      if (ok) setStatus("paused");
    } else if (status === "paused") {
      const ok = await callEndpoint("/recording/resume");
      if (ok) setStatus("recording");
    }
  };

  const handleStop = async () => {
    const ok = await callEndpoint("/recording/stop");
    if (ok) {
      setStatus("idle");
      setElapsed(0);
    }
  };

  const isIdle = status === "idle";
  const isRecording = status === "recording";
  const isPaused = status === "paused";

  return (
    <div className="recording-bar">

      <button
        className="rec-btn start"
        onClick={handleStart}
        disabled={busy || !isIdle || !cameraOnline}
        title={!cameraOnline ? "Camera is offline" : "Start recording"}
      >
        ⏺ Start
      </button>

      <button
        className="rec-btn pause"
        onClick={handlePauseResume}
        disabled={busy || isIdle}
      >
        {isPaused ? "▶ Resume" : "⏸ Pause"}
      </button>

      <button
        className="rec-btn stop"
        onClick={handleStop}
        disabled={busy || isIdle}
      >
        ⏹ Stop
      </button>

      {(isRecording || isPaused) && (
        <span className="rec-indicator">
          <span className={isRecording ? "rec-dot pulsing" : "rec-dot"} />
          <span className="rec-timer">
            {isPaused ? "PAUSED" : "REC"} {formatElapsed(elapsed)}
          </span>
        </span>
      )}

      {error && <span className="rec-error">{error}</span>}

    </div>
  );
}

export default RecordingControls;
