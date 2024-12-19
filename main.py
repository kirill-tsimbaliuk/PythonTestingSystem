import json
import os
import sys
import logging
import pickle
from pathlib import Path

import pandas as pd

from app import TaskChecker, AppSession, Student, DriveManager, notify, SecurityChecker


class MainManager:
    def __init__(self, config: dict):
        self.config = config

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

    def create(self, path_to_table: os.PathLike | str) -> None:
        students = []

        raw_json = Path(path_to_table).read_text()
        for line in json.loads(raw_json):
            student = Student(
                name=line[2][1],
                email=line[3][1],
                folder_name=line[3][1][: line[3][1].find("@")].replace(".", ""),
            )
            students.append(student)

        session = AppSession(students)

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
            logging.error("No input file")
            sys.exit()

        logging.info("Load session file")

        with open(self.config["session_file"], "rb") as file:
            return pickle.load(file)

    def _save_session(self, session) -> None:
        with open(self.config["session_file"], "wb") as file:
            # noinspection PyTypeChecker
            pickle.dump(session, file)

    def check(self, sem_name):
        checker = TaskChecker(config)
        session = self._load_session()

        results = []
        task_columns = []
        for student in session.students:
            logging.info(f"Check for student: {student.name}")

            if not Path(self.config["temp_directory"], student.folder_name).exists():
                logging.error("Failed to find student folder")
                continue

            solution_path = Path(
                self.config["temp_directory"], student.folder_name, f"{sem_name}.py"
            )
            if not solution_path.exists():
                logging.error("No solution found")
                continue

            if not SecurityChecker.check_before_run(solution_path):
                logging.error("File security check failed")
                continue

            report = checker.run_tests(student.folder_name, sem_name)
            task_columns = list(report.keys())
            report["Percent"] = sum(report.values()) / len(task_columns)
            report["Name"] = student.name
            report["Email"] = student.email
            results.append(report)

        if len(results) == 0:
            sys.exit()

        data = pd.DataFrame(results)[["Name", "Email"] + task_columns + ["Percent"]]
        output_directory = Path(self.config["output_directory"])
        output_directory.mkdir(exist_ok=True)
        output_file_path = output_directory / (sem_name + ".csv")
        data.to_csv(output_file_path, index=False)
        logging.info(f"The report is saved on path: {output_file_path}")
        print(data)

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
