import os
import logging


class TaskChecker:
    config: dict

    def __init__(self, config: dict):
        os.makedirs(config["answers"], exist_ok=True)
        os.makedirs(config["temp"], exist_ok=True)
        self.config = config

    def run_tests(self, solution_filename: str, sem_name: str) -> dict:
        output = {}
        try:
            cmd = f"__import__(\"{self.config['answers']}.{sem_name}\").{sem_name}.TASK_COUNT"
        except AttributeError:
            raise logging.error(
                f"Invalid sem file: {self.config['answers']}/{sem_name}.py"
            )
        else:
            for task in range(1, eval(cmd) + 1):
                try:
                    user_func = eval(
                        f"__import__(\"{self.config['temp']}.{solution_filename}\").{solution_filename}.task_{task}"
                    )
                except AttributeError:
                    output[f"task_{task}"] = False
                else:
                    try:
                        right_func = eval(
                            f"__import__(\"{self.config['answers']}.{sem_name}\").{sem_name}.task_{task}"
                        )
                        args_generator = eval(
                            f"__import__(\"{self.config['answers']}.{sem_name}\").{sem_name}.task_{task}_args"
                        )
                    except AttributeError:
                        raise logging.error(
                            f"Invalid sem file: {self.config['answers']}/{sem_name}.py"
                        )
                    else:
                        output[f"task_{task}"] = all(
                            user_func(*args) == right_func(*args)
                            for args in args_generator()
                        )

            return output
