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
        student1 = Student(
            name="Кирилл Цимбалюк",
            email="tsimbaliuk.ka@phystech.edu",
            folder_name="tsimbaliuk.ka",
        )
        student2 = Student(
            name="Андрей Кругликов",
            email="kruglikov.as@phystech.edu",
            folder_name="kruglikov.as",
        )
        session = AppSession([student1, student2])

        drive_manager = DriveManager(self.config["google_credentials_directory"])

        students_to_notify = drive_manager.create_folders(
            session.students, config["drive_folder"]
        )
        notify(
            students_to_notify,
            config["email_subject"],
            config["email_message_template"],
        )

        self._save_session(session)

    def _load_session(self) -> AppSession:
        if not Path(self.config["session_file"]).exists():
            self.create("")

        logging.info("Load session file")

        with open(self.config["session_file"], "rb") as file:
            return pickle.load(file)

    def _save_session(self, session) -> None:
        with open(self.config["session_file"], "wb") as file:
            # noinspection PyTypeChecker
            pickle.dump(session, file)

    def check(self, sem_name):
        session = self._load_session()

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
        session = self._load_session()

        drive_manager = DriveManager(self.config["google_credentials_directory"])

        drive_manager.download_directories(
            session.students, self.config["temp_directory"]
        )

        self._save_session(session)


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
