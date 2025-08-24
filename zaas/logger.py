import os
import time
import json
import sys


class Logger:

    logfile: str

    def __init__(self, logfile: str):
        self.logfile = logfile

    def log_json(self, message: str):
        os.makedirs(os.path.dirname(self.logfile), exist_ok=True)
        fd = os.open(self.logfile, os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", buffering=1) as f:
            rec = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "message": message,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(message)

    def fail(self, msg: str, code: int = 1):
        self.log_json(f"ERROR: {msg}")
        sys.exit(code)
