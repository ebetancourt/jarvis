from datetime import datetime
from typing import List
from langgraph.prebuilt import create_react_agent


# Conversation state management
class JournalingConversationState:
    """Manages the conversation state for the journaling agent."""

    def __init__(self):
        self.current_entry: str = ""
        self.questions_asked: List[str] = []
        self.responses_received: List[str] = []
        self.session_active: bool = False
        self.completion_signals: List[str] = [
            "I'm done",
            "i'm done",
            "done",
            "finish",
            "complete",
            "",
        ]

    def is_session_complete(self, response: str) -> bool:
        """Check if the user wants to complete the journaling session."""
        return response.strip().lower() in [
            signal.lower() for signal in self.completion_signals
        ]

    def add_question(self, question: str) -> None:
        """Add a question to the conversation history."""
        self.questions_asked.append(question)

    def add_response(self, response: str) -> None:
        """Add a user response to the conversation history."""
        self.responses_received.append(response)

    def reset_session(self) -> None:
        """Reset the conversation state for a new session."""
        self.current_entry = ""
        self.questions_asked = []
        self.responses_received = []
        self.session_active = False


# Initialize conversation state
conversation_state = JournalingConversationState()

# Tools for the journaling agent
tools = []  # Will be populated with journal tools when implemented

# Get current date for context
current_date = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%H:%M:%S")

# Create the journaling agent with conversation-aware prompt
journaling_agent_prompt = (
    f"Today is {current_date} at {current_time}. You are a thoughtful daily "
    "journaling assistant designed to help users reflect on their day through "
    "guided prompts and questions.\n\n"
    "Your primary goals:\n"
    "1. Help users capture meaningful daily reflections\n"
    "2. Ask thoughtful, CBT-style questions to encourage deeper insights\n"
    "3. Guide users through a natural conversation flow\n"
    "4. Save their entries to daily journal files\n\n"
    "Conversation Flow:\n"
    "- Start by welcoming the user and asking how their day went\n"
    "- Ask up to 2 follow-up questions based on their responses to encourage "
    "deeper reflection\n"
    "- Focus on priorities, emotions, challenges, and insights\n"
    '- When the user indicates they\'re done (says "I\'m done", "done", '
    '"finish", or gives an empty response), save their entry\n'
    "- Provide a confirmation message after saving\n\n"
    "Question Guidelines:\n"
    "- Ask open-ended questions that encourage reflection\n"
    "- Focus on emotions, priorities, challenges, and learnings\n"
    "- Avoid repeating similar questions in the same session\n"
    "- Keep questions conversational and supportive\n\n"
    "Always be warm, empathetic, and encouraging in your responses."
)

# Create the agent using LangGraph
journaling_agent = create_react_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools=tools,
    prompt=journaling_agent_prompt,
)

# Optional: Enhanced agent with memory and state management
# (Currently commented to match the pattern from jarvis.py)
# def get_journaling_agent():
#     """Create and configure the journaling agent with memory and state management."""
#     return journaling_agent.compile(
#         checkpointer=MemorySaver(),
#         store=InMemoryStore()
#     )
