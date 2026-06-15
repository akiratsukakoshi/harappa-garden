"""共通ユーティリティ (HMC modules/utils.py から logger 部分を移植)"""

import logging
import os
import sys


def setup_logger(name=__name__):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger


def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
