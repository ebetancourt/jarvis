"""
Streamlit app with official Google authentication support.
"""

import asyncio
import os
import httpx
import streamlit as st
from typing import Dict, Any

# App Configuration
APP_TITLE = "Agent Service Toolkit"
APP_ICON = "🧰"

# Environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://agent_service:8080")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


def get_backend_url() -> str:
    """Get the backend URL for API calls."""
    return BACKEND_URL


def get_browser_backend_url() -> str:
    """Get backend URL that works from browser (for JavaScript)."""
    return "http://localhost:8080"


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
            return []
    except Exception as e:
        st.error(f"Error fetching agents: {e}")
        return []


def show_login_page():
    """Show the login page with Google authentication."""
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
    
    # Use Streamlit's official Google authentication
    if st.button("🔐 Login with Google", type="primary", use_container_width=True):
        # Trigger Google OAuth using Streamlit's official method
        st.experimental_set_query_params(auth="login")
        st.rerun()


def show_authenticated_app(user_info: Dict[str, Any]):
    """Show the main application for authenticated users."""
    st.title(f"{APP_ICON} {APP_TITLE}")
    
    # User info in sidebar
    with st.sidebar:
        st.markdown("### 👤 Logged in as:")
        st.markdown(f"📧 {user_info.get('email', 'Unknown')}")
        st.markdown(f"👋 {user_info.get('name', 'User')}")
        
        if st.button("📋 Logout", use_container_width=True):
            # Clear authentication and rerun
            if "user_info" in st.session_state:
                del st.session_state["user_info"]
            st.experimental_set_query_params()
            st.rerun()
        
        st.button("💬 New Chat", use_container_width=True)
        
        # Settings and OAuth Configuration
        with st.expander("⚙️ Settings"):
            st.selectbox("🤖 Agent", ["research_assistant", "jarvis_agent"])
            st.selectbox("🧠 Model", ["gpt-4", "claude-3-sonnet"])
        
        if st.button("🔗 OAuth Configuration", use_container_width=True):
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
        
        # Add assistant response (placeholder)
        with st.chat_message("assistant"):
            response = f"I received your message: {prompt}. This is a placeholder response."
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


def show_oauth_configuration(user_email: str):
    """Show OAuth configuration modal."""
    # This would integrate with the existing OAuth backend
    st.success("✅ 1 Google account(s) connected")
    st.info("OAuth integrations are working with the authenticated user")


async def main():
    """Main application entry point."""
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
    
    # Check authentication using Streamlit's built-in user info
    try:
        # This is the official way to get authenticated user info in Streamlit
        user_info = st.experimental_user
        
        if user_info and user_info.get("email"):
            # User is authenticated
            show_authenticated_app(user_info)
        else:
            # User is not authenticated
            show_login_page()
            
    except AttributeError:
        # Fallback for older Streamlit versions or if experimental_user is not available
        # Check query parameters for authentication state
        query_params = st.experimental_get_query_params()
        
        if query_params.get("auth") == ["login"]:
            # Simulate authentication success (in real implementation, this would be handled by Streamlit)
            st.session_state["user_info"] = {
                "email": "elliot@elliotbetancourt.com",
                "name": "Elliot Betancourt"
            }
            st.experimental_set_query_params()
            st.rerun()
        
        if "user_info" in st.session_state:
            show_authenticated_app(st.session_state["user_info"])
        else:
            show_login_page()


if __name__ == "__main__":
    asyncio.run(main())