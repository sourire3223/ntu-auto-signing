import json
import re
from typing import Literal
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.config import UserConfig


class WebSigner:
    """NTU Auto Sign-in/out handler"""

    BASE_URL = "https://my.ntu.edu.tw/"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    )

    def __init__(self, config: UserConfig):
        self.config = config
        self.session = self._init_session()

    def _init_session(self) -> requests.Session:
        """Initialize HTTP session with default headers"""
        session = requests.Session()
        session.headers.update({"User-Agent": self.USER_AGENT, "Connection": "keep-alive"})
        return session

    def login_myntu(self) -> None:
        """Handle MYNTU login process"""
        # Initial request to get session cookies
        self.session.get(self.BASE_URL).raise_for_status()

        # Step 1: Navigate to login page to get redirect
        self.session.headers.update({"Host": "my.ntu.edu.tw", "Referer": "https://my.ntu.edu.tw/attend/ssi.aspx"})
        response = self.session.get("https://my.ntu.edu.tw/attend/ssi.aspx?type=login", allow_redirects=False)
        response.raise_for_status()

        # Step 2: Follow first redirect to NTU portal
        redirect_url = urljoin(self.BASE_URL, response.headers["Location"])
        response = self.session.get(redirect_url, allow_redirects=False)
        response.raise_for_status()

        # Step 3: Follow redirect to login page
        redirect_url = response.headers["Location"]
        self.session.headers.update({"Host": "web2.cc.ntu.edu.tw", "Referer": "https://my.ntu.edu.tw/attend/ssi.aspx"})
        self.session.get(redirect_url, allow_redirects=False).raise_for_status()

        # Step 4: Submit login credentials
        self.session.headers.update(
            {
                "Host": "web2.cc.ntu.edu.tw",
                "Origin": "https://web2.cc.ntu.edu.tw",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://web2.cc.ntu.edu.tw/p/s/login2/p1.php",
            }
        )
        login_data = {"user": self.config.username, "pass": self.config.password, "Submit": "登入"}
        response = self.session.post(
            "https://web2.cc.ntu.edu.tw/p/s/login2/p1.php", data=login_data, allow_redirects=False
        )
        response.raise_for_status()

        # Step 5: Follow redirect back to portal
        redirect_url = response.headers["Location"]
        self.session.headers.update({"Host": "my.ntu.edu.tw"})
        # Remove unnecessary headers
        for header in ["Origin", "Content-Type"]:
            if header in self.session.headers:
                self.session.headers.pop(header)

        response = self.session.post(redirect_url, allow_redirects=False)
        response.raise_for_status()

        # Step 6: Final redirect to attendance system
        redirect_url = response.headers["Location"]
        self.session.get(redirect_url, allow_redirects=False).raise_for_status()
        self.session.headers.pop("Referer", None)

    def check_login_success_on_attend_page(self) -> bool:
        """Verify login success by checking attendance page"""
        url = "https://my.ntu.edu.tw/attend/ssi.aspx"
        self.session.headers.update(
            {
                "Host": "my.ntu.edu.tw",
                "Referer": "https://web2.cc.ntu.edu.tw/p/s/login2/p1.php",
            }
        )
        response = self.session.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        btn_div = soup.find("div", class_="jumbotron mid bc jumbotronfix")
        if not btn_div:
            return False

        buttons = btn_div.find_all("a")
        return len(buttons) == 2 and buttons[0].get("id") == "btSign" and buttons[1].get("id") == "btSign2"

    def sign(self, action: Literal["signin", "signout"]) -> dict:
        """Perform sign in/out action"""
        if action == "signin":
            return self.signin()
        return self.signout()

    def signin(self) -> dict:
        """Sign in action"""
        url = "https://my.ntu.edu.tw/attend/ajax/signInR2.ashx"
        self.session.headers.update(
            {
                "Host": "my.ntu.edu.tw",
                "Origin": "https://my.ntu.edu.tw",
                "Referer": "https://my.ntu.edu.tw/attend/ssi.aspx",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        data = {"type": 6, "otA": 0, "t": 1}
        response = self.session.post(url, data=data)
        response.raise_for_status()
        return json.loads(response.text.strip())[0]

    def signout(self) -> dict:
        """Sign out action"""
        url = "https://my.ntu.edu.tw/attend/ajax/signInR2.ashx"
        self.session.headers.update(
            {
                "Host": "my.ntu.edu.tw",
                "Origin": "https://my.ntu.edu.tw",
                "Referer": "https://my.ntu.edu.tw/attend/ssi.aspx",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        data = {"type": 6, "otA": 0, "t": 2}
        response = self.session.post(url, data=data)
        response.raise_for_status()
        response_dict = json.loads(response.text.strip())[0]

        if response_dict["t"] == 1 or "申請加班" not in response_dict["msg"]:
            return response_dict

        data = {"type": 6, "otA": 1, "t": 2}
        response = self.session.post(url, data=data)
        response.raise_for_status()
        return json.loads(response.text.strip())[0]

    def _get_sign_records(self) -> dict:
        url = "https://my.ntu.edu.tw/attend/ajax/signInR2.ashx"
        self.session.headers.update(
            {
                "Host": "my.ntu.edu.tw",
                "Origin": "https://my.ntu.edu.tw",
                "Referer": "https://my.ntu.edu.tw/attend/ssi.aspx",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        data = {"type": 4, "day": 7}
        response = self.session.post(url, data=data)
        response.raise_for_status()

        return response.json()

    def check_signin(self, date: str) -> bool:
        """Check if the sign-in record exists for today
        Args:
            records (list[dict]): List of sign-in records.
                                  e.g. {"signdate":"2025-04-18","startdate":"08:52:52","enddate":"18:06:51"}]
        """
        records = self._get_sign_records()
        for record in records:
            if record["signdate"] == date and re.match(r"08:\d{2}:\d{2}", record["startdate"]):
                return True
        return False

    def check_signout(self, date: str) -> dict:
        """Check if the sign-out record exists for today
        Args:
            records (list[dict]): List of sign-in records.
                                  e.g. {"signdate":"2025-04-18","startdate":"08:52:52","enddate":"18:06:51"}]
        """
        records = self._get_sign_records()
        for record in records:
            if record["signdate"] == date and re.match(r"(17|18|19|20|21):\d{2}:\d{2}", record["enddate"]):
                return True
        return False

    def close(self) -> None:
        """Close HTTP session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
