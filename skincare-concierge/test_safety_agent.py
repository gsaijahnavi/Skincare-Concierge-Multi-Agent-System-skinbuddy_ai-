import pytest
from agents.safety_agent import SafetyAgent
import sys

@pytest.fixture
def agent():
    return SafetyAgent()

def test_safe_text(agent):
    text = "I have dry skin and want a moisturizer."
    result = agent.intercept(text)
    assert result == "safe"
    assert agent.get_last_safe_text() == text

def test_trigger_word(agent):
    text = "I am experiencing severe rash and bleeding."
    result = agent.intercept(text)
    assert result == "Please contact a medical professional. I can't answer this."
    # Should not update last_safe_text
    assert agent.get_last_safe_text() != text

def test_multiple_trigger_words(agent):
    text = "I feel unconscious and have chest pain."
    result = agent.intercept(text)
    assert result == "Please contact a medical professional. I can't answer this."

@pytest.mark.parametrize("word", SafetyAgent().trigger_words)
def test_each_trigger_word_flagged(agent, word):
    text = f"I have {word}"
    result = agent.intercept(text)
    assert result == "Please contact a medical professional. I can't answer this."

def main():
    agent = SafetyAgent()
    print("Type your message (or 'exit' to quit):")
    while True:
        text = input("Message: ")
        if text.lower() == "exit":
            break
        result = agent.intercept(text)
        print("Output:", result)
        if result == "safe":
            print("Text stored for next stage:", agent.get_last_safe_text())

if __name__ == "__main__":
    main()
