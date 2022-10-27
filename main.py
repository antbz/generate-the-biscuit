from fastapi import FastAPI

from generate_biscuit import *

app = FastAPI()

@app.get("/generate")
async def generate():
    return generate_the_biscuits()