import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import UserCreds

from app import Student

SERVICE_NAME = "drive"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

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
                    q=f"name='{name}' and mimeType='{folder_mimetype}'",
                    pageSize=1,
                    spaces="drive",
                    fields="files(id)",
                )
            )

            if folders := response.get("files", []):
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
    ) -> None:
        students = list(students)

        parent_id = await self._get_root_folder_id(root_folder_name)

        create_requests = [
            self.service.files.create(
                json={
                    "name": student.folder_name,
                    "mimeType": folder_mimetype,
                    "parents": [parent_id],
                },
                fields="id, name, webViewLink",
            )
            for student in students
        ]

        async with self.aiogoogle:
            # noinspection PyTypeChecker
            folders = await self.aiogoogle.as_user(*create_requests)
            folders: list[dict] = [folders] if isinstance(folders, dict) else folders

        for student, folder in zip(students, folders):
            student.link = folder["webViewLink"]

            logging.info(
                f"Created folder: {root_folder_name}/{student.folder_name} -> {student.link}"
            )

    async def download_directories_async(
        self, students: Iterable[Student], destination: os.PathLike | str
    ) -> None:
        students = list(students)
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)

        page_tokens: list[str | None] = [None] * len(students)
        student_files: dict[Student, list[dict]] = {student: [] for student in students}

        async with self.aiogoogle:
            logging.info(f"Searching for files of {len(students)} students...")

            while True:
                search_requests = [
                    self.service.files.list(
                        q=f"'{student.folder_id}' in parents",
                        spaces="drive",
                        fields="nextPageToken, files(id, name, parents)",
                        pageToken=page_token,
                    )
                    for student, page_token in zip(students, page_tokens)
                ]

                # noinspection PyTypeChecker
                responses = await self.aiogoogle.as_user(*search_requests)
                responses: list[dict] = (
                    [responses] if isinstance(responses, dict) else responses
                )

                for student, response in zip(students, responses):
                    student_files[student].extend(response.get("files", []))

                page_tokens = [response.get("nextPageToken") for response in responses]

                if all(map(lambda token: token is None, page_tokens)):
                    break

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

            logging.info("Download complete.")

    def create_folders(
        self, students: Iterable[Student], root_folder_name: str
    ) -> None:
        logging.info("Initializing asynchronous directory creation...")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.create_folders_async(students, root_folder_name))

    def download_directories(
        self, students: Iterable[Student], destination: os.PathLike | str
    ) -> None:
        logging.info("Initializing asynchronous directory download...")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.download_directories_async(students, destination))
