from dataclasses import dataclass


@dataclass
class Student:
    name: str
    email: str
    link: str


@dataclass
class AppSession:
    students: list[Student]
    students_count: int
