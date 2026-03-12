# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.api.routes import auth_router, focus_router
import app.models.user
import app.models.refresh_token
import app.models.focus_session
import app.models.rbac  
from app.api.routes.rbac import router as rbac_router  

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Focus Scoring Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(focus_router)
app.include_router(rbac_router)

@app.get("/")
def root():
    return {"message": "Focus Detection API"}