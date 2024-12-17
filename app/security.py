import re
from pathlib import Path


class SecurityChecker:
    _BANNED_EXPRESSIONS = [
        r"open",
        r"os\.system",
        r"subprocess\.",
        r"google_credentials",
        r"credentials\.json",
        r"token\.json",
        r"\.env",
        r"sys\.",
        r"\.load",
        r"\.dump",
        r"session\.session",
        r"config\.json",
        r"answers\.sem_[0-9][0-9]",
    ]

    @classmethod
    def check_before_run(cls, file_path: str | Path) -> bool:
        with open(file_path) as file:
            text = file.read()

        return all(not re.search(expression, text) for expression in cls._BANNED_EXPRESSIONS)
