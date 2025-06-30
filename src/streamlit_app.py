"""
Agent Service Toolkit - Streamlit Application with Official Google Authentication

This application combines the original agent chat functionality with
Streamlit's official Google authentication system.
"""

import asyncio
import os
import urllib.parse
import uuid
from collections.abc import AsyncGenerator
from typing import Dict, Any, Optional

import httpx
import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from client import AgentClient, AgentClientError
from schema import ChatHistory, ChatMessage
from schema.task_data import TaskData, TaskDataStatus

# App Configuration
APP_TITLE = "Agent Service Toolkit"
APP_ICON = "🧰"
USER_ID_COOKIE = "user_id"

# Environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://agent_service:8080")


def get_backend_url() -> str:
    """Get the backend URL for API calls."""
    agent_url = os.getenv("AGENT_URL")
    if not agent_url:
        host = os.getenv("HOST", "0.0.0.0")
        port = os.getenv("PORT", 8080)
        agent_url = f"http://{host}:{port}"
    return agent_url


def get_or_create_user_id() -> str:
    """Get the user ID from session state or create a new one."""
    # For authenticated users, use their email as the user ID
    if hasattr(st, 'user') and st.user.is_logged_in:
        return st.user.email

    # Fallback to session-based user ID for development
    if USER_ID_COOKIE in st.session_state:
        return st.session_state[USER_ID_COOKIE]

    # Generate a new user_id if not found
    user_id = str(uuid.uuid4())
    st.session_state[USER_ID_COOKIE] = user_id
    return user_id


# OAuth API Functions
def call_oauth_status_api(user_id: str) -> dict:
    """Call backend API to get OAuth status for a user."""
    try:
        backend_url = get_backend_url()
        response = httpx.get(f"{backend_url}/api/oauth/status/{user_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get OAuth status: {response.status_code}")
            return {
                "todoist": {"connected": False, "status": "error"},
                "google_accounts": [],
            }
    except Exception as e:
        st.error(f"Error calling OAuth status API: {e}")
        return {
            "todoist": {"connected": False, "status": "error"},
            "google_accounts": [],
        }


