import os
from unittest.mock import patch


# Import the journaling agent module directly to avoid dependency issues
def _import_journaling_agent():
    """Import journaling agent functions dynamically to avoid dependency issues."""
    import importlib.util

    # Get the current file's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(current_dir, "..", "..", "src", "agents", "journaling_agent.py")
    module_path = os.path.normpath(module_path)

    spec = importlib.util.spec_from_file_location("journaling_agent", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import the module
try:
    journaling_agent = _import_journaling_agent()
except (NameError, FileNotFoundError, AttributeError):
    # Fallback for when __file__ is not available (e.g., in exec context)
    import importlib.util

    module_path = os.path.join("src", "agents", "journaling_agent.py")
    spec = importlib.util.spec_from_file_location("journaling_agent", module_path)
    journaling_agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(journaling_agent)
JournalingConversationState = journaling_agent.JournalingConversationState
generate_guiding_questions = journaling_agent.generate_guiding_questions
generate_guiding_questions_with_memory = journaling_agent.generate_guiding_questions_with_memory
generate_confirmation_message = journaling_agent.generate_confirmation_message
process_conversation_flow = journaling_agent.process_conversation_flow
_handle_initial_phase = journaling_agent._handle_initial_phase
_handle_questioning_phase = journaling_agent._handle_questioning_phase
_handle_completion_phase = journaling_agent._handle_completion_phase


class TestJournalingConversationState:
    """Test cases for JournalingConversationState class."""

    def test_init_default_values(self):
        """Test that JournalingConversationState initializes with correct defaults."""
        state = JournalingConversationState()

        assert state.current_entry == ""
        assert state.questions_asked == []
        assert state.responses_received == []
        assert state.session_active is False
        assert state.max_questions == 2
        assert state.initial_response == ""
        assert state.conversation_phase == "initial"
        assert state.used_question_categories == []
        assert state.question_keywords_used == set()
        assert "I'm done" in state.completion_signals
        assert "done" in state.completion_signals
        assert "" in state.completion_signals

    def test_is_session_complete_with_completion_signals(self):
        """Test session completion detection with various completion signals."""
        state = JournalingConversationState()

        # Test various completion signals
        completion_cases = [
            "I'm done",
            "i'm done",
            "done",
            "DONE",
            "finish",
            "complete",
            "",
            "  ",  # Whitespace only
        ]

        for signal in completion_cases:
            assert state.is_session_complete(signal), f"Failed for signal: '{signal}'"

    def test_is_session_complete_with_non_completion_signals(self):
        """Test that non-completion signals don't trigger session end."""
        state = JournalingConversationState()

        non_completion_cases = [
            "I had a good day",
            "Something interesting happened",
            "not done yet",
            "finished my work",  # Contains 'finish' but not exact match
            "completion of the task",  # Contains 'complete' but not exact match
        ]

        for signal in non_completion_cases:
            assert not state.is_session_complete(signal), f"Incorrectly completed for: '{signal}'"

    def test_add_question(self):
        """Test adding questions to the conversation state."""
        state = JournalingConversationState()

        question1 = "How was your day?"
        question2 = "What emotions did you feel?"

        state.add_question(question1)
        assert len(state.questions_asked) == 1
        assert state.questions_asked[0] == question1

        state.add_question(question2)
        assert len(state.questions_asked) == 2
        assert state.questions_asked[1] == question2

    def test_add_response(self):
        """Test adding responses to the conversation state."""
        state = JournalingConversationState()

        response1 = "It was a challenging day"
        response2 = "I felt anxious but also accomplished"

        state.add_response(response1)
        assert len(state.responses_received) == 1
        assert state.responses_received[0] == response1

        state.add_response(response2)
        assert len(state.responses_received) == 2
        assert state.responses_received[1] == response2

    def test_can_ask_more_questions(self):
        """Test question limit checking."""
        state = JournalingConversationState()

        # Initially should be able to ask questions
        assert state.can_ask_more_questions()

        # Add first question
        state.add_question("First question")
        assert state.can_ask_more_questions()

        # Add second question (at limit)
        state.add_question("Second question")
        assert not state.can_ask_more_questions()

    def test_add_question_with_memory(self):
        """Test adding questions with memory tracking."""
        state = JournalingConversationState()

        question = "What emotions are you experiencing?"
        category = "emotions"

        state.add_question_with_memory(question, category)

        assert question in state.questions_asked
        assert category in state.used_question_categories
        assert "emotions" in state.question_keywords_used
        assert "experiencing" in state.question_keywords_used
        # Common words should be filtered out
        assert "what" not in state.question_keywords_used
        assert "are" not in state.question_keywords_used

    def test_reset_session(self):
        """Test session reset functionality."""
        state = JournalingConversationState()

        # Populate state with data
        state.current_entry = "Some entry"
        state.questions_asked = ["Question 1", "Question 2"]
        state.responses_received = ["Response 1", "Response 2"]
        state.session_active = True
        state.initial_response = "Initial response"
        state.conversation_phase = "questioning"
        state.used_question_categories = ["emotions", "thoughts"]
        state.question_keywords_used = {"emotions", "thoughts", "feelings"}

        # Reset session
        state.reset_session()

        # Verify everything is reset
        assert state.current_entry == ""
        assert state.questions_asked == []
        assert state.responses_received == []
        assert state.session_active is False
        assert state.initial_response == ""
        assert state.conversation_phase == "initial"
        assert state.used_question_categories == []
        assert state.question_keywords_used == set()

    def test_get_conversation_summary_with_initial_only(self):
        """Test conversation summary with only initial response."""
        state = JournalingConversationState()
        state.initial_response = "I had a productive day at work."

        summary = state.get_conversation_summary()
        assert summary == "I had a productive day at work."

    def test_get_conversation_summary_with_responses(self):
        """Test conversation summary with questions and responses."""
        state = JournalingConversationState()
        state.initial_response = "I had a challenging day."
        state.questions_asked = [
            "How did you handle the challenges?",
            "What did you learn?",
        ]
        state.responses_received = [
            "I took breaks and asked for help.",
            "I learned to prioritize better.",
        ]

        summary = state.get_conversation_summary()

        assert "I had a challenging day." in summary
        assert "Reflection 1: I took breaks and asked for help." in summary
        assert "Reflection 2: I learned to prioritize better." in summary

    def test_get_conversation_summary_filters_empty_responses(self):
        """Test that empty responses are filtered from conversation summary."""
        state = JournalingConversationState()
        state.initial_response = "Good day today."
        state.questions_asked = ["Question 1", "Question 2"]
        state.responses_received = [
            "Good response",
            "  ",
        ]  # Second response is whitespace

        summary = state.get_conversation_summary()

        assert "Good day today." in summary
        assert "Reflection 1: Good response" in summary
        assert "Reflection 2" not in summary  # Empty response should be filtered


class TestQuestionGeneration:
    """Test cases for question generation functions."""

    def test_generate_guiding_questions_basic_functionality(self):
        """Test basic question generation functionality."""
        user_response = "I had a tough day at work."
        previous_questions = []

        question = generate_guiding_questions(user_response, previous_questions)

        assert isinstance(question, str)
        assert len(question) > 0
        assert question.endswith("?")

    def test_generate_guiding_questions_contextual_intros(self):
        """Test that contextual intros are added based on response content."""
        test_cases = [
            ("I had a difficult day", "That sounds challenging."),
            ("It was an amazing day", "That's wonderful to hear."),
            ("The day was okay", "I hear you."),
            ("Just a regular day", "Thank you for sharing that."),
        ]

        for response, expected_intro in test_cases:
            question = generate_guiding_questions(response, [])
            assert question.startswith(expected_intro), f"Failed for response: '{response}'"

    @patch("agents.journaling_agent.random.choice")
    def test_generate_guiding_questions_avoids_similar_questions(self, mock_choice):
        """Test that similar questions are filtered out."""
        user_response = "I felt anxious today."
        previous_questions = ["What emotions are you experiencing?"]

        # Mock to return a predictable question
        mock_choice.return_value = "How are you feeling right now?"

        question = generate_guiding_questions(user_response, previous_questions)

        # Should not contain questions too similar to previous ones
        assert "emotions" not in question.lower()  # Should avoid emotion-related duplicates

    def test_generate_guiding_questions_with_memory_returns_tuple(self):
        """Test that memory-enhanced function returns question and category."""
        state = JournalingConversationState()
        user_response = "I accomplished a lot today."

        result = generate_guiding_questions_with_memory(user_response, state)

        assert isinstance(result, tuple)
        assert len(result) == 2
        question, category = result
        assert isinstance(question, str)
        assert isinstance(category, str)
        assert category in ["emotions", "thoughts", "behaviors", "growth", "priorities"]

    def test_generate_guiding_questions_with_memory_avoids_used_categories(self):
        """Test that memory system avoids recently used categories."""
        state = JournalingConversationState()
        state.used_question_categories = ["emotions", "thoughts"]
        user_response = "I had a good day."

        question, category = generate_guiding_questions_with_memory(user_response, state)

        # Should select from unused categories
        assert category in ["behaviors", "growth", "priorities"]

    def test_generate_guiding_questions_with_memory_keyword_avoidance(self):
        """Test that memory system avoids questions with overlapping keywords."""
        state = JournalingConversationState()
        state.question_keywords_used = {"emotions", "feeling", "mood"}
        user_response = "I was happy today."

        question, category = generate_guiding_questions_with_memory(user_response, state)

        # Should avoid questions with high keyword overlap
        question_words = set(question.lower().split())
        overlap = len(question_words.intersection(state.question_keywords_used))
        assert overlap <= 1  # Should have minimal overlap

    def test_generate_guiding_questions_with_memory_resets_when_exhausted(self):
        """Test that category restrictions reset when all categories are used."""
        state = JournalingConversationState()
        state.used_question_categories = [
            "emotions",
            "thoughts",
            "behaviors",
            "growth",
            "priorities",
        ]
        user_response = "Today was interesting."

        question, category = generate_guiding_questions_with_memory(user_response, state)

        # Should still generate a question even when all categories used
        assert isinstance(question, str)
        assert len(question) > 0
        assert category in ["emotions", "thoughts", "behaviors", "growth", "priorities"]


class TestConfirmationMessages:
    """Test cases for confirmation message generation."""

    def test_generate_confirmation_message_deep_engagement(self):
        """Test confirmation messages for deep engagement (2+ responses)."""
        state = JournalingConversationState()
        state.responses_received = ["First response", "Second response"]

        message = generate_confirmation_message(state)

        assert isinstance(message, str)
        assert len(message) > 0
        # Should contain encouraging language for deep engagement
        assert any(
            word in message.lower() for word in ["great", "wonderful", "excellent", "beautiful"]
        )

    def test_generate_confirmation_message_moderate_engagement(self):
        """Test confirmation messages for moderate engagement (1 response)."""
        state = JournalingConversationState()
        state.responses_received = ["Single response"]

        message = generate_confirmation_message(state)

        assert isinstance(message, str)
        assert len(message) > 0
        # Should contain appreciative language
        assert any(word in message.lower() for word in ["thank", "great", "good", "nice"])

    def test_generate_confirmation_message_initial_only(self):
        """Test confirmation messages for initial response only."""
        state = JournalingConversationState()
        state.responses_received = []

        message = generate_confirmation_message(state)

        assert isinstance(message, str)
        assert len(message) > 0
        # Should validate brief reflections
        assert any(phrase in message.lower() for phrase in ["brief", "simple", "reflection"])

    def test_generate_confirmation_message_filters_empty_responses(self):
        """Test that empty responses are filtered from engagement calculation."""
        state = JournalingConversationState()
        state.responses_received = [
            "Good response",
            "  ",
            "",
        ]  # Only one meaningful response

        message = generate_confirmation_message(state)

        # Should treat as moderate engagement (1 meaningful response)
        assert any(word in message.lower() for word in ["thank", "great", "good", "nice"])

    @patch("agents.journaling_agent.random.choice")
    def test_generate_confirmation_message_randomization(self, mock_choice):
        """Test that confirmation messages use randomization."""
        state = JournalingConversationState()
        state.responses_received = ["Response 1", "Response 2"]

        expected_message = "Mocked confirmation message"
        mock_choice.return_value = expected_message

        message = generate_confirmation_message(state)

        assert message == expected_message
        mock_choice.assert_called_once()


class TestConversationFlow:
    """Test cases for conversation flow management."""

    def test_process_conversation_flow_completion_signal_detection(self):
        """Test that completion signals are detected and handled."""
        state = JournalingConversationState()
        state.conversation_phase = "questioning"

        response, should_save = process_conversation_flow("done", state)

        assert should_save is True
        assert state.conversation_phase == "completion"
        assert "Thank you" in response or "save" in response.lower()

    def test_process_conversation_flow_initial_phase(self):
        """Test conversation flow in initial phase."""
        state = JournalingConversationState()
        user_message = "I had a busy day at work today."

        response, should_save = process_conversation_flow(user_message, state)

        assert should_save is False
        assert state.conversation_phase == "questioning"
        assert state.initial_response == user_message
        assert state.session_active is True
        assert len(state.questions_asked) == 1

    def test_process_conversation_flow_questioning_phase(self):
        """Test conversation flow in questioning phase."""
        state = JournalingConversationState()
        state.conversation_phase = "questioning"
        state.questions_asked = ["First question"]
        user_message = "I felt accomplished but tired."

        response, should_save = process_conversation_flow(user_message, state)

        if state.can_ask_more_questions():
            assert should_save is False
            assert len(state.responses_received) == 1
            assert len(state.questions_asked) == 2
        else:
            assert should_save is True
            assert state.conversation_phase == "completion"

    def test_process_conversation_flow_completion_phase(self):
        """Test conversation flow in completion phase."""
        state = JournalingConversationState()
        state.conversation_phase = "completion"

        response, should_save = process_conversation_flow("Any message", state)

        assert should_save is True
        assert "Thank you" in response or "save" in response.lower()

    def test_handle_initial_phase(self):
        """Test initial phase handling."""
        state = JournalingConversationState()
        user_message = "Today was challenging but rewarding."

        response, should_save = _handle_initial_phase(user_message, state)

        assert state.initial_response == user_message
        assert state.session_active is True
        assert state.conversation_phase == "questioning"
        assert should_save is False
        assert len(state.questions_asked) == 1

    def test_handle_questioning_phase_continue(self):
        """Test questioning phase when more questions can be asked."""
        state = JournalingConversationState()
        state.questions_asked = ["First question"]  # One question asked, can ask one more
        user_message = "I learned a lot about myself."

        response, should_save = _handle_questioning_phase(user_message, state)

        assert len(state.responses_received) == 1
        assert state.responses_received[0] == user_message
        assert len(state.questions_asked) == 2
        assert should_save is False

    def test_handle_questioning_phase_limit_reached(self):
        """Test questioning phase when question limit is reached."""
        state = JournalingConversationState()
        state.questions_asked = ["Q1", "Q2"]  # Already at limit
        user_message = "Final response"

        response, should_save = _handle_questioning_phase(user_message, state)

        assert len(state.responses_received) == 1
        assert state.conversation_phase == "completion"
        assert should_save is True

    def test_handle_completion_phase(self):
        """Test completion phase handling."""
        state = JournalingConversationState()
        state.responses_received = ["Response 1", "Response 2"]

        response, should_save = _handle_completion_phase(state)

        assert should_save is True
        assert isinstance(response, str)
        assert len(response) > 0

    def test_conversation_flow_edge_cases(self):
        """Test conversation flow edge cases."""
        state = JournalingConversationState()

        # Test unknown phase
        state.conversation_phase = "unknown"
        response, should_save = process_conversation_flow("message", state)
        assert should_save is False
        assert "reflect on your day" in response.lower()

    def test_conversation_flow_max_questions_zero(self):
        """Test conversation flow when max questions is set to zero."""
        state = JournalingConversationState()
        state.max_questions = 0
        user_message = "Initial message"

        response, should_save = _handle_initial_phase(user_message, state)

        # Should go directly to completion
        assert state.conversation_phase == "completion"
        assert should_save is True


class TestIntegration:
    """Integration tests for the complete conversation system."""

    def test_full_conversation_flow_deep_engagement(self):
        """Test a complete conversation flow with deep engagement."""
        state = JournalingConversationState()

        # Initial response
        response1, save1 = process_conversation_flow("I had a stressful day", state)
        assert save1 is False
        assert state.conversation_phase == "questioning"

        # First follow-up
        response2, save2 = process_conversation_flow("I felt overwhelmed", state)
        assert save2 is False
        assert len(state.responses_received) == 1

        # Second follow-up (should reach limit)
        response3, save3 = process_conversation_flow("I learned to manage stress", state)
        assert save3 is True
        assert state.conversation_phase == "completion"
        assert len(state.responses_received) == 2

    def test_full_conversation_flow_early_completion(self):
        """Test conversation flow with early completion signal."""
        state = JournalingConversationState()

        # Initial response
        process_conversation_flow("Brief reflection", state)

        # Early completion
        response, should_save = process_conversation_flow("done", state)
        assert should_save is True
        assert state.conversation_phase == "completion"

    def test_conversation_summary_integration(self):
        """Test that conversation summary integrates properly."""
        state = JournalingConversationState()

        # Simulate full conversation
        process_conversation_flow("Initial thought", state)
        process_conversation_flow("First reflection", state)
        process_conversation_flow("Second reflection", state)

        summary = state.get_conversation_summary()
        assert "Initial thought" in summary
        assert "Reflection 1: First reflection" in summary
        assert "Reflection 2: Second reflection" in summary

    def test_memory_system_integration(self):
        """Test that memory system works across conversation flow."""
        state = JournalingConversationState()

        # Initial phase
        process_conversation_flow("I had emotions today", state)

        # Check that memory is being tracked
        assert len(state.used_question_categories) > 0
        assert len(state.question_keywords_used) > 0

        # Continue conversation
        process_conversation_flow("More thoughts", state)

        # Should have different category for second question
        assert len(state.used_question_categories) <= 2  # Max 2 questions
        categories_used = state.used_question_categories
        if len(categories_used) == 2:
            assert categories_used[0] != categories_used[1]  # Should be different categories
