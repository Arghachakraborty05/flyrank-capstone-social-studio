from fastapi import FastAPI
from app.database import Base, engine
from app.routers import posts, variants

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Social Media Studio")
app.include_router(posts.router)
app.include_router(variants.router)