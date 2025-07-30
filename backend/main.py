import os
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from routes.clone import clone_router
from routes.ws_audio_ads import ws

load_dotenv()

app = FastAPI()

app.include_router(clone_router, prefix="/api/clones")
app.include_router(ws, prefix="/ws/ads")

origins = [
    os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)