def call_oauth_start_api(service: str, user_id: str) -> dict:
    """Call backend API to start OAuth flow."""
    try:
        backend_url = get_backend_url()
        response = httpx.post(
            f"{backend_url}/api/oauth/{service}/start", params={"user_id": user_id}
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to start {service} OAuth: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error starting {service} OAuth: {e}")
        return None


def call_oauth_disconnect_api(service: str, user_id: str) -> bool:
    """Call backend API to disconnect OAuth service."""
    try:
        backend_url = get_backend_url()
        response = httpx.delete(
            f"{backend_url}/api/oauth/disconnect/{service}/{user_id}"
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False)
        else:
            st.error(f"Failed to disconnect {service}: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error disconnecting {service}: {e}")
        return False


@st.cache_data
def get_available_agents() -> list:
    """Get list of available agents from the backend."""
    try:
        backend_url = get_backend_url()
        headers = {}
        auth_secret = os.environ.get("AUTH_SECRET")
        if auth_secret:
            headers["Authorization"] = f"Bearer {auth_secret}"
        response = httpx.get(f"{backend_url}/info", headers=headers)
        if response.status_code == 200:
            service_info = response.json()
            return [{"name": agent["key"], "description": agent["description"]} for agent in service_info.get("agents", [])]
        else:
            # Fallback to known agents
            return [
                {"name": "research-assistant", "description": "Research assistant with web search"},
                {"name": "jarvis", "description": "J.A.R.V.I.S."},
                {"name": "rag-assistant", "description": "RAG assistant"},
                {"name": "journaling-agent", "description": "Daily journaling assistant"}
            ]
    except Exception:
        # Fallback to known agents
        return [
            {"name": "research-assistant", "description": "Research assistant with web search"},
            {"name": "jarvis", "description": "J.A.R.V.I.S."},
            {"name": "rag-assistant", "description": "RAG assistant"},
            {"name": "journaling-agent", "description": "Daily journaling assistant"}
        ]


@st.dialog("🔗 OAuth Configuration")
def show_oauth_configuration(user_id: str):
    """Show OAuth configuration in a modal dialog."""
    st.markdown("### 🔗 External Integrations")
    st.caption("Configure OAuth connections for enhanced weekly reviews")

    # Get real OAuth status from backend
    oauth_status = call_oauth_status_api(user_id)

    # Todoist Integration
    st.markdown("#### 📝 Todoist Integration")
    todoist_status = oauth_status.get("todoist", {})

    if todoist_status.get("connected", False):
        st.success("✅ Connected to Todoist")
        if st.button("🔌 Disconnect Todoist Account", key="disconnect_todoist"):
            if call_oauth_disconnect_api("todoist", user_id):
                st.success("Todoist disconnected successfully!")
                st.rerun()
    else:
        st.warning("⚠️ Not connected to Todoist")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔗 Connect Todoist Account", key="connect_todoist"):
                result = call_oauth_start_api("todoist", user_id)
                if result and "authorization_url" in result:
                    st.markdown(
                        f'<a href="{result["authorization_url"]}" target="_self">Click here to authorize Todoist</a>',
                        unsafe_allow_html=True,
                    )
        with col2:
            if st.button("📊 Show Todoist Details", key="show_todoist"):
                st.info("Todoist details would be shown here")

    st.markdown("---")

    # Google Calendar Integration
    st.markdown("#### 📅 Google Calendar Integration")
    google_accounts = oauth_status.get("google_accounts", [])

    if google_accounts:
        for i, account in enumerate(google_accounts):
            with st.container(border=True):
                cols = st.columns([0.8, 0.2])
                with cols[0]:
                    st.markdown(f"**📧 {account.get('email', 'Unknown email')}**")
                with cols[1]:
                    help_str = f"Disconnect {account.get('email', 'this account')}"
                    if st.button(
                        "❌",
                        key=f"disconnect_google_{account.get('user_id', i)}",
                        help=help_str,
                    ):
                        if call_oauth_disconnect_api(
                            "google", account.get("user_id", "")
                        ):
                            st.success(
                                f"Disconnected {account.get('email', 'Google account')} successfully!"
                            )
                            st.rerun()
        st.markdown("")
    else:
        st.warning("⚠️ Not connected to Google Calendar")

    # Always show the connect button below the list
    if st.button("🔗 Connect a Google Account", key="connect_google"):
        result = call_oauth_start_api("google", user_id)
        if result and "authorization_url" in result:
            st.markdown(
                f'<a href="{result["authorization_url"]}" target="_self">Click here to authorize Google Calendar</a>',
                unsafe_allow_html=True,
            )

    # Close button
    if st.button("Close", key="close_oauth", type="primary"):
        st.rerun()


def show_login_page():
    """Show the login page with Google authentication."""
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.subheader("🔐 Authentication Required")

    st.markdown(
        """
    This application requires authentication to access your personal data and integrations.

    **Features available after login:**
    - Personal AI assistant with conversation history
    - Google Calendar integration for scheduling
    - Weekly review and planning tools
    - Journaling and task management
    """
    )

    # Official Streamlit Google authentication
    if st.button("🔐 Login with Google", type="primary", use_container_width=True):
        st.login()


async def draw_messages(
    messages: list[ChatMessage],
    agent_client: AgentClient,
    user_id: str,
    agent: str,
    model: str = "gpt-4",
    thread_id: str = "default",
) -> None:
    """Draw a list of chat messages, handling both static and streaming messages."""

    for i, message in enumerate(messages):
        message_key = f"message_{i}_{message.type}_{hash(message.content[:50])}"

        if message.type == "human":
            with st.chat_message("user", avatar="👤"):
                st.markdown(message.content)
        elif message.type == "ai":
            with st.chat_message("assistant", avatar="🤖"):
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Handle tool calls
                    for tool_call in message.tool_calls:
                        with st.expander(f"🛠️ {tool_call.get('name', 'Tool Call')}"):
                            st.code(str(tool_call.get('args', {})), language='json')

                st.markdown(message.content)

                # Show feedback for AI messages
                await handle_feedback(message, agent_client, message_key)


async def handle_feedback(
    message: ChatMessage, agent_client: AgentClient, message_key: str
) -> None:
    """Handle feedback collection for AI messages."""
    if hasattr(message, 'run_id') and message.run_id:
        # Check if feedback already given
        feedback_key = f"feedback_{message.run_id}"
        if feedback_key in st.session_state:
            existing_feedback = st.session_state[feedback_key]
            st.caption(f"👍 Feedback: {existing_feedback}/5")
            return

        # Show feedback widget
        feedback = st.feedback("stars", key=f"{message_key}_feedback")
        if feedback is not None:
            try:
                # Convert feedback to score (0-1 scale)
                normalized_score = (feedback + 1) / 5.0

                await agent_client.acreate_feedback(
                    run_id=message.run_id,
                    key="human-feedback-stars",
                    score=normalized_score,
                    kwargs={"comment": "In-line human feedback"},
                )

                st.session_state[feedback_key] = feedback + 1
                st.toast("Feedback recorded", icon="⭐")

            except AgentClientError as e:
                st.error(f"Error recording feedback: {e}")


def get_agent_welcome_message(agent_name: str) -> str:
    """Get the welcome message for a specific agent."""
    messages = {
        "research-assistant": "👋 Hello! I'm an AI-powered research assistant with web search and a calculator. Ask me anything!",
        "jarvis": "👋 Hello! I'm Jarvis, Just a Rather Very Intelligent System. How can I help you today?",
        "rag-assistant": "👋 Hello! I'm an AI-powered Company Policy & HR assistant with access to AcmeTech's Employee Handbook. I can help you find information about benefits, remote work, time-off policies, company values, and more. Ask me anything!",
        "journaling-agent": "👋 Hello! I'm a journaling agent. I can help you journal your thoughts and feelings.",
        "weekly-review-agent": "👋 Hello! I'm your GTD-style weekly review and planning assistant. I can help you review your week, plan ahead, and integrate with your tasks and calendar.",
        "chatbot": "👋 Hello! I'm a simple chatbot. Ask me anything!",
        "interrupt-agent": "👋 Hello! I'm an interrupt agent. Tell me your birthday and I will predict your personality!",
        "command-agent": "👋 Hello! I'm a command agent. I can help you with system commands and automation.",
        "bg-task-agent": "👋 Hello! I'm a background task agent. I can help you with long-running tasks.",
        "knowledge-base-agent": "👋 Hello! I'm a knowledge base agent with access to Amazon Bedrock Knowledge Base.",
    }
    return messages.get(agent_name, "👋 Hello! I'm an AI agent. Ask me anything!")


def initialize_agent_client() -> AgentClient:
    """Initialize the agent client."""
    backend_url = get_backend_url()
    return AgentClient(base_url=backend_url)


async def show_authenticated_app():
    """Show the main application for authenticated users."""
    st.title(f"{APP_ICON} {APP_TITLE}")

    # Get user ID
    user_id = get_or_create_user_id()

    # Initialize agent client
    if "agent_client" not in st.session_state:
        st.session_state.agent_client = initialize_agent_client()

    # Set agent from URL parameter if provided
    current_agent = st.query_params.get("agent", "research-assistant")
    if "agent_client" in st.session_state:
        try:
            st.session_state.agent_client.update_agent(current_agent)
        except Exception:
            # If agent from URL is invalid, ignore and use default
            pass

    # Sidebar with user info and controls
    with st.sidebar:
        st.markdown("### 👤 Logged in as:")
        # Handle both authenticated and test mode
        if hasattr(st, 'user') and st.user.is_logged_in:
            st.markdown(f"📧 {st.user.email}")
            st.markdown(f"👋 {st.user.name}")
        else:
            st.markdown("📧 test@example.com")
            st.markdown("👋 Test User")

        if st.button("📋 Logout", use_container_width=True):
            if hasattr(st, 'user') and st.user.is_logged_in:
                st.logout()
            else:
                st.info("Test mode - no actual logout")

        if st.button("💬 New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_history = ChatHistory(messages=[])
            st.rerun()

        st.markdown("---")

        # Settings
        with st.expander("⚙️ Settings"):
            # Get available agents
            agents = get_available_agents()
            agent_names = [agent.get("name", "unknown") for agent in agents]

            # Get current agent from URL or default
            current_agent_from_url = st.query_params.get("agent", "research-assistant")

            # Set default index based on URL parameter
            default_index = 0
            if current_agent_from_url in agent_names:
                default_index = agent_names.index(current_agent_from_url)
            elif "research-assistant" in agent_names:
                default_index = agent_names.index("research-assistant")

            selected_agent = st.selectbox(
                "🤖 Agent",
                options=agent_names,
                index=default_index,
                key="selected_agent",
            )

            # Handle agent selection change
            if "agent_client" in st.session_state and selected_agent:
                # Check if agent actually changed
                if selected_agent != current_agent_from_url:
                    # Update URL parameter and trigger reload
                    st.query_params["agent"] = selected_agent
                    # Clear chat history for new agent
                    st.session_state.chat_history = ChatHistory(messages=[])
                    # Update the client
                    try:
                        st.session_state.agent_client.update_agent(selected_agent)
                    except Exception as e:
                        st.error(f"Error updating agent: {e}")
                    # Trigger page reload
                    st.rerun()
                else:
                    # Just ensure the client has the right agent
                    try:
                        st.session_state.agent_client.update_agent(selected_agent)
                    except Exception as e:
                        st.error(f"Error updating agent: {e}")

            # Get available models from backend or use fallback
            try:
                if "agent_client" in st.session_state and hasattr(st.session_state.agent_client, 'info') and st.session_state.agent_client.info:
                    available_models = st.session_state.agent_client.info.models
                    default_model = st.session_state.agent_client.info.default_model
                    default_model_index = available_models.index(default_model) if default_model in available_models else 0
                else:
                    # Fallback model list (comprehensive list from schema)
                    available_models = [
                        # OpenAI - Latest and most economical first
                        "o4-mini",  # Most economical reasoning model
                        "gpt-4.1-nano",  # Fastest and cheapest
                        "gpt-4.1-mini",  # 83% cheaper than gpt-4o
                        "gpt-4.1",  # Latest flagship model
                        "gpt-4o-mini",
                        "gpt-4o",
                        "gpt-4-turbo",
                        "gpt-3.5-turbo",
                        # Anthropic - Latest Claude 4 series (2025)
                        "claude-4-sonnet",  # Latest Claude 4 Sonnet
                        "claude-4-opus",  # Latest Claude 4 Opus
                        "claude-3.5-sonnet",
                        "claude-3.5-haiku",
                        "claude-3-haiku",
                        # Google
                        "gemini-2.0-flash",
                        "gemini-1.5-pro",
                        "gemini-1.5-pro-002",
                        "gemini-2.5-pro-preview-05-06",
                        # Other providers
                        "deepseek-chat",
                        "llama-3.3-70b",
                        "llama-3.1-8b",
                        # Cloud-specific
                        "azure-gpt-4o",
                        "azure-gpt-4o-mini",
                        "bedrock-3.5-haiku",
                        "bedrock-3.5-sonnet",
                        # Generic
                        "ollama",
                        "openai-compatible"
                    ]
                    default_model_index = 0
            except Exception:
                # Fallback if anything goes wrong
                available_models = ["o4-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4o-mini", "claude-4-sonnet", "claude-3.5-haiku"]
                default_model_index = 0

            selected_model = st.selectbox(
                "🧠 Model",
                options=available_models,
                index=default_model_index,
                key="selected_model",
            )

            # Thread ID for conversation persistence
            thread_id = st.text_input(
                "🧵 Thread ID",
                value=st.session_state.get("thread_id", "default"),
                key="thread_id"
            )

        # OAuth Configuration
        if st.button("🔗 OAuth Configuration", use_container_width=True):
            show_oauth_configuration(user_id)

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = ChatHistory(messages=[])

    # Display chat messages
    if st.session_state.chat_history.messages:
        await draw_messages(
            st.session_state.chat_history.messages,
            st.session_state.agent_client,
            user_id,
            st.session_state.get("selected_agent", "research-assistant"),
            st.session_state.get("selected_model", "o4-mini"),
            st.session_state.get("thread_id", "default")
        )
    else:
        # Agent-specific welcome message
        current_agent = st.query_params.get("agent", "research-assistant")
        welcome_message = get_agent_welcome_message(current_agent)

        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(welcome_message)

    # Chat input
    if prompt := st.chat_input("Your message"):
        # Add user message to history
        user_message = ChatMessage(type="human", content=prompt)
        st.session_state.chat_history.messages.append(user_message)

        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                try:
                    # Get non-streaming response for testing
                    response = await st.session_state.agent_client.ainvoke(
                        message=prompt,
                        model=st.session_state.get("selected_model", "o4-mini"),
                        thread_id=st.session_state.get("thread_id", "default"),
                        user_id=user_id
                    )

                    st.markdown(response.content)

                    # Add AI response to history
                    st.session_state.chat_history.messages.append(response)

                except AgentClientError as e:
                    st.error(f"Error communicating with agent: {e}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")


async def main():
    """Main application entry point with official Google authentication."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Hide Streamlit branding and fix emoji rendering
    st.markdown(
        """
    <style>
    [data-testid="stStatusWidget"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }
    [data-testid="chatAvatarIcon-assistant"],
    [data-testid="stChatMessage"],
    [data-testid="chatAvatarIcon-user"] {
        font-family: sans-serif !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Check authentication using Streamlit's official authentication
    if st.user.is_logged_in:
        # User is authenticated
        await show_authenticated_app()
    else:
        # User is not authenticated
        show_login_page()


if __name__ == "__main__":
    asyncio.run(main())
