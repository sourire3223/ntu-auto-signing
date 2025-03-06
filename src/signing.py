import sched
from datetime import datetime, timedelta, timezone
from typing import Literal

from loguru import logger

from src.config import Config
from src.notifier.email_notifier import EmailNotifier
from src.singer.web_signer import WebSigner


def get_tz() -> timezone:
    return timezone(timedelta(hours=8))


def get_dt_now():
    tz = get_tz()
    return datetime.now(tz=tz)


def get_signin_and_signout_time(date: datetime) -> tuple[datetime, datetime]:
    """Get random delay time in seconds"""
    delay1 = (date.year * 41 + date.month * 41**2 + date.day * 41**3) % 1777
    delay2 = (date.year * 43 + date.month * 43**2 + date.day * 43**3) % 2999
    if delay1 > delay2:
        delay1, delay2 = delay2, delay1

    signin_time = datetime(date.year, date.month, date.day, 8, 0, 0, tzinfo=get_tz()) + timedelta(seconds=delay1)
    signout_time = datetime(date.year, date.month, date.day, 17, 0, 0, tzinfo=get_tz()) + timedelta(seconds=delay2)
    return signin_time, signout_time


def sign_once(action: Literal["signin", "signout"], config: Config) -> None:
    with WebSigner(config) as signer, EmailNotifier(config.mail) as notifier:
        _sign_once(signer, notifier, action)


def _sign_once(signer: WebSigner, notifier: EmailNotifier, action: Literal["signin", "signout"]) -> dict:
    class UnknownError(Exception): ...

    try:
        signer.login()

        if not signer.verify_login():
            msg = "Login failed: check username/password"
            raise ValueError(msg)

        result = signer.sign(action)
        logger.info(result)

        if result.get("t") != 1:
            error_msg = result.get("msg", "Unknown error")
            raise UnknownError(error_msg)

        logger.info(f"Sign {action} success: {result}")
        notifier.send_message(f"[NTU Auto Signing] Sign {action} success", str(result))

    except ValueError as e:
        logger.error(f"Error: {e}")
        notifier.send_error_message(f"[NTU Auto Signing] {error_msg}", result)

    except Exception as e:
        error_data = {"t": -1, "msg": str(e)}
        logger.error(f"Error: {e}")
        notifier.send_error_message(f"[NTU Auto Signing] {e}", error_data)


def schedule_week_sign_actions(scheduler: sched.scheduler, config: Config) -> None:
    """Schedule sign-in and sign-out actions for weekdays in the next 7 days"""
    current_dt = get_dt_now()

    logging_string: str = ""
    # Schedule for next 7 days, but only weekdays
    for day_offset in range(7):
        day_dt = current_dt + timedelta(days=day_offset)
        # 0-4 are Monday-Friday
        if day_dt.weekday() < 5:  # noqa: PLR2004
            signin_time, signout_time = get_signin_and_signout_time(day_dt)

            # Only schedule future events
            if signin_time > current_dt:
                scheduler.enterabs(
                    signin_time.timestamp(),
                    1,
                    sign_once,
                    argument=("signin", config),
                )
                logging_string += f"Sign in scheduled at {signin_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            if signout_time > current_dt:
                scheduler.enterabs(
                    signout_time.timestamp(),
                    1,
                    sign_once,
                    argument=("signout", config),
                )
                logging_string += f"Sign out scheduled at {signout_time.strftime('%Y-%m-%d %H:%M:%S')}\n"

    logger.info(logging_string)
    EmailNotifier(config.mail).send_message("[NTU Auto Signing] Scheduled Sign-in/out", logging_string)
