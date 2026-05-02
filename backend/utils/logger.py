import logging
import sys

from utils.singleton import Singleton


@Singleton
class Logger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)

            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))

            self.logger.addHandler(handler)

    def __getattr__(self, attr):
        return getattr(self.logger, attr)
