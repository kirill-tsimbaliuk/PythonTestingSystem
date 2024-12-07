import logging
from pathlib import Path


class TaskChecker:
    config: dict

    def __init__(self, config: dict):
        Path(config["answers_directory"]).mkdir(parents=True, exist_ok=True)
        Path(config["temp_directory"]).mkdir(parents=True, exist_ok=True)
        self.config = config

    def run_tests(self, student_folder_name: str, sem_name: str) -> dict:
        try:
            query = f"__import__(\"{self.config['answers_directory']}.{sem_name}\").{sem_name}.TASK_COUNT"
            task_count = eval(query)
        except AttributeError:
            raise logging.error(
                f"Invalid sem file: {self.config['answers_directory']}/{sem_name}.py"
            )
        else:
            output = {}
            for task in range(1, task_count + 1):
                try:
                    user_func = eval(
                        f"__import__(\"{self.config['temp_directory']}.{student_folder_name}.{sem_name}\")"
                        f".{student_folder_name}.{sem_name}.task_{task}"
                    )
                except AttributeError:
                    logging.info(f"No solution found for the task: task_{task}")
                    output[f"task_{task}"] = False
                else:
                    try:
                        right_func = eval(
                            f"__import__(\"{self.config['answers_directory']}.{sem_name}\").{sem_name}.task_{task}"
                        )
                        args_generator = eval(
                            f"__import__(\"{self.config['answers_directory']}.{sem_name}\").{sem_name}.task_{task}_args"
                        )
                    except AttributeError:
                        raise logging.error(
                            f"Invalid sem file: {self.config['answers_directory']}/{sem_name}.py"
                        )
                    else:
                        output[f"task_{task}"] = all(
                            user_func(*args) == right_func(*args)
                            for args in args_generator()
                        )

            return output
