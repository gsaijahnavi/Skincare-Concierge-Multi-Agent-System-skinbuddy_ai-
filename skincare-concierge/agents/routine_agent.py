# agents/routine_agent.py

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from tools.product_lookup_tool import ProductLookupTool


class RoutineAgent:
    """
    RoutineAgent

    - Takes a user question + profile
    - Classifies intent: AM / PM / BOTH / SPOT
    - Builds a skincare routine skeleton (steps)
    - For each step, picks ONE best product from product_catalog.xlsx
    - Returns a JSON-serializable dict with:
        question, user_profile, routine_brief, steps[]
    """

    def __init__(self, product_tool: ProductLookupTool):
        self.product_tool = product_tool

    # ---------- Public API ----------

    def run(self, question: str, user_profile_raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entrypoint.

        :param question: Free-text user request
        :param user_profile_raw: Profile dict with keys like:
            "Name?": "jahnavi",
            "Age?": "32",
            "Skin type (e.g., oily, dry, combination)": "dry",
            "Skin concerns (e.g., acne, sensitivity)": "aging",
            "Current Skincare routine": "no skincare",
            "Budget preference": "medium range"
        """

        profile = self._normalize_profile(user_profile_raw)
        routine_type = self._classify_routine_type(question)

        # Build logical steps (with time + step + category key)
        logical_steps = self._build_steps_for_type(routine_type, profile)

        # Fill each step with exactly ONE product (if available)
        filled_steps: List[Dict[str, Any]] = []
        for step in logical_steps:
            category = step["category"]  # e.g. "cleanser"
            product = self._choose_best_product(category, profile)
            if product:
                filled_steps.append(
                    {
                        "time": step["time"],            # "AM", "PM", "SPOT", "AM/PM"
                        "step": step["step"],            # "Cleanser"
                        "product_name": product.get("product_name"),
                        "product_url": product.get("product_url"),
                        "reason": self._build_reason_for_step(
                            step_name=step["step"],
                            category=category,
                            product=product,
                            profile=profile,
                        ),
                    }
                )

        routine_brief = self._build_routine_brief(
            question=question,
            profile=profile,
            steps=filled_steps,
            routine_type=routine_type,
        )

        return {
            "question": question,
            "user_profile": profile,
            "routine_brief": routine_brief,
            "steps": filled_steps,
        }

    # ---------- Profile Helpers ----------

    def _normalize_profile(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert verbose question-style keys into a clean internal structure.
        """
        name = raw.get("Name?", "").strip()
        age = raw.get("Age?", "").strip()

        skin_type = raw.get(
            "Skin type (e.g., oily, dry, combination)", ""
        ).strip().lower()

        concerns_raw = raw.get(
            "Skin concerns (e.g., acne, sensitivity)", ""
        )
        # allow comma/space separated concerns
        concerns_list = self._split_concerns(concerns_raw)

        current_routine = raw.get("Current Skincare routine", "").strip()
        budget_pref = raw.get("Budget preference", "").strip().lower()

        return {
            "name": name,
            "age": age,
            "skin_type": skin_type,          # e.g. "dry"
            "concerns": concerns_list,       # e.g. ["aging"]
            "current_routine": current_routine,
            "budget_preference": budget_pref # e.g. "medium range"
        }

    def _split_concerns(self, raw: Any) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(c).strip().lower() for c in raw if str(c).strip()]
        text = str(raw).lower()
        # split by comma or "and"
        parts = re.split(r"[,&]| and ", text)
        return [p.strip() for p in parts if p.strip()]

    # ---------- Routine Type + Steps ----------

    def _classify_routine_type(self, question: str) -> str:
        """
        Returns one of: "AM", "PM", "SPOT", "BOTH"
        """
        q = question.lower()

        # Spot / dark spot / spot reduction
        if "spot" in q:
            return "SPOT"

        # AM / morning
        if "am routine" in q or "morning" in q or "daytime" in q:
            return "AM"

        # PM / night
        if "pm routine" in q or "night" in q or "evening" in q or "bedtime" in q:
            return "PM"

        # Generic "based on my profile create a routine"
        if "based on my profile" in q or "routine for me" in q:
            return "BOTH"

        # fallback
        return "BOTH"

    def _build_steps_for_type(
        self,
        routine_type: str,
        profile: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Return a list of dictionaries with fields:
          - time: "AM" | "PM" | "SPOT" | "AM/PM"
          - step: Human label ("Cleanser")
          - category: product_type key ("cleanser")
        """

        steps: List[Dict[str, str]] = []

        # We always include Cleanser + Serum + Moisturizer in routines
        def am_steps():
            s: List[Dict[str, str]] = [
                {"time": "AM", "step": "Cleanser", "category": "cleanser"},
            ]

            # Hydration/repair steps depending on dry/aging skin
            if profile["skin_type"] in ("dry", "normal") or "aging" in profile["concerns"]:
                s.append({"time": "AM", "step": "Toner", "category": "toner"})
                s.append({"time": "AM", "step": "Essence", "category": "essence"})

            s.append({"time": "AM", "step": "Serum", "category": "serum"})
            s.append({"time": "AM", "step": "Moisturizer", "category": "moisturizer"})
            s.append({"time": "AM", "step": "Sunscreen", "category": "sunscreen"})

            # Spot treatment in AM only if strong concern
            if any(c in ("acne", "hyperpigmentation", "dark spots", "melasma")
                   for c in profile["concerns"]):
                s.append({"time": "AM", "step": "Spot treatment", "category": "spot treatment"})
            return s

        def pm_steps():
            s: List[Dict[str, str]] = [
                {"time": "PM", "step": "Cleanser", "category": "cleanser"},
                {"time": "PM", "step": "Toner", "category": "toner"},
                {"time": "PM", "step": "Essence", "category": "essence"},
                {"time": "PM", "step": "Serum", "category": "serum"},
                {"time": "PM", "step": "Moisturizer", "category": "moisturizer"},
            ]

            # Exfoliant: PM only, 2–3x/week (we'll mention that in brief)
            s.append({"time": "PM", "step": "Exfoliant (2–3x/week)", "category": "exfoliant"})

            # Spot treatment at night if concerns include acne/pigmentation
            if any(c in ("acne", "hyperpigmentation", "dark spots", "melasma")
                   for c in profile["concerns"]):
                s.append({"time": "PM", "step": "Spot treatment", "category": "spot treatment"})
            return s

        if routine_type == "AM":
            steps.extend(am_steps())
        elif routine_type == "PM":
            steps.extend(pm_steps())
        elif routine_type == "SPOT":
            steps.append({
                "time": "SPOT",
                "step": "Spot treatment",
                "category": "spot treatment"
            })
        else:  # BOTH
            steps.extend(am_steps())
            steps.extend(pm_steps())

        return steps

    # ---------- Product Scoring Logic ----------

    def _choose_best_product(
        self,
        category: str,
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Deterministically pick ONE best product for the given category.

        category is a product_type value, e.g. "cleanser", "serum", "sunscreen".
        """
        candidates = []
        for prod in self.product_tool.products:
            pt = str(prod.get("product_type", "")).lower()
            if category in pt:
                candidates.append(prod)

        if not candidates:
            return None

        concerns = profile.get("concerns", [])
        skin_type = profile.get("skin_type", "")
        budget = profile.get("budget_preference", "")

        def score_product(p: Dict[str, Any]) -> int:
            score = 0

            # 1) Base: category already matched by filter
            score += 2

            name = str(p.get("product_name", "")).lower()
            ingredients = str(p.get("ingredients", "")).lower()
            price = str(p.get("price", "")).lower()

            # 2) Concerns → mapped to ingredient keywords
            concern_keywords_map = {
                "acne": ["acne", "salicylic", "bha", "benzoyl"],
                "aging": ["retinol", "retinoid", "peptide", "niacinamide",
                          "vitamin c", "collagen"],
                "hyperpigmentation": ["arbutin", "kojic", "tranexamic",
                                      "licorice", "vitamin c"],
                "sensitivity": ["ceramide", "centella", "cica", "panthenol",
                                "madecassoside", "fragrance free"],
                "dryness": ["hyaluronic", "glycerin", "squalane", "ceramide"],
            }

            for c in concerns:
                c_key = c.strip().lower()
                for key, kws in concern_keywords_map.items():
                    if key in c_key:
                        if any(kw in ingredients or kw in name for kw in kws):
                            score += 2

            # 3) Skin type → ingredient lean
            skin_type_keywords = {
                "dry": ["cream", "balm", "ceramide", "hyaluronic",
                        "shea", "squalane", "glycerin"],
                "oily": ["gel", "oil-free", "salicylic", "niacinamide",
                         "non-comedogenic"],
                "combination": ["lightweight", "balancing", "non-comedogenic"],
            }
            for stype, kws in skin_type_keywords.items():
                if stype in skin_type:
                    if any(kw in ingredients or kw in name for kw in kws):
                        score += 1

            # 4) Budget preference approx match
            budget_map = {
                "low": ["low", "budget", "affordable"],
                "medium": ["mid", "medium", "mid-range", "mid range", "moderate"],
                "high": ["high", "premium", "expensive", "luxury"],
            }
            b = budget.lower()
            for b_key, kws in budget_map.items():
                if b_key in b:
                    if any(kw in price for kw in kws):
                        score += 1

            # 5) Penalty: fragrance for sensitive skin
            if any("sensitivity" in c for c in concerns) and "fragrance" in ingredients:
                score -= 2

            return score

        best = None
        best_score = -10**9

        for prod in candidates:
            s = score_product(prod)
            if s > best_score:
                best_score = s
                best = prod

        return best

    # ---------- Text Helpers ----------

    def _build_reason_for_step(
        self,
        step_name: str,
        category: str,
        product: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> str:
        """
        Short, human-readable reason for why this product was selected.
        """
        name = product.get("product_name", "this product")
        skin_type = profile.get("skin_type", "")
        concerns = ", ".join(profile.get("concerns", [])) or "general skin health"

        return (
            f"{name} was chosen as your {step_name.lower()} because it fits the "
            f"'{category}' category and suits {skin_type} skin with concerns like {concerns}."
        )

    def _build_routine_brief(
        self,
        question: str,
        profile: Dict[str, Any],
        steps: List[Dict[str, Any]],
        routine_type: str,
    ) -> str:
        """
        High-level natural language summary of the routine in order.
        """
        name = profile.get("name") or "you"
        skin_type = profile.get("skin_type", "your").replace("_", " ")
        concerns = profile.get("concerns", [])
        concerns_text = ", ".join(concerns) if concerns else "overall skin health"

        # Group steps by time
        am_steps = [s for s in steps if s["time"] == "AM"]
        pm_steps = [s for s in steps if s["time"] == "PM"]
        spot_steps = [s for s in steps if s["time"] == "SPOT"]

        parts: List[str] = []

        intro = (
            f"This routine is tailored for {name} with {skin_type} skin "
            f"and concerns around {concerns_text}."
        )
        parts.append(intro)

        if am_steps:
            order = " → ".join(s["step"] for s in am_steps)
            parts.append(f"For the morning (AM), follow: {order}.")

        if pm_steps:
            order = " → ".join(s["step"] for s in pm_steps)
            parts.append(f"For the evening (PM), follow: {order}.")

        if spot_steps and routine_type == "SPOT":
            order = " → ".join(s["step"] for s in spot_steps)
            parts.append(f"For spot reduction only, use: {order}.")

        if pm_steps:
            # Special note about exfoliant if present
            if any("Exfoliant" in s["step"] for s in pm_steps):
                parts.append(
                    "Use the exfoliant only 2–3 times per week at night, not every day."
                )

        return " ".join(parts)
