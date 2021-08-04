import asyncio
import os

import yaml

from fastapi import FastAPI, HTTPException, Header

from signingserver.signer import SigningServer
from signingserver.verifier import verify_request
from signingserver.model import SignedHash

from signingserver.log import debug_message, debug_failure


loop = asyncio.get_event_loop()
app = FastAPI()
updater = None


def get_config():
    configfile = os.environ.get("CONFIG", "config.yaml")
    debug_message("Loading config from: " + configfile)
    with open(configfile, "rt") as fh:
        data = yaml.load(fh.read(), Loader=yaml.SafeLoader)

    if os.environ.get("DOMAIN_OVERRIDE"):
        data["config"]["domain"] = os.environ.get("DOMAIN_OVERRIDE")

    if os.environ.get("PORT_OVERRIDE"):
        data["config"]["port"] = int(os.environ.get("PORT_OVERRIDE"))

    return data["config"]


@app.on_event("startup")
async def startup_event():
    global updater
    debug_message("Startup begin...")
    updater = SigningServer(**get_config())
    task = loop.create_task(updater.renew_loop(loop))


@app.post("/sign/{data}", response_model=SignedHash)
async def sign_data(data, authorization: str = Header(None)):
    debug_message("Signing Request...")
    if not updater.validate_token(authorization):
        debug_failure("Invalid Auth Token")
        raise HTTPException(status_code=403, detail="Invalid auth token")

    return updater.sign_request(data)


@app.post("/verify")
async def verify_data(signed_req: SignedHash):
    debug_message("Verifying Signed Request...")
    result = await loop.run_in_executor(None, verify_request, signed_req)
    if result:
        return result

    raise HTTPException(status_code=400, detail="Not verified")