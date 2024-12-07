import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Iterable

from aiogoogle.models import Response
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import UserCreds

from app import Student

SERVICE_NAME = "drive"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/drive"]

folder_mimetype = "application/vnd.google-apps.folder"


class DriveManager:
    def __init__(self, credentials_directory: os.PathLike | str) -> None:
        credentials_directory = Path(credentials_directory)

        creds: Credentials | None = None

        token_json_path = credentials_directory / "token.json"
        credentials_json_path = credentials_directory / "credentials.json"

        if token_json_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_json_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_json_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            token_json_path.write_text(creds.to_json())

        token_json = json.loads(token_json_path.read_text())

        user_creds = UserCreds(
            access_token=token_json["token"],
            refresh_token=token_json["refresh_token"],
            expires_at=token_json["expiry"],
            scopes=token_json["scopes"],
        )

        self.aiogoogle = Aiogoogle(user_creds=user_creds)

        loop = asyncio.get_event_loop()
        self.service = loop.run_until_complete(
            self.aiogoogle.discover(SERVICE_NAME, API_VERSION)
        )

    async def _get_root_folder_id(self, name: str) -> str:
        async with self.aiogoogle:
            # noinspection PyTypeChecker
            response: dict = await self.aiogoogle.as_user(
                self.service.files.list(
                    q=f"name = '{name}' and mimeType = '{folder_mimetype}' and trashed = false",
                    pageSize=1,
                    spaces="drive",
                    fields="files(id)",
                )
            )

            if folders := response["files"]:
                return folders[0]["id"]
            else:
                # noinspection PyTypeChecker
                folder: dict = await self.aiogoogle.as_user(
                    self.service.files.create(
                        json={
                            "name": name,
                            "mimeType": folder_mimetype,
                        },
                        fields="id",
                    )
                )

                return folder["id"]

    async def create_folders_async(
        self, students: Iterable[Student], root_folder_name: str
    ) -> list[Student]:
        students_without_folder = list(students)

        parent_id = await self._get_root_folder_id(root_folder_name)

        async with self.aiogoogle:
            # noinspection PyTypeChecker
            check_response: Response = await self.aiogoogle.as_user(
                self.service.files.list(
                    q=(
                        f"'{parent_id}' in parents and "
                        f"mimeType = '{folder_mimetype}' and "
                        f"trashed = false"
                    ),
                    spaces="drive",
                    fields="files(name, webViewLink)",
                ),
                full_res=True,
            )

            async for page in check_response:
                for folder in page["files"]:
                    for student in students_without_folder:
                        if folder["name"] == student.folder_name:
                            student.link = folder["webViewLink"]
                            students_without_folder.remove(student)

            if not students_without_folder:
                logging.info("Folders for all students have been already created")
                return students_without_folder

            create_requests = [
                self.service.files.create(
                    json={
                        "name": student.folder_name,
                        "mimeType": folder_mimetype,
                        "parents": [parent_id],
                    },
                    fields="id, name, webViewLink",
                )
                for student in students_without_folder
            ]

            # noinspection PyTypeChecker
            folders = await self.aiogoogle.as_user(*create_requests)
            folders: list[dict] = [folders] if isinstance(folders, dict) else folders

            permission_requests = [
                self.service.permissions.create(
                    fileId=folder["id"],
                    json={
                        "role": "writer",
                        "type": "anyone",
                    },
                )
                for student, folder in zip(students_without_folder, folders)
            ]

            await self.aiogoogle.as_user(*permission_requests)

        for student, folder in zip(students_without_folder, folders):
            student.link = folder["webViewLink"]

            logging.info(
                f"Created folder: {root_folder_name}/{student.folder_name} -> {student.link}"
            )

        return students_without_folder

    async def download_directories_async(
        self, students: Iterable[Student], destination: os.PathLike | str
    ) -> None:
        students = list(students)
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)

        student_files: dict[Student, list[dict]] = {student: [] for student in students}

        for student in students:
            (destination / student.folder_name).mkdir(parents=True, exist_ok=True)

        async with self.aiogoogle:
            logging.info(f"Searching for files of {len(students)} students...")

            search_requests = [
                self.service.files.list(
                    q=f"'{student.folder_id}' in parents and trashed = false",
                    spaces="drive",
                    fields="files(id, name)"
                )
                for student in students
            ]

            # noinspection PyTypeChecker
            responses = await self.aiogoogle.as_user(*search_requests, full_res=True)
            responses: list[Response] = (
                [responses] if isinstance(responses, Response) else responses
            )

            for student, response in zip(students, responses):
                async for page in response:
                    student_files[student].extend(page["files"])

            logging.info(
                f"Downloading {sum(map(len, student_files.values()))} student files..."
            )

            download_requests = [
                self.service.files.get(
                    fileId=file["id"],
                    download_file=str(destination / student.folder_name / file["name"]),
                    alt="media",
                )
                for student, files in student_files.items()
                for file in files
            ]

            await self.aiogoogle.as_user(*download_requests)

            logging.info("Download completed")

    def create_folders(
        self, students: Iterable[Student], root_folder_name: str
    ) -> list[Student]:
        logging.info("Initializing asynchronous directory creation...")

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.create_folders_async(students, root_folder_name)
        )

    def download_directories(
        self, students: Iterable[Student], destination: os.PathLike | str
    ) -> None:
        logging.info("Initializing asynchronous directory download...")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.download_directories_async(students, destination))
