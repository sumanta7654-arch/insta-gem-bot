from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from app.api.webhook import router as webhook_router

app = FastAPI()

app.include_router(webhook_router)
