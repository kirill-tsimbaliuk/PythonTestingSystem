from dataclasses import dataclass


@dataclass
class Student:
    name: str
    email: str
    link: str
    folder_name: str

    @property
    def folder_id(self) -> str:
        return self.link.split("/")[-1]


@dataclass
class AppSession:
    students: list[Student]
    students_count: int
