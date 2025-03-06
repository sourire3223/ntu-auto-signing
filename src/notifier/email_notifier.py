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
        msg["From"] = self.config.User
        msg["To"] = self.config.User
        msg["Subject"] = title
        msg.attach(MIMEText(content, "plain"))

        with smtplib.SMTP(self.config.Host, int(self.config.TlsPort)) as server:
            server.starttls()
            server.login(self.config.User, self.config.Password)
            server.send_message(msg)

    def send_error_message(self, error_msg: str, response_data: dict) -> None:
        """Send error notification email if configured"""
        subject = f"Error ({error_msg})"

        body = f"NTU Auto Signing failed: {error_msg}\n\n"
        if "d" in response_data:
            body += f"Timestamp: {response_data['d']}\n"
        if "msg" in response_data:
            body += f"System Message: {response_data['msg']}\n"
        body += f"Response: {json.dumps(response_data, indent=2)}"

        self.send_message(subject, body, self.config)
