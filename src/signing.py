import sched
from datetime import datetime, timedelta, timezone
from typing import Literal

from loguru import logger

from src.config import Config
from src.notifier.email_notifier import EmailNotifier
from src.signer.web_signer import WebSigner


def get_tz() -> timezone:
    return timezone(timedelta(hours=8))


def get_dt_now():
    tz = get_tz()
    return datetime.now(tz=tz)


def get_signin_and_signout_times(date: datetime) -> tuple[tuple[datetime, datetime], tuple[datetime, datetime]]:
    """Get random delay time in seconds"""
    a = (date.year * 41 + date.month * 41**2 + date.day * 41**3) % 599
    b = (date.year * 43 + date.month * 43**2 + date.day * 43**3) % 599 + 599
    c = (date.year * 47 + date.month * 47**2 + date.day * 47**3) % 599 + 2396
    d = (date.year * 53 + date.month * 53**2 + date.day * 53**3) % 599 + 3594

    signin_time1 = datetime(date.year, date.month, date.day, 8, 0, 0, tzinfo=get_tz()) + timedelta(seconds=a)
    signin_time2 = datetime(date.year, date.month, date.day, 8, 0, 0, tzinfo=get_tz()) + timedelta(seconds=b)
    signout_time1 = datetime(date.year, date.month, date.day, 17, 0, 0, tzinfo=get_tz()) + timedelta(seconds=c)
    signout_time2 = datetime(date.year, date.month, date.day, 17, 0, 0, tzinfo=get_tz()) + timedelta(seconds=d)
    return (signin_time1, signin_time2), (signout_time1, signout_time2)


def format_error_message(error_msg: str, response_data: dict) -> str:
    """Format error message with response data to title and content"""
    title = f"[NTU Auto Signing] {error_msg}"
    content = f"NTU Auto Signing failed: {error_msg}\n\n"
    if "d" in response_data:
        content += f"Timestamp: {response_data['d']}\n"
    if "msg" in response_data:
        content += f"System Message: {response_data['msg']}\n"
    content += f"Response: {response_data}"
    return title, content


def sign_once(action: Literal["signin", "signout"], config: Config) -> None:
    notifier = EmailNotifier(config.mail)
    with WebSigner(config.user) as signer:
        _sign_once(signer, notifier, action)


def _sign_once(signer: WebSigner, notifier: EmailNotifier, action: Literal["signin", "signout"]) -> dict:
    class UnknownError(Exception): ...

    try:
        signer.login_myntu()

        if not signer.check_login_success_on_attend_page():
            msg = "Login failed: check username/password"
            raise ValueError(msg)

        result = signer.sign(action)
        logger.info(result)

        if result.get("t") != 1:
            error_msg = result.get("msg", "Unknown error")
            raise UnknownError(error_msg)

        logger.info(f"Sign {action} success: {result}")
        notifier.send_message(f"[NTU Auto Signing] Sign {action} success", str(result))

    except UnknownError as e:
        logger.error(f"Error: {e}")
        title, content = format_error_message(str(e), result)
        notifier.send_message(title, content)

    except Exception as e:
        error_data = {"t": -1, "msg": str(e)}
        logger.error(f"Error: {e}")
        title, content = format_error_message(str(e), error_data)
        notifier.send_message(title, content)


def schedule_week_sign_actions(scheduler: sched.scheduler, config: Config) -> None:
    """Schedule sign-in and sign-out actions for weekdays in the next 7 days"""
    current_dt = get_dt_now()

    logging_string: str = ""
    # Schedule for next 7 days, but only weekdays
    for day_offset in range(7):
        day_dt = current_dt + timedelta(days=day_offset)
        # 0-4 are Monday-Friday
        if day_dt.weekday() < 5:  # noqa: PLR2004
            signin_times, signout_times = get_signin_and_signout_times(day_dt)

            # Only schedule future events
            for signin_time in signin_times:
                if signin_time > current_dt:
                    scheduler.enterabs(
                        signin_time.timestamp(),
                        1,
                        sign_once,
                        argument=("signin", config),
                    )
                    logging_string += f"Sign in scheduled at {signin_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            for signout_time in signout_times:
                if signout_time > current_dt:
                    scheduler.enterabs(
                        signout_time.timestamp(),
                        1,
                        sign_once,
                        argument=("signout", config),
                    )
                    logging_string += f"Sign out scheduled at {signout_time.strftime('%Y-%m-%d %H:%M:%S')}\n"

    logger.info("Scheduled sign-in/out actions:\n" + logging_string)
    EmailNotifier(config.mail).send_message("[NTU Auto Signing] Scheduled Sign-in/out", logging_string)


def check(config: Config) -> None:
    """Check sign-in from 0 to 17 / sign-out from 17 to 24 and send email notification"""
    notifier = EmailNotifier(config.mail)

    now = get_dt_now()
    today_str = now.strftime("%Y-%m-%d")

    with WebSigner(config.user) as signer:
        try:
            signer.login_myntu()

            if not signer.check_login_success_on_attend_page():
                msg = "Login failed: check username/password"
                raise ValueError(msg)

            if now.hour < 17:
                action = "signin"
                have_signed = signer.check_signin(today_str)
            else:
                action = "signout"
                have_signed = signer.check_signout(today_str)

            if have_signed:
                logger.info(f"Check {action} success")
                # notifier.send_message(f"[NTU Auto Signing] Check {action} success", "")
            else:
                logger.error(f"Check {action} failed")
                notifier.send_message("[NTU Auto Signing] 出事啦 阿伯", "")

        except Exception as e:
            error_data = {"t": -1, "msg": str(e)}
            logger.error(f"Error: {e}")
            title, content = format_error_message(str(e), error_data)
            notifier.send_message(title, content)
