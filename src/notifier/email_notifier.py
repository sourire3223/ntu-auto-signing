import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import MailConfig


class EmailNotifier:
    def __init__(self, config: MailConfig):
        self.config = config

    def send_message(self, title: str, content: str) -> None:
        """Send email with given subject and body"""
        msg = MIMEMultipart()
        msg["From"] = self.config.from_
        msg["To"] = self.config.to
        msg["Subject"] = title
        msg.attach(MIMEText(content, "plain"))

        with smtplib.SMTP(self.config.host, int(self.config.tls_port)) as server:
            server.starttls()
            server.login(self.config.from_, self.config.password)
            server.send_message(msg)
