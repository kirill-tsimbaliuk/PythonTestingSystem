import json
import os.path
import sys
import logging
import pickle
import pandas as pd

from app import TaskChecker, AppSession, Student


class MainManager:

    def __init__(self, config: dict):
        self.config = config
        self.checker = TaskChecker(config)

    def process(self, argv: list) -> None:
        command = argv[1]

        if command == "create":
            if len(argv) == 2:
                logging.error("No input file")
                sys.exit()
            self.create(argv[2])
        elif command == "check":
            if len(argv) == 2:
                logging.error("No input name")
                sys.exit()
            self.check(argv[2])
        elif command == "download":
            self.download()
        else:
            logging.error("Invalid command")

    def create(self, path_to_table):
        # Code for create session example session file
        student1 = Student(name="Kirill", email="", link="", folder_name="kirill")
        student2 = Student(name="Test", email="", link="", folder_name="test")
        session = AppSession([student1, student2], 2)

        with open(self.config['session_file'], 'wb') as file:
            pickle.dump(session, file)

    def check(self, sem_name):
        if not os.path.exists(self.config['session_file']):
            logging.error("No session file")
        logging.info("Load session file")

        with open(self.config["session_file"], 'rb') as file:
            session = pickle.load(file)

        results = []
        for student in session.students:
            logging.info(f"Check for student: {student.name}")
            if not os.path.exists(os.path.join(self.config['temp'], student.folder_name)):
                logging.error(f"Fail to find student folder")
                continue
            if not os.path.exists(os.path.join(self.config['temp'], student.folder_name, sem_name + ".py")):
                logging.info(f"No solution find")
                continue
            results.append(self.checker.run_tests())

        data = pd.DataFrame(results)
        data.to_csv(self.config["output"])

    def download(self):
        pass


LOG_LEVEL = "INFO"
LOG_FORMAT = "%(levelname)s - %(asctime)s - %(message)s"

if __name__ == "__main__":
    with open("config.json") as file:
        config = json.load(file)

    if "log" in config:
        logging.basicConfig(filename=config["log"], level=LOG_LEVEL, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

    manager = MainManager(config)
    if len(sys.argv) == 1:
        logging.error("The command has not been entered")
        sys.exit()

    manager.process(sys.argv)
