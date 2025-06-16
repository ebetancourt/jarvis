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
        self.max_questions: int = 2
        self.initial_response: str = ""
        self.conversation_phase: str = (
            "initial"  # "initial", "questioning", "completion"
        )
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
        self.initial_response = ""
        self.conversation_phase = "initial"

    def can_ask_more_questions(self) -> bool:
        """Check if we can still ask more questions in this session."""
        return len(self.questions_asked) < self.max_questions

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for journal entry."""
        summary_parts = []

        if self.initial_response:
            summary_parts.append(self.initial_response)

        # Add question-response pairs
        for i, (question, response) in enumerate(
            zip(self.questions_asked, self.responses_received)
        ):
            if response.strip():  # Only include non-empty responses
                summary_parts.append(f"\n\nReflection {i+1}: {response}")

        return "\n\n".join(summary_parts)


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


def process_conversation_flow(
    user_message: str, conversation_state: JournalingConversationState
) -> tuple[str, bool]:
    """
    Process the conversation flow logic with question limits and phase management.

    Manages the conversation through three phases:
    1. Initial: Capture the user's opening response
    2. Questioning: Ask up to 2 follow-up questions
    3. Completion: Process final responses and prepare for journal saving

    Args:
        user_message: The user's current message
        conversation_state: Current state of the conversation

    Returns:
        tuple[str, bool]: (response_message, should_save_entry)
    """

    # Check for completion signals first
    if conversation_state.is_session_complete(user_message):
        conversation_state.conversation_phase = "completion"
        return _handle_completion_phase(conversation_state)

    # Handle different conversation phases
    if conversation_state.conversation_phase == "initial":
        return _handle_initial_phase(user_message, conversation_state)

    elif conversation_state.conversation_phase == "questioning":
        return _handle_questioning_phase(user_message, conversation_state)

    elif conversation_state.conversation_phase == "completion":
        return _handle_completion_phase(conversation_state)

    else:
        # Default fallback
        return (
            "I'm here to help you reflect on your day. How was your day today?",
            False,
        )


def _handle_initial_phase(
    user_message: str, conversation_state: JournalingConversationState
) -> tuple[str, bool]:
    """Handle the initial response from the user."""
    conversation_state.initial_response = user_message
    conversation_state.session_active = True
    conversation_state.conversation_phase = "questioning"

    # Generate first follow-up question
    if conversation_state.can_ask_more_questions():
        question = generate_guiding_questions(
            user_message, conversation_state.questions_asked
        )
        conversation_state.add_question(question)
        return question, False
    else:
        # Skip questioning if no questions allowed
        conversation_state.conversation_phase = "completion"
        return _handle_completion_phase(conversation_state)


def _handle_questioning_phase(
    user_message: str, conversation_state: JournalingConversationState
) -> tuple[str, bool]:
    """Handle follow-up questions and responses."""
    # Store the response to the last question
    conversation_state.add_response(user_message)

    # Check if we can ask more questions
    if conversation_state.can_ask_more_questions():
        # Generate next question based on the latest response
        question = generate_guiding_questions(
            user_message, conversation_state.questions_asked
        )
        conversation_state.add_question(question)
        return question, False
    else:
        # We've reached the question limit, move to completion
        conversation_state.conversation_phase = "completion"
        return _handle_completion_phase(conversation_state)


def _handle_completion_phase(
    conversation_state: JournalingConversationState,
) -> tuple[str, bool]:
    """Handle the completion phase and prepare for journal saving."""
    completion_message = generate_confirmation_message(conversation_state)
    return completion_message, True


def generate_confirmation_message(
    conversation_state: JournalingConversationState,
) -> str:
    """
    Generate encouraging confirmation messages for journal entry saving.

    Creates varied, supportive messages that acknowledge the user's reflection
    effort and confirm the journal entry will be saved.

    Args:
        conversation_state: Current conversation state with user responses

    Returns:
        str: An encouraging confirmation message
    """
    responses_count = len(
        [r for r in conversation_state.responses_received if r.strip()]
    )

    # Different message sets based on engagement level
    if responses_count >= 2:
        # Deep engagement - multiple meaningful responses
        deep_engagement_messages = [
            "Great work diving deep into your reflections today! I'll save this "
            "thoughtful entry to your daily journal. 📝",
            "Thank you for taking the time to explore your thoughts and feelings. "
            "Your insights are now saved in your journal! ✨",
            "Wonderful reflection! I can see you've really thought through your day. "
            "Your entry is being saved to your journal. 🌟",
            "Excellent self-reflection today! These insights will be valuable to "
            "look back on. Saving to your journal now! 💭",
            "Beautiful work reflecting on your experiences. Your thoughtful entry "
            "is now safely stored in your daily journal! 🌱",
        ]
        selected_messages = deep_engagement_messages

    elif responses_count == 1:
        # Moderate engagement - one follow-up response
        moderate_engagement_messages = [
            "Thank you for sharing your thoughts with me today. I'll save this "
            "reflection to your daily journal! 📖",
            "Great job taking a moment to reflect. Your entry is being saved "
            "to your journal now! ✍️",
            "Nice work thinking through your day. I'll add this to your daily "
            "journal for you! 🗓️",
            "Thanks for the thoughtful reflection! Your journal entry is being "
            "saved now. 💫",
            "Good reflection today! I'll make sure this gets saved to your "
            "daily journal. 📚",
        ]
        selected_messages = moderate_engagement_messages

    else:
        # Initial response only
        initial_only_messages = [
            "Thank you for sharing your initial thoughts. I'll save this to "
            "your daily journal. Even brief reflections can be meaningful! 📝",
            "Great start! I'll add your thoughts to today's journal entry. "
            "Every reflection counts! ✨",
            "Thanks for taking a moment to reflect. Your entry is being saved "
            "to your journal! 🌟",
            "Perfect! I'll save your reflection to today's journal. Sometimes "
            "simple thoughts are the most powerful! 💭",
            "Wonderful! Your thoughts are being added to your daily journal. "
            "Thank you for reflecting today! 🌱",
        ]
        selected_messages = initial_only_messages

    # Select a random message from the appropriate set
    confirmation_message = random.choice(selected_messages)

    return confirmation_message


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
