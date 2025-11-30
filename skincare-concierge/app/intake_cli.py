import asyncio
from agents.intake_agent import IntakeAgent
from tools.profile_tool import ProfileDBTool

def ask_fn(prompt):
    return input(prompt + " ")

def main():
    agent = IntakeAgent(ProfileDBTool())
    user_id = input("Enter your user ID: ")
    while True:
        query = input("\nAsk a question (or type 'exit' to quit): ")
        if query.lower() == "exit":
            break
        async def run_agent():
            # Use asyncio.to_thread to make ask_fn async-compatible
            result = await agent.handle(user_id, query, ask_fn=lambda p: asyncio.to_thread(ask_fn, p))
            print(result)
        asyncio.run(run_agent())

if __name__ == "__main__":
    main()
