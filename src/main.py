import argparse
import sched
import time

from src.config import Config, load_config
from src.signing import schedule_week_sign_actions, sign_once


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="NTU Auto Sign-in/out")
    parser.add_argument("-c", "--config", default="./config.ini", type=str, help="Path to config file")
    parser.add_argument(
        "-a",
        "--action",
        choices=["signin", "signout", "loop"],
        default="loop",
        help="Sign in or sign out action",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config: Config = load_config(args.config)
    scheduler = sched.scheduler(time.time, time.sleep)

    match args.action:
        case "loop":
            while True:
                schedule_week_sign_actions(scheduler, config)
                scheduler.run()
        case _:
            sign_once(args.action, config)


if __name__ == "__main__":
    main()
