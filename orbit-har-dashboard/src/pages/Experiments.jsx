import { useState } from "react";
import { BACKEND_URL } from "../config.js";

const EXPERIMENTS = [
  {
    id: "container-orientation",
    name: "Container Orientation Experiment",
    icon: "🧪",
    description:
      "Perform the container orientation experiment using real-time astronaut interaction tracking.",
    json: {
      name: "Container Orientation Experiment",
      steps: [
        {
          id: 1,
          action: "PICK_CONTAINER",
          instruction: "Pick up the sample container",
        },
        {
          id: 2,
          action: "TILT_CONTAINER",
          instruction: "Tilt the sample container",
        },
        {
          id: 3,
          action: "SHAKE_CONTAINER",
          instruction: "Shake the sample container",
        },
        {
          id: 4,
          action: "RETURN_UPRIGHT",
          instruction:
            "Return the sample container to an upright position",
        },
        {
          id: 5,
          action: "PUT_CONTAINER_DOWN",
          instruction: "Put the sample container down",
        },
      ],
    },
  },

  {
    id: "syringe-liquid-transfer",
    name: "Syringe Liquid Transfer",
    icon: "💉",
    description:
      "Transfer liquid from Container A to Container B using a syringe.",
    json: {
      name: "Syringe Liquid Transfer",
      steps: [
        {
          id: 1,
          action: "PICK_SYRINGE",
          instruction: "Pick up the syringe",
        },
        {
          id: 2,
          action: "INSERT_CONTAINER_A",
          instruction: "Insert the syringe into Container A (green)",
        },
        {
          id: 3,
          action: "DRAW_LIQUID",
          instruction: "Draw liquid into the syringe",
        },
        {
          id: 4,
          action: "INSERT_CONTAINER_B",
          instruction: "Insert the syringe into Container B (yellow)",
        },
        {
          id: 5,
          action: "RETURN_SYRINGE",
          instruction:
            "Put the syringe back in its original position",
        },
      ],
    },
  },

  // ============================================================
  // SEED SORTING
  // ============================================================

  {
    id: "seed-sorting",
    name: "Seed Sorting Experiment",
    icon: "🌱",
    description:
      "Sort red and blue seeds into their calibrated target containers using real-time hand interaction tracking.",
    json: {
      name: "Seed Sorting Experiment",

      description:
        "Sequential red and blue seed sorting using hand interaction and calibrated container regions.",

      error_detection: false,

      steps: [
        {
          id: 1,
          action: "PICK_RED_SEED",
          instruction: "Pick up the red seed",
          object: "RED",
          source: "SEED AREA",
        },
        {
          id: 2,
          action: "PLACE_RED_SEED",
          instruction: "Place the red seed into Container A",
          object: "RED",
          target: "CONTAINER A",
        },
        {
          id: 3,
          action: "PICK_BLUE_SEED",
          instruction: "Pick up the blue seed",
          object: "BLUE",
          source: "SEED AREA",
        },
        {
          id: 4,
          action: "PLACE_BLUE_SEED",
          instruction: "Place the blue seed into Container B",
          object: "BLUE",
          target: "CONTAINER B",
        },
      ],
    },
  },
];

function Experiments() {
  const [selectedExperiment, setSelectedExperiment] = useState(null);
  const [starting, setStarting] = useState(false);

  // ============================================================
  // START EXPERIMENT
  // ============================================================

  const startExperiment = async () => {
    if (!selectedExperiment) return;

    setStarting(true);

    try {
      const response = await fetch(
        `${BACKEND_URL}/experiment/start`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(selectedExperiment.json),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to start experiment");
      }

      const result = await response.json();

      console.log("🚀 Experiment started:", result);

      if (result.status === "error") {
        throw new Error(result.message || "Experiment failed to start");
      }

      // Go to Monitoring
      window.location.href = "/";
    } catch (error) {
      console.error("❌ Failed to start experiment:", error);

      alert(
        error.message ||
          "Could not start experiment. Is the ORBIT-HAR backend running?"
      );
    } finally {
      setStarting(false);
    }
  };

  // ============================================================
  // EXPERIMENT DETAILS
  // ============================================================

  if (selectedExperiment) {
    const experiment = selectedExperiment.json;

    return (
      <div className="experiments-page">

        {/* BACK */}

        <button
          className="experiment-back"
          onClick={() => setSelectedExperiment(null)}
        >
          ← Back to Experiments
        </button>

        {/* TITLE */}

        <div className="page-title">

          <h2>
            {selectedExperiment.icon} {experiment.name}
          </h2>

          <p>
            Review the experimental procedure before starting the mission.
          </p>

        </div>

        {/* DETAILS */}

        <div className="experiment-details-card">

          <div className="experiment-details-header">

            <div>

              <h3>
                Experiment Procedure
              </h3>

              <p>
                {experiment.steps.length} steps
              </p>

            </div>

            <span className="experiment-status">
              READY
            </span>

          </div>

          {/* STEPS */}

          <div className="experiment-step-list">

            {experiment.steps.map((step) => (

              <div
                className="experiment-step"
                key={step.id}
              >

                <div className="experiment-step-number">
                  {step.id}
                </div>

                <div className="experiment-step-info">

                  <strong>
                    STEP {step.id}
                  </strong>

                  <span>
                    {step.instruction}
                  </span>

                  <small>
                    Expected action: {step.action}
                  </small>

                </div>

              </div>

            ))}

          </div>

          {/* START */}

          <div className="experiment-actions">

            <button
              className="experiment-start-large"
              onClick={startExperiment}
              disabled={starting}
            >
              {starting
                ? "STARTING..."
                : "▶ START EXPERIMENT"}
            </button>

          </div>

        </div>

      </div>
    );
  }

  // ============================================================
  // EXPERIMENT LIST
  // ============================================================

  return (
    <div className="experiments-page">

      <div className="page-title">

        <h2>
          Experiments
        </h2>

        <p>
          Select an experiment to begin an ORBIT-HAR mission.
        </p>

      </div>

      {EXPERIMENTS.map((experiment) => (

        <div
          className="experiment-card"
          key={experiment.id}
          onClick={() =>
            setSelectedExperiment(experiment)
          }
        >

          <div className="experiment-icon">
            {experiment.icon}
          </div>

          <div className="experiment-info">

            <h3>
              {experiment.name}
            </h3>

            <p>
              {experiment.description}
            </p>

            <span className="experiment-steps">
              {experiment.json.steps.length} Steps
            </span>

          </div>

          <button
            className="experiment-start"
            onClick={(event) => {
              event.stopPropagation();
              setSelectedExperiment(experiment);
            }}
          >
            View Experiment →
          </button>

        </div>

      ))}

    </div>
  );
}

export default Experiments;