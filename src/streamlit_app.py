import asyncio
import os
import urllib.parse
import uuid
from collections.abc import AsyncGenerator
# OAuth types removed - will use API responses directly

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from client import AgentClient, AgentClientError
from schema import ChatHistory, ChatMessage
from schema.task_data import TaskData, TaskDataStatus

# A Streamlit app for interacting with the langgraph agent via a simple chat interface.
# The app has three main functions which are all run async:

# - main() - sets up the streamlit app and high level structure
# - draw_messages() - draws a set of chat messages - either replaying existing messages
#   or streaming new ones.
# - handle_feedback() - Draws a feedback widget and records feedback from the user.

# The app heavily uses AgentClient to interact with the agent's FastAPI endpoints.


APP_TITLE = "Agent Service Toolkit"
APP_ICON = "🧰"
USER_ID_COOKIE = "user_id"


def get_or_create_user_id() -> str:
    """Get the user ID from session state or URL parameters, or create a new one if it doesn't exist."""
    # Check if user_id exists in session state
    if USER_ID_COOKIE in st.session_state:
        return st.session_state[USER_ID_COOKIE]

    # Try to get from URL parameters using the new st.query_params
    if USER_ID_COOKIE in st.query_params:
        user_id = st.query_params[USER_ID_COOKIE]
        st.session_state[USER_ID_COOKIE] = user_id
        return user_id

    # Generate a new user_id if not found
    user_id = str(uuid.uuid4())

    # Store in session state for this session
    st.session_state[USER_ID_COOKIE] = user_id

    # Also add to URL parameters so it can be bookmarked/shared
    st.query_params[USER_ID_COOKIE] = user_id

    return user_id


# OAuth callback handling will be moved to backend API


# OAuth status loading will be handled via API calls to backend


# TODO: Replace with API calls to backend service
# The following OAuth functions will be reimplemented as HTTP client calls:
# - start_google_oauth() -> POST /api/oauth/google/start
# - start_todoist_oauth() -> POST /api/oauth/todoist/start
# - disconnect_google_account() -> DELETE /api/oauth/disconnect/google/{user_id}
# - disconnect_todoist() -> DELETE /api/oauth/disconnect/todoist/{user_id}
# - test_google_connection() -> GET /api/oauth/test/google/{user_id}
# - test_todoist_connection() -> GET /api/oauth/test/todoist/{user_id}
# - refresh_google_account() -> POST /api/oauth/refresh/google/{user_id}
# - refresh_todoist_account() -> POST /api/oauth/refresh/todoist/{user_id}
# - get_account_health_display() -> GET /api/oauth/health/{service}/{user_id}
# - show_service_summary() -> GET /api/oauth/summary/{service}
# - fetch_google_calendars() -> GET /api/calendars/{user_id}
# - update_calendar_selection() -> PUT /api/calendars/{user_id}/preferences
# - get_calendar_summary() -> GET /api/calendars/{user_id}/summary
# - load_oauth_status() -> GET /api/oauth/status/{user_id}


# OAuth HTTP Client Functions for Backend API
def get_backend_url() -> str:
    """Get the backend service URL."""
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", 8080)
    return f"http://{host}:{port}"


