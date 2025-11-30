from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
import asyncio

# ----------------------------
# IMPORT YOUR AGENTS + TOOLS
# ----------------------------
from agents.orchestrator_agent import OrchestratorAgent

from tools.profile_tool import ProfileDBTool
from tools.evidence_search_tool import EvidenceSearchTool
from tools.product_lookup_tool import ProductLookupTool
from tools.calendar_tool import CalendarTool
from tools.reminder_store import ReminderStore

from agents.intake_agent import IntakeAgent
from agents.safety_agent import SafetyAgent
from agents.evidence_rag_agent import EvidenceRAGAgent
from agents.product_lookup_agent import ProductLookupAgent
from agents.routine_agent import RoutineAgent
from agents.calendar_agent import CalendarAgent


# ----------------------------
# INITIALIZE AGENTS + MEMORY
# ----------------------------
profile_tool = ProfileDBTool()
evidence_tool = EvidenceSearchTool("data/evidence.xlsx")
product_tool = ProductLookupTool()
calendar_tool = CalendarTool()
reminder_store = ReminderStore()

intake_agent = IntakeAgent(profile_tool)
safety_agent = SafetyAgent()
evidence_agent = EvidenceRAGAgent(tool=evidence_tool)
product_agent = ProductLookupAgent(product_tool)
routine_agent = RoutineAgent(product_tool)
calendar_agent = CalendarAgent(reminder_store, calendar_tool)

orchestrator = OrchestratorAgent(
    intake_agent,
    safety_agent,
    evidence_agent,
    product_agent,
    routine_agent,
    calendar_agent,
)

conversation_memory = {}   # {user_id: [ {role,message}, ... ]}


# ----------------------------
# FASTAPI APP
# ----------------------------
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


# ----------------------------
# HOMEPAGE UI
# ----------------------------
@app.get("/")
def home():
    return HTMLResponse(open("static/index.html").read())


# ----------------------------
# WEBSOCKET FOR LIVE CHAT
# ----------------------------
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):

    await websocket.accept()

    if user_id not in conversation_memory:
        conversation_memory[user_id] = []

    try:
        while True:
            message = await websocket.receive_text()

            # memory append (user)
            conversation_memory[user_id].append({"role": "user", "message": message})

            result = await orchestrator.run(user_id, message)

            final_reply = json.dumps(result, indent=2)

            # memory append (assistant)
            conversation_memory[user_id].append({"role": "assistant", "message": final_reply})

            await websocket.send_text(final_reply)

    except WebSocketDisconnect:
        print(f"User {user_id} disconnected.")


# ----------------------------
# SIMPLE HEALTH CHECK
# ----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}
