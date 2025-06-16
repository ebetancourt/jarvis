from datetime import datetime
from typing import List, Optional
import random
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


def generate_guiding_questions(
    user_response: str, previous_questions: List[str], context: Optional[str] = None
) -> str:
    """
    Generate CBT-style guiding questions based on user responses.

    Uses cognitive behavioral therapy principles to ask thoughtful questions
    that encourage reflection on thoughts, feelings, behaviors, and patterns.

    Args:
        user_response: The user's most recent response
        previous_questions: List of questions already asked in this session
        context: Optional additional context about the conversation

    Returns:
        str: A thoughtful follow-up question to encourage deeper reflection
    """

    # CBT-style question banks organized by focus area
    emotion_questions = [
        "What emotions are you experiencing as you think about this?",
        "How are you feeling in your body right now when you reflect on this?",
        "What feelings came up for you during this situation?",
        "Can you name the strongest emotion you felt today?",
        "What triggered that emotional response for you?",
        "How did your mood shift throughout the day?",
    ]

    thought_pattern_questions = [
        "What thoughts were going through your mind during that moment?",
        "What assumptions might you have been making in that situation?",
        "How would you challenge that thought if a friend shared it with you?",
        "What evidence supports or contradicts that belief?",
        "What would you tell someone else who had this same thought?",
        "Is there another way to look at this situation?",
    ]

    behavior_questions = [
        "How did you respond to that challenge?",
        "What actions did you take that you're proud of today?",
        "What would you do differently if faced with a similar situation?",
        "What coping strategies did you use today?",
        "How did your actions align with your values today?",
        "What behavior patterns are you noticing in yourself?",
    ]

    growth_questions = [
        "What did you learn about yourself today?",
        "What would you like to remember from today's experience?",
        "How has this situation helped you grow?",
        "What strengths did you discover or use today?",
        "What are you grateful for from today?",
        "What would 'future you' want to know about today?",
    ]

    priority_questions = [
        "What mattered most to you today?",
        "How did you spend your energy today?",
        "What activities brought you the most fulfillment?",
        "What would you prioritize differently tomorrow?",
        "How did today align with your bigger goals?",
        "What deserves more of your attention going forward?",
    ]

    # Combine all question banks
    all_questions = (
        emotion_questions
        + thought_pattern_questions
        + behavior_questions
        + growth_questions
        + priority_questions
    )

    # Filter out questions that are too similar to previously asked ones
    available_questions = []
    for question in all_questions:
        # Simple similarity check - avoid questions with overlapping key words
        is_similar = False
        question_words = set(question.lower().split())

        for prev_q in previous_questions:
            prev_words = set(prev_q.lower().split())
            # If more than 2 key words overlap, consider it similar
            overlap = len(question_words.intersection(prev_words))
            if overlap > 2:
                is_similar = True
                break

        if not is_similar:
            available_questions.append(question)

    # If we've exhausted unique questions, fall back to growth questions
    if not available_questions:
        available_questions = growth_questions

    # Select a random question from available options
    selected_question = random.choice(available_questions)

    # Add contextual intro based on response content
    response_lower = user_response.lower()

    if any(
        word in response_lower
        for word in ["hard", "difficult", "tough", "struggle", "challenge"]
    ):
        intro = "That sounds challenging. "
    elif any(
        word in response_lower
        for word in ["good", "great", "amazing", "wonderful", "happy"]
    ):
        intro = "That's wonderful to hear. "
    elif any(word in response_lower for word in ["okay", "fine", "alright", "normal"]):
        intro = "I hear you. "
    else:
        intro = "Thank you for sharing that. "

    return f"{intro}{selected_question}"


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
