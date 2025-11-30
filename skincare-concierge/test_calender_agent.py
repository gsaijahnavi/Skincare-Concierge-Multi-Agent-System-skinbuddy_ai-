# test_calendar_agent.py

import json
from agents.calendar_agent import CalendarAgent  # adjust path if needed

if __name__ == "__main__":
    agent = CalendarAgent()

    user_profile = {
        "Name?": "jahnavi",
        "Age?": "32",
        "Skin type (e.g., oily, dry, combination)": "dry",
        "Skin concerns (e.g., acne, sensitivity)": "aging",
        "Current Skincare routine": "no skincare",
        "Budget preference": "medium range",
    }

    # EXAMPLES:
    # question = "Remind me to use my AM routine at 7 AM every day"
    # question = "List my reminders"
    # question = "Delete my AM routine reminder"
    # question = "Delete all my reminders"
    question = "delete my PM reminders?"
    plan = agent.plan(question, user_profile)

    print("\n--- PLAN ---")
    print(json.dumps(plan, indent=2, default=str))

    intent = plan.get("intent")

    confirm = True
    selected_titles = None

    if intent == "delete":
        matches = plan.get("payload", {}).get("matches", [])
        if not matches:
            print("\nNo matching reminders to delete.")
            confirm = False
        elif len(matches) == 1:
            print(f"\nMatching reminder: {matches[0]}")
            ans = input("Delete this reminder? (y/n): ").strip().lower()
            confirm = ans == "y"
            selected_titles = matches
        else:
            print("\nMultiple matching reminders found:")
            for i, t in enumerate(matches, start=1):
                print(f"{i}. {t}")
            print("Type 'all' to delete all, or comma-separated numbers (e.g., 1,3):")
            choice = input("Your choice: ").strip().lower()

            if choice == "all":
                selected_titles = matches
            else:
                try:
                    idxs = [int(x.strip()) for x in choice.split(",") if x.strip().isdigit()]
                    selected_titles = [matches[i - 1] for i in idxs if 1 <= i <= len(matches)]
                except Exception:
                    selected_titles = []

            if not selected_titles:
                print("No valid selection made; cancelling.")
                confirm = False

    elif plan.get("needs_confirmation"):
        ans = input("\nProceed with this action? (y/n): ").strip().lower()
        confirm = ans == "y"

    result = agent.execute(plan, confirm=confirm, selected_titles=selected_titles)

    print("\n--- RESULT ---")
    print(json.dumps(result, indent=2, default=str))
