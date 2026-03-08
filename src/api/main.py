"""FastAPI application entry point."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import APP_PASSWORD, create_token, verify_token
from .routes import media, people, search

load_dotenv()

app = FastAPI(title="Memories Archive", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(media.router)
app.include_router(people.router)
app.include_router(search.router)


class LoginRequest(BaseModel):
    password: str


@app.post("/api/login")
def login(body: LoginRequest):
    if not APP_PASSWORD:
        raise HTTPException(status_code=500, detail="APP_PASSWORD not configured")
    if body.password != APP_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    return {"token": create_token()}


@app.get("/api/me")
def me(_token: str = Depends(verify_token)):
    return {"ok": True}


# Serve Vue build in production (web/dist must exist)
DIST = Path("web/dist")
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file = DIST / full_path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(DIST / "index.html")
