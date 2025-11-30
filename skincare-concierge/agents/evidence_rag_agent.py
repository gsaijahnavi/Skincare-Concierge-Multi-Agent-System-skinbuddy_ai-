"""
EvidenceRAGAgent with gemini-2.5-flash-lite (recommended free/cheap model)
"""
import json
from typing import Any, Dict, Optional
from pydantic import Field

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool, ToolContext


class EvidenceRAGAgent(LlmAgent):

    # Declare custom fields BEFORE __init__
    evidence_tool: Optional[AgentTool] = Field(default=None, exclude=True)

    def __init__(self, tool: AgentTool):
        model = Gemini(model="gemini-2.5-flash-lite")

        super().__init__(
            name="evidence_rag_agent",
            model=model,
            description="Retrieves scientific skincare evidence using MCP tool.",
            evidence_tool=tool
        )

    def extract_intent(self, user_input: Any) -> Dict[str, str]:
        text = str(user_input).lower()

        INGREDIENTS = [
            "niacinamide", "azelaic acid", "salicylic acid", "tretinoin",
            "retinol", "vitamin c", "ascorbic acid", "glycolic acid",
            "lactic acid", "ceramides", "panthenol", "hyaluronic acid",
            "arbutin", "kojic acid", "tranexamic acid"
        ]

        found = next((i for i in INGREDIENTS if i in text), "")
        return {"ingredient": found, "question": text.strip()}



    def run(self, user_input: Any, context: ToolContext = None) -> Dict:
        intent = self.extract_intent(user_input)
        ingredient = intent["ingredient"]
        question = intent["question"]

        if not ingredient:
            return {
                "ingredient": None,
                "question": question,
                "summary": None,
                "strength": "none",
                "sources": [],
                "tags": [],
                "error": "NO_INGREDIENT_FOUND"
            }

        # Call EvidenceSearchTool
        result = self.evidence_tool.run(context, query=question, ingredient=ingredient)

        if not result or not result.get("chunks"):
            return {
                "ingredient": ingredient,
                "question": question,
                "summary": "No evidence found.",
                "strength": "weak",
                "sources": [],
                "tags": []
            }

        chunks = result["chunks"]

        # Extract text
        evidence_text = "\n".join([c["snippet"] for c in chunks])

        # ⭐ STRONG ENFORCEMENT — JSON ONLY
        prompt = (
            "You are an evidence summarization engine. "
            "You MUST respond with STRICT JSON ONLY. "
            "No chit-chat. No conversational responses. "
            "Do NOT ask questions. Do NOT explain steps. "
            "Do NOT include any text before or after JSON.\n\n"
            "JSON Schema:\n"
            "{\n"
            '  "summary": "<string>",\n'
            '  "strength": "<strong|moderate|weak>",\n'
            '  "sources": [ {"title": "", "url": "", "snippet": ""} ],\n'
            '  "tags": [""]\n'
            "}\n\n"
            "Use ONLY this evidence:\n"
            f"{evidence_text}\n"
        )

        raw_response = self.model.predict(prompt)

        # Attempt to load JSON
        try:
            parsed = json.loads(raw_response)
        except:
            cleaned = raw_response[ raw_response.find("{") : raw_response.rfind("}") + 1 ]
            parsed = json.loads(cleaned)

        # ALWAYS return the same structure
        return {
            "ingredient": ingredient,
            "question": question,
            "summary": parsed.get("summary"),
            "strength": parsed.get("strength"),
            "sources": parsed.get("sources", []),
            "tags": parsed.get("tags", []),
        }
