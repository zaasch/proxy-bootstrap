#!/usr/bin/env python3

import json

from zaas.register import ZaaSRegister
from zaas.logger import Logger
from zaas.config import config

from pathlib import Path


logger = Logger(config.LOGFILE)


def main():

    # Perform registration
    register = ZaaSRegister(logger)
    register.register()

    # Get GitHub token
    token = register.get_github_token()
    if token:
        logger.log_json("Successfully retrieved GitHub token")
    else:
        logger.fail("Failed to retrieve GitHub token")

    # Store token
    if token:
        with open(Path(config.CONFIG_DIR) / Path(config.GITHUB_TOKEN_FILE), "w", encoding="utf-8") as f:
            json.dump(token, f)
        logger.log_json(f"Successfully stored GitHub token")
    else:
        logger.fail("Failed to retrieve GitHub token")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.fail("Interrupted by user", code=130)
