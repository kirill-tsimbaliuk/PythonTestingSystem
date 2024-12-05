import json
import sys
import logging
import pickle
from pathlib import Path

import pandas as pd

from app import TaskChecker, AppSession, Student, DriveManager, notify


class MainManager:
    def __init__(self, config: dict):
        self.config = config
        self.checker = TaskChecker(config)

    def process(self, argv: list) -> None:
        command = argv[1]

        if command == "create":
            if len(argv) < 3:
                logging.error("No input file")
                sys.exit()
            self.create(argv[2])
        elif command == "check":
            if len(argv) < 3:
                logging.error("No input name")
                sys.exit()
            self.check(argv[2])
        elif command == "download":
            self.download()
        else:
            logging.error("Invalid command")

    def create(self, path_to_table):  # TODO
        # Code for create session example session file
        student1 = Student(name="Kirill", email="", link="", folder_name="kirill")
        student2 = Student(name="Test", email="", link="", folder_name="test")
        session = AppSession([student1, student2], 2)

        drive_manager = DriveManager(self.config["google_credentials_directory"])

        drive_manager.create_folders(session.students, config["drive_folder"])
        notify(
            session.students, config["email_subject"], config["email_message_template"]
        )

        with open(self.config["session_file"], "wb") as file:
            # noinspection PyTypeChecker
            pickle.dump(session, file)

    def load_session(self) -> AppSession:
        if not Path(self.config["session_file"]).exists():
            self.create("")

        logging.info("Load session file")

        with open(self.config["session_file"], "rb") as file:
            return pickle.load(file)

    def check(self, sem_name):
        session = self.load_session()

        results = []
        for student in session.students:
            logging.info(f"Check for student: {student.name}")

            if not Path(self.config["temp_directory"], student.folder_name).exists():
                logging.error("Failed to find student folder")
                continue

            if not Path(
                self.config["temp_directory"], student.folder_name, f"{sem_name}.py"
            ).exists():
                logging.error("No solution found")
                continue

            results.append(self.checker.run_tests())  # FIXME

        data = pd.DataFrame(results)
        data.to_csv(self.config["output"])

    def download(self):
        session = self.load_session()

        drive_manager = DriveManager(self.config["google_credentials_directory"])

        drive_manager.download_directories(
            session.students, self.config["temp_directory"]
        )


LOG_LEVEL = "INFO"
LOG_FORMAT = "%(levelname)s - %(asctime)s - %(message)s"
CONFIG_PATH = Path("config.json")

if __name__ == "__main__":
    config = json.loads(CONFIG_PATH.read_text())

    logging.basicConfig(filename=config.get("log"), level=LOG_LEVEL, format=LOG_FORMAT)

    manager = MainManager(config)
    if len(sys.argv) < 2:
        logging.error("The command has not been entered")
        sys.exit()

    manager.process(sys.argv)
