import json
import sys
import logging

from app import TaskChecker


class MainManager:

    def __init__(self, config: dict):
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
            self.create(argv[2])
        elif command == "download":
            self.download()
        else:
            logging.error("Invalid command")

    def create(self, path_to_table):
        pass

    def check(self, sem_name):
        pass

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
