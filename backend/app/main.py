from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.graph_routes import router as graph_router

app = FastAPI()

# CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ROUTERS
app.include_router(graph_router)