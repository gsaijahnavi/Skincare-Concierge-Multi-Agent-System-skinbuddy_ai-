import os
from agents.orchestrator_agent import OrchestratorAgent
from agents.intake_agent import IntakeAgent
from agents.routine_agent import RoutineAgent
from agents.compatibility_agent import CompatibilityAgent
from agents.evidence_rag_agent import EvidenceRAGAgent
from agents.calendar_agent import CalendarAgent
from tools.evidence_search_tool import EvidenceSearchTool
from tools.ingredient_tool import IngredientTool
from tools.calendar_tool import CalendarTool
import pandas as pd
import json

# Gemini API authentication (for Google Cloud Gemini)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", None)
if GOOGLE_API_KEY:
    print("✅ GOOGLE_API_KEY loaded from environment.")
else:
    raise RuntimeError("🔑 GOOGLE_API_KEY not set. Please set it in your environment before running.")

# Gemini API usage example (requires google-generativeai)
# pip install google-generativeai
import google.generativeai as genai

genai.configure(api_key=GOOGLE_API_KEY)

def gemini_summarize(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text

# Load data
with open('data/user_profile_template.json') as f:
    user_profile = json.load(f)
evidence_data = pd.read_csv('data/evidence.csv').to_dict(orient='records')
ingredient_data = pd.read_csv('data/ingredient_safety.csv').to_dict(orient='records')

# Instantiate tools
calendar_tool = CalendarTool()
evidence_tool = EvidenceSearchTool(evidence_data)
ingredient_tool = IngredientTool(ingredient_data)

# Instantiate agents
intake_agent = IntakeAgent()
routine_agent = RoutineAgent()
compatibility_agent = CompatibilityAgent(ingredient_tool)
evidence_rag_agent = EvidenceRAGAgent(evidence_tool)
calendar_agent = CalendarAgent(calendar_tool)

# Orchestrator
orchestrator = OrchestratorAgent(
    intake_agent,
    routine_agent,
    compatibility_agent,
    evidence_rag_agent,
    calendar_agent
)

def run():
    # Example input
    user_input = user_profile.copy()
    user_input['products'] = [
        {"id": 2, "name": "Retinoid Serum", "ingredients": ["Retinoid", "Squalane"]},
        {"id": 3, "name": "Daily SPF", "ingredients": ["SPF", "Niacinamide"]}
    ]
    user_input['question'] = "What is the benefit of niacinamide?"
    result = orchestrator.handle(user_input)
    print(result)

if __name__ == "__main__":
    run()
