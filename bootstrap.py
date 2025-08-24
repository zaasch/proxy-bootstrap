#!/usr/bin/env python3

from zaas.bootstrap import ZaaSBootstrap
from zaas.logger import Logger
from zaas.config import config


logger = Logger(config.LOGFILE)


def main():
    bootstrap = ZaaSBootstrap(logger)
    bootstrap.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.fail("Interrupted by user", code=130)
