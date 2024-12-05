from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class Student:
    name: str
    email: str
    folder_name: str
    link: str = None

    @property
    def folder_id(self) -> str:
        return self.link.split("/")[-1]


@dataclass
class AppSession:
    students: list[Student]
