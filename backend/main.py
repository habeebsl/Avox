from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.clone import clone_router
from routes.ws_audio_ads import ws

app = FastAPI()

app.include_router(clone_router, prefix="/api/clones")
app.include_router(ws, prefix="/ws/ads")

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)