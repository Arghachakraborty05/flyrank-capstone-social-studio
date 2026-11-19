from fastapi import FastAPI
from app.database import Base, engine
from app.routers import posts

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Social Media Studio")
app.include_router(posts.router)