def call_oauth_status_api(user_id: str) -> dict:
    """Call backend API to get OAuth status for a user."""
    try:
        backend_url = get_backend_url()
        response = st.session_state.agent_client._client.get(
            f"{backend_url}/api/oauth/status/{user_id}"
        )
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
        response = st.session_state.agent_client._client.post(
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
        response = st.session_state.agent_client._client.delete(
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


def call_oauth_refresh_api(service: str, user_id: str) -> bool:
    """Call backend API to refresh OAuth token."""
    try:
        backend_url = get_backend_url()
        response = st.session_state.agent_client._client.post(
            f"{backend_url}/api/oauth/refresh/{service}/{user_id}"
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False)
        else:
            st.error(f"Failed to refresh {service} token: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error refreshing {service} token: {e}")
        return False


def call_oauth_health_api(service: str, user_id: str) -> dict:
    """Call backend API to get OAuth health status."""
    try:
        backend_url = get_backend_url()
        response = st.session_state.agent_client._client.get(
            f"{backend_url}/api/oauth/health/{service}/{user_id}"
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "icon": "🔴",
                "message": f"API error: {response.status_code}",
                "can_refresh": False,
            }
    except Exception as e:
        return {
            "status": "error",
            "icon": "🔴",
            "message": f"Error: {e}",
            "can_refresh": False,
        }


def call_oauth_summary_api(service: str) -> dict:
    """Call backend API to get service summary."""
    try:
        backend_url = get_backend_url()
        response = st.session_state.agent_client._client.get(
            f"{backend_url}/api/oauth/summary/{service}"
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "total_accounts": 0,
                "healthy_accounts": 0,
                "expired_accounts": 0,
                "service_status": "error",
            }
    except Exception as e:
        st.error(f"Error getting {service} summary: {e}")
        return {
            "total_accounts": 0,
            "healthy_accounts": 0,
            "expired_accounts": 0,
            "service_status": "error",
        }


def call_calendars_api(user_id: str) -> list:
    """Call backend API to get calendars for a user."""
    try:
        backend_url = get_backend_url()
        response = st.session_state.agent_client._client.get(
            f"{backend_url}/api/calendars/{user_id}"
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("calendars", [])
        else:
            st.error(f"Failed to get calendars: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error getting calendars: {e}")
        return []


def call_calendar_summary_api(user_id: str) -> dict:
    """Call backend API to get calendar summary."""
    try:
        backend_url = get_backend_url()
        response = st.session_state.agent_client._client.get(
            f"{backend_url}/api/calendars/{user_id}/summary"
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"enabled": 0, "total": 0}
    except Exception as e:
        return {"enabled": 0, "total": 0}


def call_update_calendar_preferences_api(user_id: str, preferences: list) -> bool:
    """Call backend API to update calendar preferences."""
    try:
        backend_url = get_backend_url()
        response = st.session_state.agent_client._client.put(
            f"{backend_url}/api/calendars/{user_id}/preferences",
            json={"calendar_preferences": preferences},
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False)
        else:
            st.error(f"Failed to update calendar preferences: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error updating calendar preferences: {e}")
        return False


def load_oauth_status_from_api(user_id: str) -> None:
    """Load OAuth status from backend API and store in session state."""
    try:
        status_data = call_oauth_status_api(user_id)

        # Initialize session state for OAuth status
        if "oauth_status" not in st.session_state:
            st.session_state.oauth_status = {
                "todoist": {"connected": False, "user_email": None},
                "google_accounts": [],
            }

        # Update with API data
        st.session_state.oauth_status = status_data

    except Exception as e:
        st.error(f"Error loading OAuth status: {e}")
        # Initialize with default values on error
        st.session_state.oauth_status = {
            "todoist": {"connected": False, "user_email": None},
            "google_accounts": [],
        }


def start_todoist_oauth_flow(user_id: str) -> None:
    """Start Todoist OAuth flow using backend API."""
    result = call_oauth_start_api("todoist", user_id)
    if result:
        auth_url = result["authorization_url"]
        st.markdown(
            f'<a href="{auth_url}" target="_self">Click here to authorize Todoist access</a>',
            unsafe_allow_html=True,
        )
        st.info(
            "You will be redirected to Todoist to authorize access. Please complete the authorization and return here."
        )
    else:
        st.error("Failed to start Todoist OAuth flow.")


def start_google_oauth_flow(user_id: str) -> None:
    """Start Google OAuth flow using backend API."""
    result = call_oauth_start_api("google", user_id)
    if result:
        auth_url = result["authorization_url"]
        st.markdown(
            f'<a href="{auth_url}" target="_self">Click here to authorize Google Calendar access</a>',
            unsafe_allow_html=True,
        )
        st.info(
            "You will be redirected to Google to authorize access. Please complete the authorization and return here."
        )
    else:
        st.error("Failed to start Google OAuth flow.")


def disconnect_todoist_account(user_id: str) -> bool:
    """Disconnect Todoist account using backend API."""
    success = call_oauth_disconnect_api("todoist", user_id)
    if success:
        st.success("✅ Disconnected from Todoist")
        return True
    else:
        st.error("❌ Failed to disconnect from Todoist")
        return False


def disconnect_google_account_by_email(user_id: str, account_email: str) -> bool:
    """Disconnect Google account using backend API."""
    # Find the Google user ID for this email
    google_accounts = st.session_state.oauth_status.get("google_accounts", [])
    for account in google_accounts:
        if account.get("email") == account_email:
            google_user_id = account.get("user_id")
            if google_user_id:
                success = call_oauth_disconnect_api("google", google_user_id)
                if success:
                    st.success(f"✅ Disconnected Google account: {account_email}")
                    return True
                else:
                    st.error(f"❌ Failed to disconnect Google account: {account_email}")
                    return False

    st.error(f"❌ Could not find Google account: {account_email}")
    return False


def refresh_todoist_token(user_id: str) -> bool:
    """Refresh Todoist token using backend API."""
    success = call_oauth_refresh_api("todoist", user_id)
    if success:
        st.success("✅ Todoist token refreshed successfully!")
        return True
    else:
        st.error("❌ Failed to refresh Todoist token")
        return False


def refresh_google_token(google_user_id: str) -> bool:
    """Refresh Google token using backend API."""
    success = call_oauth_refresh_api("google", google_user_id)
    if success:
        st.success("✅ Google token refreshed successfully!")
        return True
    else:
        st.error("❌ Failed to refresh Google token")
        return False


def test_oauth_connection(service: str, user_id: str) -> bool:
    """Test OAuth connection using backend API."""
    health = call_oauth_health_api(service, user_id)
    if health["status"] == "healthy":
        st.success(f"✅ {service.title()} connection working!")
        return True
    elif health["status"] == "error":
        st.error(f"❌ {service.title()} connection failed")
        return False
    else:
        st.warning(f"⚠️ {service.title()} connection status: {health['message']}")
        return False


def show_service_summary_from_api(service: str) -> None:
    """Show service summary using backend API."""
    summary = call_oauth_summary_api(service)

    service_name = service.title()
    total = summary["total_accounts"]
    healthy = summary["healthy_accounts"]
    expired = summary["expired_accounts"]

    if total == 0:
        st.info(f"No {service_name} accounts connected")
        return

    status_color = "🟢" if summary["service_status"] == "healthy" else "🟡"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Accounts", total)
    with col2:
        st.metric("Healthy", healthy, delta=None if healthy == total else f"-{expired}")
    with col3:
        st.write(f"**Status:** {status_color} {summary['service_status'].title()}")

    if expired > 0:
        st.warning(f"⚠️ {expired} account(s) need attention")


async def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        menu_items={},
    )

    # Hide the streamlit upper-right chrome
    st.html(
        """
        <style>
        [data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
            }
        </style>
        """,
    )
    if st.get_option("client.toolbarMode") != "minimal":
        st.set_option("client.toolbarMode", "minimal")
        await asyncio.sleep(0.1)
        st.rerun()

    # Get or create user ID
    user_id = get_or_create_user_id()

    # Initialize agent client first
    if "agent_client" not in st.session_state:
        load_dotenv()
        agent_url = os.getenv("AGENT_URL")
        if not agent_url:
            host = os.getenv("HOST", "0.0.0.0")
            port = os.getenv("PORT", 8080)
            agent_url = f"http://{host}:{port}"
        try:
            with st.spinner("Connecting to agent service..."):
                st.session_state.agent_client = AgentClient(base_url=agent_url)
        except AgentClientError as e:
            st.error(f"Error connecting to agent service at {agent_url}: {e}")
            st.markdown("The service might be booting up. Try again in a few seconds.")
            st.stop()
    agent_client: AgentClient = st.session_state.agent_client

    # Load OAuth status from backend API (requires agent_client to be initialized)
    load_oauth_status_from_api(user_id)

    # TODO: OAuth callback handling will be done via backend API

    if "thread_id" not in st.session_state:
        thread_id = st.query_params.get("thread_id")
        if not thread_id:
            thread_id = str(uuid.uuid4())
            messages = []
        else:
            try:
                messages: ChatHistory = agent_client.get_history(thread_id=thread_id).messages
            except AgentClientError:
                st.error("No message history found for this Thread ID.")
                messages = []
        st.session_state.messages = messages
        st.session_state.thread_id = thread_id

    # Config options
    with st.sidebar:
        st.header(f"{APP_ICON} {APP_TITLE}")

        ""
        "Full toolkit for running an AI agent service built with LangGraph, FastAPI and Streamlit"
        ""

        if st.button(":material/chat: New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

        with st.popover(":material/settings: Settings", use_container_width=True):
            model_idx = agent_client.info.models.index(agent_client.info.default_model)
            model = st.selectbox("LLM to use", options=agent_client.info.models, index=model_idx)
            agent_list = [a.key for a in agent_client.info.agents]
            agent_idx = agent_list.index(agent_client.info.default_agent)
            agent_client.agent = st.selectbox(
                "Agent to use",
                options=agent_list,
                index=agent_idx,
            )
            use_streaming = st.toggle("Stream results", value=True)

            # Display user ID (for debugging or user information)
            st.text_input("User ID (read-only)", value=user_id, disabled=True)

        # OAuth Configuration Section for Weekly Review Agent
        with st.popover(
            ":material/sync: OAuth Configuration", use_container_width=True
        ):
            st.subheader("🔗 External Integrations")
            st.caption("Configure OAuth connections for enhanced weekly reviews")

            # OAuth status is loaded by load_oauth_status_from_api function

            # Todoist Configuration Section
            st.write("### 📋 Todoist Integration")

            todoist_status = st.session_state.oauth_status["todoist"]
            if todoist_status["connected"]:
                # Get health information
                health = call_oauth_health_api("todoist", user_id)

                # Display status with health indicator
                st.success(
                    f"{health['icon']} Connected as: {todoist_status['user_email']}"
                )
                st.caption(f"Status: {health['message']}")

                if health.get("expires_display"):
                    st.caption(f"Token expires in: {health['expires_display']}")

                # Action buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🔄 Test", key="todoist_test"):
                        test_oauth_connection("todoist", user_id)
                with col2:
                    if st.button("🔃 Refresh", key="todoist_refresh"):
                        if refresh_todoist_token(user_id):
                            st.rerun()
                with col3:
                    if st.button("❌ Remove", key="todoist_disconnect"):
                        if disconnect_todoist_account(user_id):
                            st.rerun()

                # Show warning if token needs attention
                if health["status"] in ["expired", "expiring_soon", "invalid"]:
                    if health["can_refresh"]:
                        st.warning("⚠️ Token needs refresh")
                    else:
                        st.error("🔴 Token expired - reconnection required")
            else:
                st.warning("⚠️ Not connected to Todoist")
                if st.button("🔗 Connect Todoist Account", key="todoist_connect"):
                    start_todoist_oauth_flow(user_id)

            # Show Todoist service summary
            if st.button("📊 Show Todoist Details", key="todoist_summary"):
                show_service_summary_from_api("todoist")

            st.divider()

            # Google Calendar Configuration Section
            st.write("### 📅 Google Calendar Integration")

            google_accounts = st.session_state.oauth_status["google_accounts"]
            if google_accounts:
                st.success(f"✅ {len(google_accounts)} Google account(s) connected")

                for i, account in enumerate(google_accounts):
                    with st.expander(f"📧 {account['email']}", expanded=False):
                        st.write(f"**Account:** {account['email']}")

                        # Get calendar summary
                        calendar_summary = call_calendar_summary_api(account["user_id"])
                        if calendar_summary["total"] > 0:
                            st.write(
                                f"**Calendars:** {calendar_summary['enabled']}/"
                                f"{calendar_summary['total']} enabled"
                            )
                        else:
                            st.write("**Calendars:** Not loaded")

                        # Calendar Configuration Section
                        with st.container():
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                if st.button(
                                    "📅 Configure Calendars", key=f"google_config_{i}"
                                ):
                                    st.session_state[f"show_calendar_config_{i}"] = True

                            with col2:
                                if st.button("🔄 Test", key=f"google_test_{i}"):
                                    test_oauth_connection("google", account["user_id"])

                        # Simplified Calendar Configuration Interface
                        if st.session_state.get(f"show_calendar_config_{i}", False):
                            with st.expander(
                                "📅 Calendar Configuration", expanded=True
                            ):
                                col_close, _ = st.columns([1, 4])
                                with col_close:
                                    if st.button(
                                        "❌ Close", key=f"close_cal_config_{i}"
                                    ):
                                        st.session_state[
                                            f"show_calendar_config_{i}"
                                        ] = False
                                        st.rerun()

                                st.info(
                                    "📅 Calendar management will be available when backend APIs are implemented."
                                )

                                # Basic calendar information
                                with st.spinner("Loading calendar info..."):
                                    calendars = call_calendars_api(account["user_id"])

                                if calendars:
                                    st.success(f"✅ Found {len(calendars)} calendars")

                                    # Simple calendar list
                                    for calendar in calendars[
                                        :5
                                    ]:  # Show first 5 calendars
                                        calendar_name = calendar.get(
                                            "summary", "Unnamed Calendar"
                                        )
                                        access_role = calendar.get(
                                            "accessRole", "unknown"
                                        )
                                        st.write(f"**{calendar_name}** ({access_role})")

                                    if len(calendars) > 5:
                                        st.caption(
                                            f"... and {len(calendars) - 5} more calendars"
                                        )

                                else:
                                    st.warning("⚠️ No calendars found or failed to load")

                        # Account Management Actions
                        st.divider()
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            if st.button("🔄 Refresh", key=f"google_refresh_{i}"):
                                if refresh_google_token(account["user_id"]):
                                    st.rerun()

                        with col2:
                            if st.button("🔃 Reload Calendars", key=f"reload_cal_{i}"):
                                with st.spinner("Reloading calendars..."):
                                    calendars = call_calendars_api(account["user_id"])
                                    if calendars:
                                        st.success("✅ Calendars reloaded")
                                    else:
                                        st.error("❌ Failed to reload calendars")

                        with col3:
                            if st.button("❌ Remove", key=f"google_disconnect_{i}"):
                                if disconnect_google_account_by_email(
                                    user_id, account["email"]
                                ):
                                    st.rerun()

            else:
                st.warning("⚠️ No Google accounts connected")
                if st.button("🔗 Connect Google Account", key="google_connect"):
                    start_google_oauth_flow(user_id)

            # Show Google service summary
            if st.button("📊 Show Google Details", key="google_summary"):
                show_service_summary_from_api("google")

            st.divider()

            # OAuth Status Summary
            st.write("### 📊 Integration Status")
            integrations_connected = 0
            total_integrations = 2

            if todoist_status["connected"]:
                integrations_connected += 1
            if google_accounts:
                integrations_connected += 1

            # Overall status display
            col1, col2 = st.columns([2, 1])
            with col1:
                if integrations_connected == 0:
                    st.error("❌ No integrations configured")
                    st.caption("Weekly reviews will use manual reflection methods")
                elif integrations_connected == total_integrations:
                    st.success("🎉 All integrations connected!")
                    st.caption("Weekly reviews will have full data access")
                else:
                    st.warning(
                        f"⚠️ {integrations_connected}/{total_integrations} "
                        "integrations connected"
                    )
                    st.caption(
                        "Weekly reviews will use available data + manual methods"
                    )

            with col2:
                # Account management actions
                if st.button("🔄 Refresh All", key="refresh_all_accounts"):
                    refresh_count = 0
                    if todoist_status["connected"]:
                        if refresh_todoist_token(user_id):
                            refresh_count += 1

                    for account in google_accounts:
                        if refresh_google_token(account["user_id"]):
                            refresh_count += 1

                    if refresh_count > 0:
                        st.success(f"✅ Refreshed {refresh_count} account(s)")
                        st.rerun()
                    else:
                        st.error("❌ No accounts could be refreshed")

            # Service health overview
            if integrations_connected > 0:
                with st.expander("🔍 Service Health Details"):
                    if todoist_status["connected"]:
                        st.write("**Todoist Service:**")
                        show_service_summary_from_api("todoist")
                        st.divider()

                    if google_accounts:
                        st.write("**Google Calendar Service:**")
                        show_service_summary_from_api("google")
                        st.divider()

                    # Database information
                    st.write("**🗄️ OAuth Database:**")
                    st.info(
                        "Database information will be available when backend APIs are fully implemented."
                    )

                    # Placeholder for future database info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Storage Type", "Backend API")
                    with col2:
                        st.metric("Connected Services", integrations_connected)

            # Test Connection Button
            if integrations_connected > 0:
                if st.button("🧪 Test Connections", key="test_connections"):
                    with st.spinner("Testing connections..."):
                        results = []

                        # Test Todoist if connected
                        if todoist_status["connected"]:
                            if test_oauth_connection("todoist", user_id):
                                results.append("✅ Todoist: Working")
                            else:
                                results.append("❌ Todoist: Failed")

                        # Test Google accounts if connected
                        if google_accounts:
                            for account in google_accounts:
                                if test_oauth_connection("google", account["user_id"]):
                                    results.append(
                                        f"✅ Google ({account['email']}): Working"
                                    )
                                else:
                                    results.append(
                                        f"❌ Google ({account['email']}): Failed"
                                    )

                        if results:
                            for result in results:
                                st.write(result)

        @st.dialog("Architecture")
        def architecture_dialog() -> None:
            st.image(
                "https://github.com/JoshuaC215/agent-service-toolkit/blob/main/media/agent_architecture.png?raw=true"
            )
            "[View full size on Github](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/media/agent_architecture.png)"
            st.caption(
                "App hosted on [Streamlit Cloud](https://share.streamlit.io/) with FastAPI service running in [Azure](https://learn.microsoft.com/en-us/azure/app-service/)"
            )

        if st.button(":material/schema: Architecture", use_container_width=True):
            architecture_dialog()

        with st.popover(":material/policy: Privacy", use_container_width=True):
            st.write(
                "Prompts, responses and feedback in this app are anonymously recorded and saved to LangSmith for product evaluation and improvement purposes only."
            )

        @st.dialog("Share/resume chat")
        def share_chat_dialog() -> None:
            session = st.runtime.get_instance()._session_mgr.list_active_sessions()[0]
            st_base_url = urllib.parse.urlunparse(
                [session.client.request.protocol, session.client.request.host, "", "", "", ""]
            )
            # if it's not localhost, switch to https by default
            if not st_base_url.startswith("https") and "localhost" not in st_base_url:
                st_base_url = st_base_url.replace("http", "https")
            # Include both thread_id and user_id in the URL for sharing to maintain user identity
            chat_url = (
                f"{st_base_url}?thread_id={st.session_state.thread_id}&{USER_ID_COOKIE}={user_id}"
            )
            st.markdown(f"**Chat URL:**\n```text\n{chat_url}\n```")
            st.info("Copy the above URL to share or revisit this chat")

        if st.button(":material/upload: Share/resume chat", use_container_width=True):
            share_chat_dialog()

        "[View the source code](https://github.com/JoshuaC215/agent-service-toolkit)"
        st.caption(
            "Made with :material/favorite: by [Joshua](https://www.linkedin.com/in/joshua-k-carroll/) in Oakland"
        )

    # Draw existing messages
    messages: list[ChatMessage] = st.session_state.messages

    if len(messages) == 0:
        match agent_client.agent:
            case "chatbot":
                WELCOME = "Hello! I'm a simple chatbot. Ask me anything!"
            case "interrupt-agent":
                WELCOME = "Hello! I'm an interrupt agent. Tell me your birthday and I will predict your personality!"
            case "research-assistant":
                WELCOME = "Hello! I'm an AI-powered research assistant with web search and a calculator. Ask me anything!"
            case "rag-assistant":
                WELCOME = """Hello! I'm an AI-powered Company Policy & HR assistant with access to AcmeTech's Employee Handbook.
                I can help you find information about benefits, remote work, time-off policies, company values, and more. Ask me anything!"""
            case "journaling-agent":
                WELCOME = "Hello! I'm a journaling agent. I can help you journal your thoughts and feelings."
            case "jarvis":
                WELCOME = "Hello! I'm Jarvis, Just a Rather Very Intelligent System. How can I help you today?"
            case _:
                WELCOME = "Hello! I'm an AI agent. Ask me anything!"

        with st.chat_message("ai"):
            st.write(WELCOME)

    # draw_messages() expects an async iterator over messages
    async def amessage_iter() -> AsyncGenerator[ChatMessage, None]:
        for m in messages:
            yield m

    await draw_messages(amessage_iter())

    # Generate new message if the user provided new input
    if user_input := st.chat_input():
        messages.append(ChatMessage(type="human", content=user_input))
        st.chat_message("human").write(user_input)
        try:
            if use_streaming:
                stream = agent_client.astream(
                    message=user_input,
                    model=model,
                    thread_id=st.session_state.thread_id,
                    user_id=user_id,
                )
                await draw_messages(stream, is_new=True)
            else:
                response = await agent_client.ainvoke(
                    message=user_input,
                    model=model,
                    thread_id=st.session_state.thread_id,
                    user_id=user_id,
                )
                messages.append(response)
                st.chat_message("ai").write(response.content)
            st.rerun()  # Clear stale containers
        except AgentClientError as e:
            st.error(f"Error generating response: {e}")
            st.stop()

    # If messages have been generated, show feedback widget
    if len(messages) > 0 and st.session_state.last_message:
        with st.session_state.last_message:
            await handle_feedback()


async def draw_messages(
    messages_agen: AsyncGenerator[ChatMessage | str, None],
    is_new: bool = False,
) -> None:
    """
    Draws a set of chat messages - either replaying existing messages
    or streaming new ones.

    This function has additional logic to handle streaming tokens and tool calls.
    - Use a placeholder container to render streaming tokens as they arrive.
    - Use a status container to render tool calls. Track the tool inputs and outputs
      and update the status container accordingly.

    The function also needs to track the last message container in session state
    since later messages can draw to the same container. This is also used for
    drawing the feedback widget in the latest chat message.

    Args:
        messages_aiter: An async iterator over messages to draw.
        is_new: Whether the messages are new or not.
    """

    # Keep track of the last message container
    last_message_type = None
    st.session_state.last_message = None

    # Placeholder for intermediate streaming tokens
    streaming_content = ""
    streaming_placeholder = None

    # Iterate over the messages and draw them
    while msg := await anext(messages_agen, None):
        # str message represents an intermediate token being streamed
        if isinstance(msg, str):
            # If placeholder is empty, this is the first token of a new message
            # being streamed. We need to do setup.
            if not streaming_placeholder:
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")
                with st.session_state.last_message:
                    streaming_placeholder = st.empty()

            streaming_content += msg
            streaming_placeholder.write(streaming_content)
            continue
        if not isinstance(msg, ChatMessage):
            st.error(f"Unexpected message type: {type(msg)}")
            st.write(msg)
            st.stop()

        match msg.type:
            # A message from the user, the easiest case
            case "human":
                last_message_type = "human"
                st.chat_message("human").write(msg.content)

            # A message from the agent is the most complex case, since we need to
            # handle streaming tokens and tool calls.
            case "ai":
                # If we're rendering new messages, store the message in session state
                if is_new:
                    st.session_state.messages.append(msg)

                # If the last message type was not AI, create a new chat message
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")

                with st.session_state.last_message:
                    # If the message has content, write it out.
                    # Reset the streaming variables to prepare for the next message.
                    if msg.content:
                        if streaming_placeholder:
                            streaming_placeholder.write(msg.content)
                            streaming_content = ""
                            streaming_placeholder = None
                        else:
                            st.write(msg.content)

                    if msg.tool_calls:
                        # Create a status container for each tool call and store the
                        # status container by ID to ensure results are mapped to the
                        # correct status container.
                        call_results = {}
                        for tool_call in msg.tool_calls:
                            status = st.status(
                                f"""Tool Call: {tool_call["name"]}""",
                                state="running" if is_new else "complete",
                            )
                            call_results[tool_call["id"]] = status
                            status.write("Input:")
                            status.write(tool_call["args"])

                        # Expect one ToolMessage for each tool call.
                        for _ in range(len(call_results)):
                            tool_result: ChatMessage = await anext(messages_agen)

                            if tool_result.type != "tool":
                                st.error(f"Unexpected ChatMessage type: {tool_result.type}")
                                st.write(tool_result)
                                st.stop()

                            # Record the message if it's new, and update the correct
                            # status container with the result
                            if is_new:
                                st.session_state.messages.append(tool_result)
                            if tool_result.tool_call_id:
                                status = call_results[tool_result.tool_call_id]
                            status.write("Output:")
                            status.write(tool_result.content)
                            status.update(state="complete")

            case "custom":
                # CustomData example used by the bg-task-agent
                # See:
                # - src/agents/utils.py CustomData
                # - src/agents/bg_task_agent/task.py
                try:
                    task_data: TaskData = TaskData.model_validate(msg.custom_data)
                except ValidationError:
                    st.error("Unexpected CustomData message received from agent")
                    st.write(msg.custom_data)
                    st.stop()

                if is_new:
                    st.session_state.messages.append(msg)

                if last_message_type != "task":
                    last_message_type = "task"
                    st.session_state.last_message = st.chat_message(
                        name="task", avatar=":material/manufacturing:"
                    )
                    with st.session_state.last_message:
                        status = TaskDataStatus()

                status.add_and_draw_task_data(task_data)

            # In case of an unexpected message type, log an error and stop
            case _:
                st.error(f"Unexpected ChatMessage type: {msg.type}")
                st.write(msg)
                st.stop()


async def handle_feedback() -> None:
    """Draws a feedback widget and records feedback from the user."""

    # Keep track of last feedback sent to avoid sending duplicates
    if "last_feedback" not in st.session_state:
        st.session_state.last_feedback = (None, None)

    latest_run_id = st.session_state.messages[-1].run_id
    feedback = st.feedback("stars", key=latest_run_id)

    # If the feedback value or run ID has changed, send a new feedback record
    if feedback is not None and (latest_run_id, feedback) != st.session_state.last_feedback:
        # Normalize the feedback value (an index) to a score between 0 and 1
        normalized_score = (feedback + 1) / 5.0

        agent_client: AgentClient = st.session_state.agent_client
        try:
            await agent_client.acreate_feedback(
                run_id=latest_run_id,
                key="human-feedback-stars",
                score=normalized_score,
                kwargs={"comment": "In-line human feedback"},
            )
        except AgentClientError as e:
            st.error(f"Error recording feedback: {e}")
            st.stop()
        st.session_state.last_feedback = (latest_run_id, feedback)
        st.toast("Feedback recorded", icon=":material/reviews:")


if __name__ == "__main__":
    asyncio.run(main())
