import os
from datetime import datetime


class ExperimentLogger:

    def __init__(self, experiment_name):

        self.experiment_name = experiment_name

        os.makedirs("logs", exist_ok=True)

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        self.filename = (
            f"logs/experiment_{timestamp}.txt"
        )

        self.start_time = datetime.now()

        with open(self.filename, "w") as file:

            file.write(
                "ORBIT-HAR EXPERIMENT LOG\n"
            )

            file.write(
                "========================\n"
            )

            file.write(
                f"Experiment: "
                f"{self.experiment_name}\n"
            )

            file.write(
                f"Started: "
                f"{self.start_time.strftime('%d-%b-%Y %H:%M:%S')}\n\n"
            )


    def log_step(self, step_id, action, status):

        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        with open(self.filename, "a") as file:

            file.write(
                f"STEP {step_id}\n"
            )

            file.write(
                f"Action: {action}\n"
            )

            file.write(
                f"Status: {status}\n"
            )

            file.write(
                f"Time: {timestamp}\n\n"
            )


    def complete_experiment(self):

        timestamp = datetime.now().strftime(
            "%d-%b-%Y %H:%M:%S"
        )

        with open(self.filename, "a") as file:

            file.write(
                "========================\n"
            )

            file.write(
                "EXPERIMENT COMPLETE\n"
            )

            file.write(
                f"Completed: {timestamp}\n"
            )