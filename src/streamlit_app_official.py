"""
Agent Service Toolkit - Official Streamlit Google Authentication

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
            return [{"name": "research_assistant", "description": "Research assistant with web search"}]
    except Exception:
        return [{"name": "research_assistant", "description": "Research assistant with web search"}]


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
    
    # Official Streamlit Google authentication
    if st.button("🔐 Login with Google", type="primary", use_container_width=True):
        st.login()


def show_oauth_configuration():
    """Show OAuth configuration in an expander."""
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


def show_authenticated_app():
    """Show the main application for authenticated users."""
    st.title(f"{APP_ICON} {APP_TITLE}")
    
    # Sidebar with user info and controls
    with st.sidebar:
        st.markdown("### 👤 Logged in as:")
        st.markdown(f"📧 {st.user.email}")
        st.markdown(f"👋 {st.user.name}")
        
        if st.button("📋 Logout", use_container_width=True):
            st.logout()
        
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
        show_oauth_configuration()
    
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
                response = f"Hello {st.user.name}! I received your message: '{prompt}'. This is using official Streamlit authentication!"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})


def main():
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
    
    # Check authentication using Streamlit's official authentication
    if st.user.is_logged_in:
        # User is authenticated
        show_authenticated_app()
    else:
        # User is not authenticated
        show_login_page()


if __name__ == "__main__":
    main()