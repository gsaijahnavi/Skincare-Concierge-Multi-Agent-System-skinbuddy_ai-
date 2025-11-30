# agents/product_lookup_agent.py

import json
from typing import Dict, Any, List, Optional

from google import genai
from google.genai import types

from tools.product_lookup_tool import ProductLookupTool


class ProductLookupAgent:
    """
    ProductLookupAgent (no ADK / LlmAgent inheritance):

    - Input:
        user_question: str
        user_profile: dict (optional)

    - Behavior:
        1) Ask Gemini (gemini-2.5-flash-lite) which columns & patterns to search
           (STRICTLY from: product_name, product_url, product_type, ingredients, price)
        2) Use ProductLookupTool.search_products(...) to fetch matching items
        3) Return a dict:

           {
             "question": str,
             "products": [
               {
                 "product_name": str,
                 "product_url": str,
                 "reason": str
               },
               ...
             ],
             "reason": str
           }
    """

    def __init__(
        self,
        product_tool: ProductLookupTool,
        model_name: str = "gemini-2.5-flash-lite",
    ):
        self.product_tool = product_tool
        self.model_name = model_name

        # Relies on GEMINI_API_KEY in env (or other genai config)
        self.client = genai.Client()

        # Lock allowed columns to your schema
        self.allowed_columns = [
            "product_name",
            "product_url",
            "product_type",
            "ingredients",
            "price",
        ]

    # ---------- Prompt builder ----------

    def _build_prompt(
        self,
        question: str,
        user_profile: Optional[Dict[str, Any]],
    ) -> str:
        """
        Build a prompt to get:
        - columns_to_search
        - patterns per column
        - reason

        Strictly constrained to allowed_columns.
        """

        profile_json = json.dumps(user_profile or {}, ensure_ascii=False)

        return f"""
You are a product-catalog search planner for a skincare recommendation system.

The ONLY available product catalog columns are:

- "product_name"   (string: the human-readable name of the product)
- "product_url"    (string: link to the product page)
- "product_type"   (string: high-level category, e.g. "cleanser", "exfoliant", "serum", "moisturizer", "sunscreen")
- "ingredients"    (string: ingredients list or key actives)
- "price"          (string: price or price range)

User question:
{question}

User profile (JSON):
{profile_json}

Your task:
1. Decide which columns are most relevant to search, using ONLY the 5 allowed columns.
2. Decide what text patterns to look for within each of those columns.
3. THINK carefully about product_type semantics:
   - If the user asks explicitly for "exfoliants", your patterns for "product_type"
     should include "exfoliant" and should NOT match unrelated types like "cleanser"
     or "moisturizer", unless the question explicitly allows that.
   - Similarly for "cleanser", "serum", "moisturizer", "sunscreen", etc.

You MUST respond with STRICT JSON ONLY in this exact schema:

{{
  "columns_to_search": ["product_type", "ingredients"],
  "patterns": {{
    "product_type": ["exfoliant"],
    "ingredients": ["bha", "aha", "salicylic", "glycolic"]
  }},
  "reason": "Short 1–2 sentence explanation of why these columns and patterns were chosen."
}}

Rules:
- columns_to_search MUST be a subset of:
  ["product_name", "product_url", "product_type", "ingredients", "price"]
- Do NOT invent or mention any other column names.
- Use lowercase patterns where possible (e.g. "acne", "oily skin", "exfoliant").
- Do NOT include any text before or after the JSON.
"""

    # ---------- LLM call for search plan ----------

    def _call_llm_for_search_plan(
        self,
        question: str,
        user_profile: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Call Gemini to decide:
        - columns_to_search
        - patterns per column
        - reason

        Enforces:
        - columns_to_search subset of allowed_columns
        - Fallback defaults if parsing fails
        """

        prompt = self._build_prompt(question, user_profile)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=512,
            ),
        )

        raw_text = response.text or ""

        # Try to parse JSON strictly
        try:
            parsed = json.loads(raw_text)
        except Exception:
            # Fallback: try to salvage JSON substring
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1:
                try:
                    parsed = json.loads(raw_text[start : end + 1])
                except Exception:
                    parsed = {}
            else:
                parsed = {}

        if not isinstance(parsed, dict):
            parsed = {}

        # Extract with fallbacks
        columns_to_search = parsed.get("columns_to_search") or []
        patterns = parsed.get("patterns") or {}
        reason = parsed.get("reason") or "Heuristic column selection fallback."

        # Enforce allowed columns
        columns_to_search = [
            c for c in columns_to_search
            if isinstance(c, str) and c in self.allowed_columns
        ]

        # If LLM failed to produce useful columns, fallback sensibly
        if not columns_to_search:
            columns_to_search = ["product_type", "ingredients"]

        # Ensure patterns is a dict of lists and only for allowed columns
        clean_patterns: Dict[str, List[str]] = {}
        if isinstance(patterns, dict):
            for col, pat_list in patterns.items():
                if col in self.allowed_columns and isinstance(pat_list, list):
                    clean_patterns[col] = [str(p) for p in pat_list if str(p).strip()]

        # If nothing usable, derive simple patterns from question
        if not clean_patterns:
            base_words = [
                w.strip().lower()
                for w in question.split()
                if len(w.strip()) > 2
            ]
            base_words = list(set(base_words))
            clean_patterns = {col: base_words for col in columns_to_search}

        return {
            "columns_to_search": columns_to_search,
            "patterns": clean_patterns,
            "reason": reason,
        }

    # ---------- Public API ----------

    def run(
        self,
        user_question: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point.

        Returns a JSON-serializable dict:

        {
          "question": str,
          "products": [
             {"product_name": str, "product_url": str, "reason": str},
             ...
          ],
          "reason": str
        }
        """
        # 1) Ask LLM for search configuration
        plan = self._call_llm_for_search_plan(user_question, user_profile)

        columns_to_search = plan["columns_to_search"]
        patterns = plan["patterns"]
        reason = plan["reason"]

        # 2) Search with the tool
        matching_products = self.product_tool.search_products(
            columns_to_search=columns_to_search,
            patterns=patterns,
        )

        # 3) Format final output
        products_out: List[Dict[str, Any]] = []
        for p in matching_products:
            products_out.append(
                {
                    "product_name": p.get("product_name"),
                    "product_url": p.get("product_url"),
                    "reason": reason,
                }
            )

        return {
            "question": user_question,
            "products": products_out,
            "reason": reason,
        }
