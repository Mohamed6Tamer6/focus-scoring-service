# main.py
from fastapi import FastAPI
from app.database import Base, engine
from app.api.routes import auth_router
import app.models.user
import app.models.refresh_token

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "Focus Detection API"}
    
