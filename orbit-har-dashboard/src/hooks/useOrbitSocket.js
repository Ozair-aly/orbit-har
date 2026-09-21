import { useEffect, useState } from "react";

const WS_URL = "wss://orbit-har-1.onrender.com/ws";
const CAMERA_STATUS_URL = "https://orbit-har-1.onrender.com/camera/status";

export function useOrbitSocket() {

  // ==========================================================
  // GENERIC EXPERIMENT DATA
  // ==========================================================

  const [data, setData] = useState({
    experiment: "---",
    step: 0,
    total_steps: 0,
    expected_action: "---",
    detected_action: "WAITING",
    status: "WAITING",
    instruction: "---",
    ai_activity: "SEARCHING",
  });

  const [completedSteps, setCompletedSteps] = useState([]);
  const [logs, setLogs] = useState([]);

  const [connected, setConnected] = useState(false);
  const [cameraOnline, setCameraOnline] = useState(false);
  const [voiceMessage, setVoiceMessage] = useState(null);

  // ==========================================================
  // GENERIC AI STATUS
  // ==========================================================

  const [aiStatus, setAiStatus] = useState({
    objects: {},
    handTracking: false,
    interaction: false,
    sequenceEngine: true,
    edgeProcessing: true,
    activity: "SEARCHING",
    status: "READY",
  });

  // ==========================================================
  // WEBSOCKET
  // ==========================================================

  useEffect(() => {

    let socket;
    let reconnectTimer;

    const connectWebSocket = () => {

      socket = new WebSocket(WS_URL);

      // ------------------------------------------------------
      // CONNECTED
      // ------------------------------------------------------

      socket.onopen = () => {

        console.log("🟢 ORBIT-HAR backend connected");

        setConnected(true);
      };

      // ------------------------------------------------------
      // MESSAGE
      // ------------------------------------------------------

      socket.onmessage = (event) => {

        try {

          const message = JSON.parse(event.data);
          // ==================================================
          // VOICE ASSISTANT
          // ==================================================

          if (message.type === "voice") {

            const text = message.message;

            if (text) {

              console.log("🔊 DASHBOARD VOICE:", text);

              setVoiceMessage(text);

              const utterance =
                new SpeechSynthesisUtterance(text);

              utterance.rate = 1;
              utterance.pitch = 1;
              utterance.volume = 1;

              window.speechSynthesis.cancel();

              window.speechSynthesis.speak(
                utterance
              );
            }

            return;
          }

          // ==================================================
          // AI STATUS
          // ==================================================

          if (message.type === "ai_status") {

            setData((prev) => ({

              ...prev,

              experiment:
                message.experiment ??
                prev.experiment,

              step:
                Number(
                  message.step ??
                  prev.step
                ),

              total_steps:
                Number(
                  message.total_steps ??
                  prev.total_steps
                ),

              expected_action:
                message.expected_action ??
                prev.expected_action,

              detected_action:
                message.detected_action ??
                prev.detected_action,

              status:
                message.ai_status ??
                prev.status,

              instruction:
                message.instruction ??
                prev.instruction,

              ai_activity:
                message.ai_activity ??
                prev.ai_activity,

            }));


            // ------------------------------------------------
            // GENERIC OBJECT DETECTION
            // ------------------------------------------------

            const objects = {};

            if (
              message.syringe_detected !== undefined
            ) {

              objects.syringe =
                Boolean(
                  message.syringe_detected
                );

            }

            if (
              message.bottle_detected !== undefined
            ) {

              objects.container =
                Boolean(
                  message.bottle_detected
                );

            }

            if (
              message.container_detected !== undefined
            ) {

              objects.container =
                Boolean(
                  message.container_detected
                );

            }

            if (
              message.container_a_detected !== undefined
            ) {

              objects.container_a =
                Boolean(
                  message.container_a_detected
                );

            }

            if (
              message.container_b_detected !== undefined
            ) {

              objects.container_b =
                Boolean(
                  message.container_b_detected
                );

            }


            // ------------------------------------------------
            // GENERIC INTERACTION
            // ------------------------------------------------

            const interaction =
              Boolean(
                message.hand_container_interaction ||
                message.hand_syringe_interaction
              );


            setAiStatus({

              objects,

              handTracking:
                Boolean(
                  message.hand_detected
                ),

              interaction,

              sequenceEngine: true,

              edgeProcessing: true,

              activity:
                message.ai_activity ||
                "SEARCHING",

              status:
                message.ai_status ||
                "READY",

            });

            return;
          }


          // ==================================================
          // STEP VERIFIED
          // ==================================================

          if (
            message.type ===
            "step_verified"
          ) {

            const completedStep =
              Number(
                message.completed_step
              );

            const currentStep =
              Number(
                message.current_step
              );

            const totalSteps =
              Number(
                message.total_steps || 0
              );


            setCompletedSteps((prev) =>
              prev.includes(completedStep)
                ? prev
                : [
                    ...prev,
                    completedStep
                  ]
            );


            setData((prev) => ({

              ...prev,

              experiment:
                message.experiment ||
                prev.experiment,

              step:
                currentStep,

              total_steps:
                totalSteps,

              expected_action:
                message.next_action ||
                "---",

              detected_action:
                "WAITING",

              status:
                "VERIFIED",

              instruction:
                message.next_instruction ||
                "---",

            }));


            const time =
              new Date().toLocaleTimeString();


            setLogs((prev) => [

              {
                time,

                action:
                  `STEP ${completedStep} COMPLETED`,

                status:
                  "SUCCESS",

              },

              ...prev,

            ].slice(0, 10));


            return;
          }


          // ==================================================
          // EXPERIMENT COMPLETE
          // ==================================================

          if (
            message.type ===
            "experiment_complete"
          ) {

            const totalSteps =
              Number(
                message.total_steps || 0
              );


            setCompletedSteps(
              Array.from(
                {
                  length:
                    totalSteps,
                },
                (_, i) =>
                  i + 1
              )
            );


            setData((prev) => ({

              ...prev,

              experiment:
                message.experiment ||
                prev.experiment,

              step:
                totalSteps,

              total_steps:
                totalSteps,

              expected_action:
                "COMPLETE",

              detected_action:
                message.detected_action ||
                "COMPLETE",

              status:
                "SUCCESS",

              instruction:
                "Experiment completed",

            }));


            const time =
              new Date().toLocaleTimeString();


            setLogs((prev) => [

              {
                time,

                action:
                  "EXPERIMENT COMPLETED",

                status:
                  "SUCCESS",

              },

              ...prev,

            ].slice(0, 10));


            return;
          }


          // ==================================================
          // ACTION DETECTED
          // ==================================================

          if (
            message.type ===
            "action_detected"
          ) {

            const totalSteps =
              Number(
                message.total_steps || 0
              );

            const status =
              message.status ||
              "UNKNOWN";

            const detected =
              message.detected_action ||
              "---";

            const expected =
              message.expected_action ||
              "---";


            // ------------------------------------------------
            // WRONG ACTION
            // ------------------------------------------------

            if (
              status ===
              "WRONG"
            ) {

              setData((prev) => ({

                ...prev,

                experiment:
                  message.experiment ||
                  prev.experiment,

                step:
                  Number(
                    message.step ??
                    prev.step
                  ),

                total_steps:
                  totalSteps,

                expected_action:
                  expected,

                detected_action:
                  detected,

                status:
                  "WRONG",

              }));


              const time =
                new Date().toLocaleTimeString();


              setLogs((prev) => [

                {
                  time,

                  action:
                    detected,

                  status:
                    "WRONG",

                },

                ...prev,

              ].slice(0, 10));


              return;
            }


            // ------------------------------------------------
            // CHECKING
            // ------------------------------------------------

            if (
              status ===
              "CHECKING"
            ) {

              setData((prev) => ({

                ...prev,

                experiment:
                  message.experiment ||
                  prev.experiment,

                step:
                  Number(
                    message.step ??
                    prev.step
                  ),

                total_steps:
                  totalSteps,

                expected_action:
                  expected,

                detected_action:
                  detected,

                status:
                  "CHECKING",

              }));


              return;
            }

            return;
          }


          // ==================================================
          // CAMERA STATUS
          // ==================================================

          if (
            message.type ===
            "camera_status"
          ) {

            setCameraOnline(
              Boolean(
                message.active
              )
            );

            return;
          }

        }

        catch (error) {

          console.error(
            "❌ WebSocket message error:",
            error
          );

        }

      };


      // ======================================================
      // ERROR
      // ======================================================

      socket.onerror = () => {

        console.log(
          "🔴 WebSocket error"
        );

        setConnected(false);

      };


      // ======================================================
      // DISCONNECTED
      // ======================================================

      socket.onclose = () => {

        console.log(
          "🔴 Backend disconnected"
        );

        setConnected(false);

        reconnectTimer =
          setTimeout(
            connectWebSocket,
            2000
          );

      };

    };


    connectWebSocket();


    return () => {

      clearTimeout(
        reconnectTimer
      );

      if (socket) {
        socket.close();
      }

    };

  }, []);


  // ==========================================================
  // CAMERA STATUS POLLING
  // ==========================================================

  useEffect(() => {

    const checkCamera = async () => {

      try {

        const response =
          await fetch(
            CAMERA_STATUS_URL
          );


        if (!response.ok) {

          setCameraOnline(false);

          return;

        }


        const result =
          await response.json();


        setCameraOnline(
          Boolean(
            result.active
          )
        );

      }

      catch {

        setCameraOnline(false);

      }

    };


    checkCamera();


    const interval =
      setInterval(
        checkCamera,
        1000
      );


    return () =>
      clearInterval(
        interval
      );

  }, []);


  // ==========================================================
  // RETURN
  // ==========================================================

  return {

    data,

    completedSteps,

    logs,

    connected,

    aiStatus,

    cameraOnline,

    voiceMessage,

  };

}