# test_routine_agent.py

import json

from agents.routine_agent import RoutineAgent
from tools.product_lookup_tool import ProductLookupTool


if __name__ == "__main__":
    # Example profile in your exact schema
    user_profile_raw = {
        "Name?": "jahnavi",
        "Age?": "32",
        "Skin type (e.g., oily, dry, combination)": "dry",
        "Skin concerns (e.g., acne, sensitivity)": "aging",
        "Current Skincare routine": "no skincare",
        "Budget preference": "medium range",
    }

    # Try a few questions:

    # question = "Create an AM routine for me"
    # question = "Create a PM routine for me"
    # question = "Based on my profile create a routine for me"
    question = "Create a AM routine for me"

    tool = ProductLookupTool()
    agent = RoutineAgent(product_tool=tool)

    result = agent.run(question, user_profile_raw)
    print(json.dumps(result, indent=2))
