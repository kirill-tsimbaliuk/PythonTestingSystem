import logging
import os
from collections.abc import Iterable
from smtplib import SMTP_SSL
from email.message import EmailMessage

from dotenv import load_dotenv, find_dotenv

from app import Student


load_dotenv(find_dotenv())

SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT"))
SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")


def notify(
    students: Iterable[Student], message_subject: str, message_template: str
) -> None:
    with SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_EMAIL, SMTP_PASSWORD)

        for student in students:
            msg = EmailMessage()
            msg["Subject"] = message_subject
            msg["From"] = SMTP_EMAIL
            msg["To"] = student.email
            msg.set_content(
                message_template.format(name=student.name, link=student.link)
            )

            server.send_message(msg)

            logging.info(f"Notification sent to {student.name}")
