import json
import os
import subprocess
from datetime import datetime


# ==========================================
# ORBIT-HAR
# Onboard Experiment Human Activity Recognition
# ==========================================

EXPERIMENT_FILE = "experiments/liquid_transfer.json"


class OrbitHAR:

    def __init__(self, experiment_file):

        self.experiment_file = experiment_file
        self.experiment = self.load_experiment()

        self.steps = self.experiment["steps"]
        self.current_step = 0

        print("\n🚀 ORBIT-HAR INITIALIZED")
        print("=" * 45)
        print(f"Experiment: {self.experiment['name']}")
        print("=" * 45)

    # --------------------------------------
    # LOAD EXPERIMENT
    # --------------------------------------

    def load_experiment(self):

        if not os.path.exists(self.experiment_file):

            raise FileNotFoundError(
                f"Experiment file not found: "
                f"{self.experiment_file}"
            )

        with open(
            self.experiment_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    # --------------------------------------
    # CURRENT STEP
    # --------------------------------------

    def get_current_step(self):

        if self.current_step >= len(self.steps):
            return None

        return self.steps[self.current_step]

    # --------------------------------------
    # VOICE
    # --------------------------------------

    def speak(self, message):

        print(f"🔊 ORBIT-HAR: {message}")

        subprocess.run([
            "say",
            message
        ])

    # --------------------------------------
    # PROCESS AI ACTION
    # --------------------------------------

    def process_action(self, detected_action):

        current = self.get_current_step()

        if current is None:

            print("🎉 Experiment already completed.")
            return

        expected = current["action"]

        print("\n-----------------------------------------")
        print(f"Expected : {expected}")
        print(f"Detected : {detected_action}")

        # ------------------------------
        # CORRECT
        # ------------------------------

        if detected_action == expected:

            print("✅ CORRECT")

            self.current_step += 1

            if self.current_step >= len(self.steps):

                print("\n🎉 EXPERIMENT COMPLETED!")

                self.speak(
                    "Experiment completed successfully."
                )

            else:

                next_step = self.get_current_step()

                print(
                    f"➡️ Next: "
                    f"{next_step['instruction']}"
                )

                self.speak(
                    f"Correct. "
                    f"Next step. "
                    f"{next_step['instruction']}"
                )

        # ------------------------------
        # WRONG / SKIPPED
        # ------------------------------

        else:

            future_actions = [
                step["action"]
                for step in self.steps[
                    self.current_step + 1:
                ]
            ]

            if detected_action in future_actions:

                print("🔴 STEP SKIPPED")

                message = (
                    f"Please complete "
                    f"{current['instruction']} "
                    f"before continuing."
                )

                self.speak(message)

            else:

                print("⚠️ UNEXPECTED ACTION")

                self.speak(
                    "Unexpected action detected. "
                    "Please follow the experiment sequence."
                )

    # --------------------------------------
    # STATUS
    # --------------------------------------

    def show_status(self):

        print("\n========== ORBIT-HAR STATUS ==========")

        if self.current_step >= len(self.steps):

            print("STATUS : 🎉 COMPLETE")

        else:

            step = self.get_current_step()

            print(
                f"STEP   : "
                f"{self.current_step + 1}/"
                f"{len(self.steps)}"
            )

            print(
                f"ACTION : {step['action']}"
            )

            print(
                f"NEXT   : {step['instruction']}"
            )

        print("=======================================")


# ==========================================
# START ORBIT-HAR
# ==========================================

if __name__ == "__main__":

    orbit = OrbitHAR(EXPERIMENT_FILE)

    orbit.show_status()

    print("\n🧪 TESTING AI ACTION PIPELINE")

    # Simulated AI detections.
    # Later these will come from
    # our camera + HAR model.

    test_actions = [
        "PICK_CONTAINER",
        "PLACE_CONTAINER",
        "TRANSFER_SAMPLE",   # INTENTIONALLY WRONG
        "OPEN_VALVE",
        "TRANSFER_SAMPLE",
        "CLOSE_VALVE"
    ]

    for action in test_actions:

        orbit.process_action(action)

## hello guys if you are reading this it means you did go through the code just to check on things so when you see me SAY "HELLO DARKNESS MY OLD FRIEND!!"