import json
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
        self.session.headers.update({
            "Host": "my.ntu.edu.tw",
            "Referer": "https://my.ntu.edu.tw/attend/ssi.aspx"
        })
        response = self.session.get("https://my.ntu.edu.tw/attend/ssi.aspx?type=login",
                                    allow_redirects=False)
        response.raise_for_status()

        # Step 2: Follow first redirect to NTU portal
        redirect_url = urljoin(self.BASE_URL, response.headers["Location"])
        response = self.session.get(redirect_url, allow_redirects=False)
        response.raise_for_status()

        # Step 3: Follow redirect to login page
        redirect_url = response.headers["Location"]
        self.session.headers.update({
            "Host": "web2.cc.ntu.edu.tw",
            "Referer": "https://my.ntu.edu.tw/attend/ssi.aspx"
        })
        self.session.get(redirect_url, allow_redirects=False).raise_for_status()

        # Step 4: Submit login credentials
        self.session.headers.update({
            "Host": "web2.cc.ntu.edu.tw",
            "Origin": "https://web2.cc.ntu.edu.tw",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://web2.cc.ntu.edu.tw/p/s/login2/p1.php"
        })
        login_data = {
            "user": self.config.username,
            "pass": self.config.password,
            "Submit": "登入"
        }
        response = self.session.post(
            "https://web2.cc.ntu.edu.tw/p/s/login2/p1.php",
            data=login_data,
            allow_redirects=False
        )
        response.raise_for_status()

        # Step 5: Follow redirect back to portal
        redirect_url = response.headers["Location"]
        self.session.headers.update({
            "Host": "my.ntu.edu.tw"
        })
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

        action_map = {"signin": 1, "signout": 2}
        if action not in action_map:
            raise ValueError(f"Unknown action: {action}")

        data = {"type": 6, "otA": 0, "t": action_map[action]}
        response = self.session.post(url, data=data)
        response.raise_for_status()
        return json.loads(response.text.strip())[0]

    def close(self) -> None:
        """Close HTTP session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
