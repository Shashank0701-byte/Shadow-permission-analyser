from fastapi import FastAPI
from app.graph.queries import find_escalation_paths
from app.api.graph_routes import router as graph_router

app = FastAPI()

app.include_router(graph_router)
@app.get("/")
def home():
    return {"status": "Shadow Permission Analyzer running"}


@app.get("/escalation/{user}")
def escalation(user: str):
    paths = find_escalation_paths(user)
    return {"paths": str(paths)}