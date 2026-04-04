#!/usr/bin/env bash
python -c 'import time, jwt; print(jwt.encode({"sub":"starlord","iss":"cmu.edu","exp": int(time.time()) + 86400}, "dummy-secret-at-least-32-bytes-long!!", algorithm="HS256"))'
