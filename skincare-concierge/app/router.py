from agents.orchestrator_agent import OrchestratorAgent
from fastapi import APIRouter, Request

router = APIRouter()

# Assume orchestrator is instantiated elsewhere and imported
orchestrator: OrchestratorAgent = None

@router.post("/run")
async def run_orchestrator(request: Request):
    user_input = await request.json()
    result = orchestrator.handle(user_input)
    return result
