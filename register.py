#!/usr/bin/env python3


from zaas.register import ZaaSRegister
from zaas.logger import Logger
from zaas.config import config


logger = Logger(config.LOGFILE)


def main():
    register = ZaaSRegister(logger)
    register.register()
    token = register.get_github_token()
    print(token)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.fail("Interrupted by user", code=130)
