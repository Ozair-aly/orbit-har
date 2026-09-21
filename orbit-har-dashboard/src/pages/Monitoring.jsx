import RecordingControls from "../components/RecordingControls";

const cameraUrl = "http://127.0.0.1:8000/video";

function formatObjectName(name) {
  return name
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function Monitoring({
  data,
  completedSteps,
  aiStatus,
  cameraOnline,
  logs,
}) {
  const progress =
    data.total_steps > 0
      ? Math.min(100, (data.step / data.total_steps) * 100)
      : 0;

  const isWrong = data.status === "WRONG";
  const isChecking = data.status === "CHECKING";
  const isVerified = data.status === "VERIFIED";

  const isComplete =
    data.status === "SUCCESS" &&
    data.step >= data.total_steps &&
    data.total_steps > 0;

  const objectEntries = Object.entries(aiStatus.objects || {});

  return (
    <main className="dashboard">

      {/* =================================================
          LEFT COLUMN
      ================================================= */}

      <div className="dashboard-left">

        {/* =================================================
            CAMERA
        ================================================= */}

        <section className="panel camera">

          <div className="panel-title">

            <span>
              LIVE CAMERA
            </span>

            <span
              className={
                cameraOnline
                  ? "live"
                  : "offline-camera"
              }
            >
              ●{" "}
              {cameraOnline
                ? "LIVE"
                : "OFFLINE"}
            </span>

          </div>

          <RecordingControls
            cameraOnline={cameraOnline}
          />

          <div className="camera-box">

            {cameraOnline ? (

              <img
                src={cameraUrl}
                alt="ORBIT-HAR Live Camera"
                className="live-camera"
              />

            ) : (

              <div className="camera-offline">

                <h2>
                  ORBIT-HAR
                </h2>

                <p>
                  CAMERA OFFLINE
                </p>

                <small>
                  Start the selected experiment
                </small>

              </div>

            )}

          </div>
 

        </section>


        {/* =================================================
            AI DETECTION
        ================================================= */}

        <section className="panel detection">

          <div className="panel-title">
            AI DETECTION
          </div>

          {/* OBJECT DETECTION */}

          {objectEntries.length > 0 && (

            <>

              <div
                style={{
                  marginBottom: "10px",
                  fontWeight: "bold",
                }}
              >
                OBJECT DETECTION
              </div>

              {objectEntries.map(
                ([name, detected]) => (

                  <div
                    className="detection-item"
                    key={name}
                  >

                    <span>
                      {formatObjectName(name)}
                    </span>

                    <b
                      className={
                        detected
                          ? "detected-state"
                          : "inactive-state"
                      }
                    >
                      {detected
                        ? "✓ DETECTED"
                        : "○ NOT DETECTED"}
                    </b>

                  </div>

                )
              )}

            </>

          )}


          {/* HAND TRACKING */}

          <div className="detection-item">

            <span>
              Hand Tracking
            </span>

            <b
              className={
                aiStatus.handTracking
                  ? "active-state"
                  : "inactive-state"
              }
            >
              {aiStatus.handTracking
                ? "✓ ACTIVE"
                : "○ INACTIVE"}
            </b>

          </div>


          {/* INTERACTION */}

          <div className="detection-item">

            <span>
              Interaction
            </span>

            <b
              className={
                aiStatus.interaction
                  ? "active-state"
                  : "inactive-state"
              }
            >
              {aiStatus.interaction
                ? "✓ DETECTED"
                : "○ NONE"}
            </b>

          </div>


          {/* SEQUENCE ENGINE */}

          <div className="detection-item">

            <span>
              Sequence Engine
            </span>

            <b className="active-state">
              ✓ ACTIVE
            </b>

          </div>


          {/* EDGE PROCESSING */}

          <div className="detection-item">

            <span>
              Edge Processing
            </span>

            <b className="active-state">
              ✓ LOCAL
            </b>

          </div>

        </section>

      </div>


      {/* =================================================
          RIGHT COLUMN
      ================================================= */}

      <div className="dashboard-right">

        {/* =================================================
            EXPERIMENT STATUS
        ================================================= */}

        <section className="panel status">

          <div className="panel-title">
            EXPERIMENT STATUS
          </div>
          <button
  className="stop-experiment-button"
  onClick={async () => {
    console.log("🛑 STOP BUTTON CLICKED");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/experiment/stop",
        {
          method: "POST",
        }
      );

      console.log(
        "STOP RESPONSE STATUS:",
        response.status
      );

      const result = await response.json();

      console.log(
        "🛑 STOP RESPONSE:",
        result
      );

      alert("Stop request sent");

    } catch (error) {

      console.error(
        "❌ STOP REQUEST FAILED:",
        error
      );

      alert(
        "STOP FAILED: " + error.message
      );
    }
  }}
>
  🛑 STOP EXPERIMENT
</button>

          <h2>
            {data.experiment}
          </h2>

          <div className="step-number">

            STEP {data.step}

            <span>
              {" "}
              / {data.total_steps}
            </span>

          </div>

          <div className="progress">

            <div
              className="progress-fill"
              style={{
                width: `${progress}%`,
              }}
            />

          </div>


          {/* DYNAMIC STEP LIST */}

          <div
            style={{
              marginTop: "20px",
              marginBottom: "20px",
            }}
          >

            {Array.from(
              {
                length: data.total_steps || 0,
              },
              (_, index) => index + 1
            ).map((stepNumber) => {

              const completed =
                completedSteps.includes(stepNumber);

              const current =
                data.step === stepNumber;

              return (

                <div
                  key={stepNumber}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "7px 0",
                  }}
                >

                  <span>
                    Step {stepNumber}
                  </span>

                  <strong>

                    {completed
                      ? "✅ COMPLETED"
                      : current
                      ? "🟡 CURRENT"
                      : "○ PENDING"}

                  </strong>

                </div>

              );

            })}

          </div>


          {/* CURRENT INSTRUCTION */}

          <div className="expected">

            <small>
              CURRENT INSTRUCTION
            </small>

            <strong>
              {data.instruction}
            </strong>

          </div>


          {/* EXPECTED ACTION */}

          <div className="expected">

            <small>
              EXPECTED ACTION
            </small>

            <strong>
              {data.expected_action}
            </strong>

          </div>


          {/* AI DETECTED */}

          <div className="detected">

            <small>
              AI DETECTED
            </small>

            <strong
              className={
                isWrong
                  ? "detected-wrong"
                  : ""
              }
            >
              {data.detected_action}
            </strong>

          </div>


          {/* AI ACTIVITY */}

          <div className="expected">

            <small>
              AI ACTIVITY
            </small>

            <strong>
              {data.ai_activity}
            </strong>

          </div>


          {/* STATUS MESSAGES */}

          {isChecking && (

            <div className="waiting-box">
              🧠 AI IS CHECKING ACTION...
            </div>

          )}


          {isVerified && (

            <div className="success-box">
              ✅ STEP VERIFIED
            </div>

          )}


          {isWrong && (

            <div className="error-box">

              ⚠️ WRONG / OUT OF SEQUENCE

              <br />

              Expected:
              {" "}
              {data.expected_action}

              <br />

              Detected:
              {" "}
              {data.detected_action}

            </div>

          )}


          {isComplete && (

            <div className="success-box">
              🎉 EXPERIMENT COMPLETED
            </div>

          )}


          {!isChecking &&
            !isVerified &&
            !isWrong &&
            !isComplete && (

              <div className="waiting-box">
                ⏳ WAITING FOR ACTION
              </div>

            )}

        </section>


        {/* =================================================
            MISSION LOG
        ================================================= */}

        <section className="panel mission">

          <div className="panel-title">
            LIVE MISSION LOG
          </div>

          {logs.length === 0 ? (

            <div className="empty">
              Waiting for experiment events...
            </div>

          ) : (

            logs.map((log, index) => (

              <div
                className="log"
                key={index}
              >

                <span>
                  {log.time}
                </span>

                <strong>
                  {log.action}
                </strong>

                <b>

                  {log.status === "SUCCESS"
                    ? "✓"
                    : log.status === "WRONG"
                    ? "⚠"
                    : "●"}

                </b>

              </div>

            ))

          )}

        </section>

      </div>

    </main>
  );
}

export default Monitoring;