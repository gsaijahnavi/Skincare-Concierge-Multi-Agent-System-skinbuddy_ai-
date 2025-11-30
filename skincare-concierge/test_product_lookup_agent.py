# test_product_lookup_agent.py

import json

from agents.product_lookup_agent import ProductLookupAgent
from tools.product_lookup_tool import ProductLookupTool


if __name__ == "__main__":
    user_profile = {
        "age": 28,
        "skin_type": "dry",
        "concerns": ["acne", "texture"]
    }

    question = "Suggest me 1 moisturizer for acne-prone dry skin in the mid price range."

    tool = ProductLookupTool()
    agent = ProductLookupAgent(tool)

    result = agent.run(question, user_profile)
    print(json.dumps(result, indent=2))
