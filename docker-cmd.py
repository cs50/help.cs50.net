#!/usr/bin/env python3

import os

import lib50


lib50.set_local_path(os.getenv("HELP50_PATH"))
print(lib50.local(os.getenv("HELPERS_SLUG")))
