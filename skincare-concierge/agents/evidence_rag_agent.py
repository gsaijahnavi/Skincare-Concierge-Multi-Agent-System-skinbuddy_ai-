"""
EvidenceRAGAgent
Uses:
- Excel evidence search MCP tool
- Gemini 2.5 Flash Lite for JSON summarization
"""

import json
from typing import Any, Dict, Optional

from pydantic import Field

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool, ToolContext

# NEW SDK imports
from google import genai
from google.genai import types


class EvidenceRAGAgent(LlmAgent):
    """
    Evidence → RAG → Strict JSON summary agent.

    This agent:
    1) Extracts ingredient from user query
    2) Calls EvidenceSearchTool (Excel RAG)
    3) Summarizes extracted evidence into strict JSON using Gemini
    """

    # Pydantic-safe custom fields
    evidence_tool: Optional[AgentTool] = Field(default=None, exclude=True)

    # NEW — private fields allowed by Pydantic
    client: Any = Field(default=None, exclude=True)
    model_name: str = Field(default="gemini-2.5-flash-lite", exclude=True)

    def __init__(self, tool: AgentTool):
        # Underlying ADK model for compatibility
        model = Gemini(model="gemini-2.5-flash-lite")

        super().__init__(
            name="evidence_rag_agent",
            model=model,
            description="Retrieves and summarizes scientific skincare evidence.",
            evidence_tool=tool,
            client=None,                      # filled below
            model_name="gemini-2.5-flash-lite"
        )

        # Bypass pydantic validation using raw setattr
        object.__setattr__(self, "client", genai.Client())

    # ----------------------------------------------------------------------
    # Intent Extraction
    # ----------------------------------------------------------------------

    def extract_intent(self, user_input: Any) -> Dict[str, str]:
        text = str(user_input).lower()

        INGREDIENTS = [
            "niacinamide", "azelaic acid", "salicylic acid", "tretinoin",
            "retinol", "vitamin c", "ascorbic acid", "glycolic acid",
            "lactic acid", "ceramides", "panthenol", "hyaluronic acid",
            "arbutin", "kojic acid", "tranexamic acid"
        ]

        found = next((i for i in INGREDIENTS if i in text), "")

        return {
            "ingredient": found,
            "question": text.strip()
        }

    # ----------------------------------------------------------------------
    # Main RUN (called by orchestrator)
    # ----------------------------------------------------------------------

    def run(self, user_input: Any, context: ToolContext = None) -> Dict:
        """
        Synchronous method for orchestrator.
        Returns a JSON dict.
        """

        intent = self.extract_intent(user_input)
        ingredient = intent["ingredient"]
        question = intent["question"]

        # No ingredient found
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

        # ------------------------------------------------------------------
        # 1) Call EvidenceSearchTool
        # ------------------------------------------------------------------
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
        evidence_text = "\n".join([c.get("snippet", "") for c in chunks])

        # ------------------------------------------------------------------
        # 2) Build strict JSON summarization prompt
        # ------------------------------------------------------------------

        prompt = (
            "You are an evidence summarization engine. "
            "You MUST respond with STRICT JSON ONLY. "
            "NO text before or after the JSON. NO commentary.\n\n"
            "JSON Schema:\n"
            "{\n"
            '  \"summary\": \"<string>\",\n'
            '  \"strength\": \"<strong|moderate|weak>\",\n'
            '  \"sources\": [ {\"title\": \"\", \"url\": \"\", \"snippet\": \"\"} ],\n'
            '  \"tags\": [\"\" ]\n'
            "}\n\n"
            "Use ONLY the following evidence:\n"
            f"{evidence_text}\n"
        )

        # ------------------------------------------------------------------
        # 3) Call Gemini using new SDK
        # ------------------------------------------------------------------

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=800,
            ),
        )

        raw = response.text or ""

        # ------------------------------------------------------------------
        # 4) Parse JSON robustly
        # ------------------------------------------------------------------

        try:
            parsed = json.loads(raw)
        except Exception:
            # Attempt to extract JSON substring
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(raw[start:end+1])
            else:
                raise RuntimeError(
                    f"Gemini returned non-JSON output:\n{raw}"
                )

        # ------------------------------------------------------------------
        # 5) Return normalized structure
        # ------------------------------------------------------------------

        return {
            "ingredient": ingredient,
            "question": question,
            "summary": parsed.get("summary"),
            "strength": parsed.get("strength"),
            "sources": parsed.get("sources", []),
            "tags": parsed.get("tags", []),
        }
