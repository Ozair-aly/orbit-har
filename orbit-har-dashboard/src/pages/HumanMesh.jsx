import { useEffect, useState } from "react";

function HumanMesh() {

  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(false);

  const BACKEND = "http://127.0.0.1:8000";
  const HUMAN_MESH = "http://127.0.0.1:8010";


  // ==========================================
  // CHECK HUMAN 3D STATUS
  // ==========================================

  const checkStatus = async () => {

    try {

      const response = await fetch(
        `${BACKEND}/human-mesh/status`
      );

      const data = await response.json();

      setRunning(data.running === true);

    } catch {

      setRunning(false);

    }

  };


  // ==========================================
  // CHECK ON PAGE LOAD
  // ==========================================

  useEffect(() => {

    checkStatus();

    const interval = setInterval(
      checkStatus,
      2000
    );

    return () => clearInterval(interval);

  }, []);


  // ==========================================
  // START
  // ==========================================

  const startHumanMesh = async () => {

    setLoading(true);

    try {

      const response = await fetch(
        `${BACKEND}/human-mesh/start`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (data.running) {

        setRunning(true);

      }

    } catch (error) {

      console.error(
        "Human 3D start failed:",
        error
      );

    }

    setLoading(false);

  };


  // ==========================================
  // STOP
  // ==========================================

  const stopHumanMesh = async () => {

    setLoading(true);

    try {

      await fetch(
        `${BACKEND}/human-mesh/stop`,
        {
          method: "POST",
        }
      );

      setRunning(false);

    } catch (error) {

      console.error(
        "Human 3D stop failed:",
        error
      );

    }

    setLoading(false);

  };


  return (
    <div className="human-mesh-page">

      {/* PAGE TITLE */}

      <div className="page-title">

        <h2> 3D Human Mesh</h2>

        <p>
          Standalone MediaPipe-based human pose
          and mesh visualization.
        </p>

      </div>


      {/* MAIN CARD */}

      <div className="human-mesh-card">


        {/* HEADER */}

        <div className="human-mesh-header">

          <div>

            <h3>
              HUMAN 3D VIEWER
            </h3>

            <p>
              Live astronaut body visualization
            </p>

          </div>


          <span className="human-mesh-status">

            {running
              ? "● ONLINE"
              : "● OFFLINE"
            }

          </span>

        </div>


        {/* =====================================
            CONTROL BAR
            ===================================== */}

        <div className="human-mesh-controls">

          <button
            className="human-mesh-start"
            onClick={startHumanMesh}
            disabled={running || loading}
          >
            {loading && !running
              ? "STARTING..."
              : "▶ START HUMAN 3D"
            }
          </button>


          <button
            className="human-mesh-stop"
            onClick={stopHumanMesh}
            disabled={!running || loading}
          >
            {loading && running
              ? "STOPPING..."
              : "■ STOP HUMAN 3D"
            }
          </button>


          <div className="human-mesh-process-status">

            <span>
              STATUS
            </span>

            <strong>
              {running
                ? "MEDIAPIPE ACTIVE"
                : "MEDIAPIPE STOPPED"
              }
            </strong>

          </div>

        </div>


        {/* =====================================
            TWO VIEWER PANELS
            ===================================== */}

        <div className="human-mesh-panels">


          {/* CAMERA */}

          <div className="human-mesh-panel">

            <div className="human-mesh-panel-header">

              <div>

                <h4>
                  LIVE CAMERA
                </h4>

                <span>
                  MediaPipe source camera
                </span>

              </div>


              <span className="panel-status">

                {running
                  ? "● LIVE"
                  : "● OFFLINE"
                }

              </span>

            </div>


            <div className="human-mesh-camera">

              {running ? (

                <img
                  src={`${HUMAN_MESH}/video`}
                  alt="ORBIT-HAR Human 3D Camera"
                />

              ) : (

                <div className="human-mesh-offline">

                  <div>
                    📷
                  </div>

                  <strong>
                    HUMAN 3D OFFLINE
                  </strong>

                  <span>
                    Press START HUMAN 3D
                  </span>

                </div>

              )}

            </div>

          </div>


          {/* 3D MESH */}

          <div className="human-mesh-panel">

            <div className="human-mesh-panel-header">

              <div>

                <h4>
                  3D HUMAN MESH
                </h4>

                <span>
                  MediaPipe Pose World Landmarks
                </span>

              </div>


              <span className="panel-status">

                {running
                  ? "● LOCAL"
                  : "● OFFLINE"
                }

              </span>

            </div>


            <div className="human-mesh-viewer">

              {running ? (

                <img
                  src={`${HUMAN_MESH}/mesh`}
                  alt="ORBIT-HAR 3D Human Mesh"
                />

              ) : (

                <div className="human-mesh-placeholder">

                  <div className="mesh-icon">
                    
                  </div>

                  <h2>
                    HUMAN 3D MESH
                  </h2>

                  <p>
                    MediaPipe body visualization
                  </p>

                  <span>
                    Press START HUMAN 3D
                  </span>

                </div>

              )}

            </div>

          </div>


        </div>


        {/* SYSTEM INFORMATION */}

        <div className="human-mesh-info">

          <div>

            <small>
              MODEL
            </small>

            <strong>
              MediaPipe
            </strong>

          </div>


          <div>

            <small>
              PROCESSING
            </small>

            <strong>
              LOCAL
            </strong>

          </div>


          <div>

            <small>
              EXPERIMENT LINK
            </small>

            <strong>
              DISABLED
            </strong>

          </div>

        </div>


      </div>

    </div>
  );
}

export default HumanMesh;