#!/bin/sh
uvicorn signingserver.main:app --port 8080 --host 0.0.0.0 --log-config log.json