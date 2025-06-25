"""
Agent Service Toolkit - Streamlit Application with Official Google Authentication

This application uses Streamlit's official Google authentication (1.42.0+)
for secure user authentication and session management.
"""

import asyncio
import os
import httpx
import streamlit as st
from typing import Dict, Any, Optional

# App Configuration
APP_TITLE = "Agent Service Toolkit"
APP_ICON = "🧰"

# Environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://agent_service:8080")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


def get_backend_url() -> str:
    """Get the backend URL for API calls."""
    return BACKEND_URL


@st.cache_data
def get_available_agents() -> list:
    """Get list of available agents from the backend."""
    try:
        backend_url = get_backend_url()
        response = httpx.get(f"{backend_url}/agents")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch agents: {response.status_code}")
            return [{"name": "research_assistant", "description": "Research assistant with web search"}]
    except Exception as e:
        st.error(f"Error fetching agents: {e}")
        return [{"name": "research_assistant", "description": "Research assistant with web search"}]


def show_authentication_required():
    """Show authentication required page."""
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.subheader("🔐 Authentication Required")
    
    st.markdown("""
    This application requires authentication to access your personal data and integrations.
    
    **Features available after login:**
    - Personal AI assistant with conversation history
    - Google Calendar integration for scheduling  
    - Weekly review and planning tools
    - Journaling and task management
    """)
    
    st.info("Please click the 'Sign in with Google' button in the top-right corner to continue.")


def setup_authenticated_user(user_info: Dict[str, Any]) -> str:
    """Set up authenticated user with backend and return user ID."""
    try:
        # For now, use email as user ID (in production, you'd have proper user mapping)
        user_id = user_info.get("email", "unknown_user")
        
        # Store user info in session state
        st.session_state["user_id"] = user_id
        st.session_state["user_email"] = user_info.get("email")
        st.session_state["user_name"] = user_info.get("name", "User")
        
        return user_id
        
    except Exception as e:
        st.error(f"Error setting up user: {e}")
        return "unknown_user"


def show_oauth_configuration(user_email: str):
    """Show OAuth configuration in a modal-like expander."""
    with st.expander("🔗 OAuth Configuration", expanded=False):
        st.markdown("### 🔗 External Integrations")
        st.caption("Configure OAuth connections for enhanced weekly reviews")
        
        # Todoist Integration
        st.markdown("#### 📝 Todoist Integration")
        st.warning("⚠️ Not connected to Todoist")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔗 Connect Todoist Account"):
                st.info("Todoist integration would be implemented here")
        with col2:
            if st.button("📊 Show Todoist Details"):
                st.info("Todoist details would be shown here")
        
        # Google Calendar Integration  
        st.markdown("#### 📅 Google Calendar Integration")
        st.success("✅ 1 Google account(s) connected")
        st.caption("Using the same Google account as your login")


def show_authenticated_app(user_info: Dict[str, Any]):
    """Show the main application for authenticated users."""
    # Set up user
    user_id = setup_authenticated_user(user_info)
    
    st.title(f"{APP_ICON} {APP_TITLE}")
    
    # Sidebar with user info and controls
    with st.sidebar:
        st.markdown("### 👤 Logged in as:")
        st.markdown(f"📧 {user_info.get('email', 'Unknown')}")
        st.markdown(f"👋 {user_info.get('name', 'User')}")
        
        if st.button("📋 Logout", use_container_width=True):
            # Use Streamlit's logout functionality
            st.session_state.clear()
            st.rerun()
        
        if st.button("💬 New Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        
        # Settings
        with st.expander("⚙️ Settings"):
            # Get available agents
            agents = get_available_agents()
            agent_names = [agent.get("name", "unknown") for agent in agents]
            
            selected_agent = st.selectbox(
                "🤖 Agent", 
                options=agent_names,
                index=0 if agent_names else 0,
                key="selected_agent"
            )
            
            selected_model = st.selectbox(
                "🧠 Model", 
                options=["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"],
                index=0,
                key="selected_model"
            )
        
        # OAuth Configuration
        show_oauth_configuration(user_info.get('email'))
    
    # Main chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Welcome message
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown("👋 Hello! I'm an AI-powered research assistant with web search and a calculator. Ask me anything!")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Your message"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Add assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Placeholder response - in real implementation, this would call the agent
                response = f"I received your message: '{prompt}'. This is a placeholder response using the official Streamlit authentication!"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})


async def main():
    """Main application entry point with official Google authentication."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Hide Streamlit branding
    st.markdown("""
    <style>
    [data-testid="stStatusWidget"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Configure Google authentication
    st.auth_config = {
        "client_id": st.secrets["google_oauth"]["client_id"],
        "redirect_uri": st.secrets["google_oauth"]["redirect_uri"]
    }
    
    # Check authentication using Streamlit's official authentication
    if st.user_info:
        # User is authenticated
        show_authenticated_app(st.user_info)
    else:
        # User is not authenticated
        show_authentication_required()


if __name__ == "__main__":
    asyncio.run(main())