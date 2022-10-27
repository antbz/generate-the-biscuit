from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from generate_biscuit import *

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/generate")
async def generate():
    return generate_the_biscuits()
