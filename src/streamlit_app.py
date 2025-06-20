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

    # TODO: OAuth callback handling will be done via backend API

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

            # OAuth status is loaded by load_oauth_status function

            # Todoist Configuration Section
            st.write("### 📋 Todoist Integration")

            todoist_status = st.session_state.oauth_status["todoist"]
            if todoist_status["connected"]:
                # Get health information
                user_id = get_or_create_user_id()
                health = get_account_health_display("todoist", user_id)

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
                        test_todoist_connection()
                with col2:
                    if st.button("🔃 Refresh", key="todoist_refresh"):
                        if refresh_todoist_account():
                            st.rerun()
                with col3:
                    if st.button("❌ Remove", key="todoist_disconnect"):
                        disconnect_todoist()
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
                    start_todoist_oauth()

            # Show Todoist service summary
            if st.button("📊 Show Todoist Details", key="todoist_summary"):
                show_service_summary("todoist")

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
                        calendar_summary = get_calendar_summary(account["user_id"])
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
                                    test_google_connection(account["email"])

                        # Enhanced Calendar Configuration Interface
                        if st.session_state.get(f"show_calendar_config_{i}", False):
                            with st.expander(
                                "📅 Calendar Selection & Filtering", expanded=True
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

                                with st.spinner("Loading calendars..."):
                                    all_calendars = fetch_google_calendars(
                                        account["user_id"]
                                    )

                                if all_calendars:
                                    # Calendar statistics
                                    stats = oauth_manager.get_calendar_statistics(
                                        all_calendars
                                    )

                                    col1_stat, col2_stat, col3_stat = st.columns(3)
                                    with col1_stat:
                                        st.metric("Total Calendars", stats["total"])
                                    with col2_stat:
                                        st.metric("Currently Enabled", stats["enabled"])
                                    with col3_stat:
                                        enabled_pct = (
                                            stats["enabled"] / stats["total"] * 100
                                            if stats["total"] > 0
                                            else 0
                                        )
                                        st.metric("Enabled %", f"{enabled_pct:.0f}%")

                                    # Filter presets
                                    st.write("**🔍 Quick Filters:**")
                                    presets = (
                                        oauth_manager.get_calendar_filter_presets()
                                    )

                                    # Create filter preset buttons
                                    preset_cols = st.columns(len(presets))
                                    selected_preset = None

                                    for idx, (preset_key, preset_data) in enumerate(
                                        presets.items()
                                    ):
                                        with preset_cols[idx]:
                                            if st.button(
                                                preset_data["name"],
                                                key=f"preset_{account['user_id']}_{preset_key}",
                                                help=preset_data["description"],
                                            ):
                                                selected_preset = preset_key

                                    # Apply filter if preset selected
                                    if selected_preset:
                                        if selected_preset == "all":
                                            filtered_calendars = all_calendars
                                        else:
                                            filter_config = presets[selected_preset][
                                                "filters"
                                            ]
                                            filtered_calendars = (
                                                oauth_manager.apply_calendar_filters(
                                                    all_calendars, filter_config
                                                )
                                            )

                                        # Update session state for display
                                        st.session_state[
                                            f"filtered_calendars_{account['user_id']}"
                                        ] = filtered_calendars
                                        st.success(
                                            f"Applied filter: {presets[selected_preset]['name']}"
                                        )

                                    # Use filtered calendars if available
                                    display_calendars = st.session_state.get(
                                        f"filtered_calendars_{account['user_id']}",
                                        all_calendars,
                                    )

                                    # Advanced filtering
                                    with st.expander(
                                        "🛠️ Advanced Filters", expanded=False
                                    ):
                                        st.write("**Custom Filter Options:**")

                                        # Access role filter
                                        access_roles = st.multiselect(
                                            "Access Roles",
                                            [
                                                "owner",
                                                "writer",
                                                "reader",
                                                "freeBusyReader",
                                            ],
                                            default=[
                                                "owner",
                                                "writer",
                                                "reader",
                                                "freeBusyReader",
                                            ],
                                            key=f"access_filter_{account['user_id']}",
                                        )

                                        # Calendar type filter
                                        calendar_types = st.multiselect(
                                            "Calendar Types",
                                            [
                                                "primary",
                                                "work",
                                                "personal",
                                                "holiday",
                                                "shared",
                                                "other",
                                            ],
                                            default=[
                                                "primary",
                                                "work",
                                                "personal",
                                                "holiday",
                                                "shared",
                                                "other",
                                            ],
                                            key=f"type_filter_{account['user_id']}",
                                        )

                                        # Keyword filters
                                        col_include, col_exclude = st.columns(2)
                                        with col_include:
                                            include_keywords = st.text_input(
                                                "Include Keywords (comma-separated)",
                                                key=f"include_filter_{account['user_id']}",
                                                placeholder="work, meeting, team",
                                            )
                                        with col_exclude:
                                            exclude_keywords = st.text_input(
                                                "Exclude Keywords (comma-separated)",
                                                key=f"exclude_filter_{account['user_id']}",
                                                placeholder="holiday, spam, test",
                                            )

                                        # Apply custom filter
                                        if st.button(
                                            "Apply Custom Filter",
                                            key=f"custom_filter_{account['user_id']}",
                                        ):
                                            custom_filters = {
                                                "access_roles": access_roles,
                                                "calendar_types": calendar_types,
                                            }

                                            if include_keywords:
                                                custom_filters["include_keywords"] = [
                                                    kw.strip()
                                                    for kw in include_keywords.split(
                                                        ","
                                                    )
                                                    if kw.strip()
                                                ]

                                            if exclude_keywords:
                                                custom_filters["exclude_keywords"] = [
                                                    kw.strip()
                                                    for kw in exclude_keywords.split(
                                                        ","
                                                    )
                                                    if kw.strip()
                                                ]

                                            filtered_calendars = (
                                                oauth_manager.apply_calendar_filters(
                                                    all_calendars, custom_filters
                                                )
                                            )
                                            st.session_state[
                                                f"filtered_calendars_{account['user_id']}"
                                            ] = filtered_calendars
                                            st.success(
                                                f"Applied custom filter. "
                                                f"Showing {len(filtered_calendars)} calendars."
                                            )

                                    # Bulk actions
                                    st.write("**📦 Bulk Actions:**")
                                    bulk_col1, bulk_col2, bulk_col3 = st.columns(3)

                                    with bulk_col1:
                                        if st.button(
                                            "✅ Enable All Visible",
                                            key=f"enable_all_{account['user_id']}",
                                        ):
                                            for calendar in display_calendars:
                                                update_calendar_selection(
                                                    account["user_id"],
                                                    calendar["id"],
                                                    True,
                                                )
                                            st.success("Enabled all visible calendars")
                                            st.rerun()

                                    with bulk_col2:
                                        if st.button(
                                            "❌ Disable All Visible",
                                            key=f"disable_all_{account['user_id']}",
                                        ):
                                            for calendar in display_calendars:
                                                update_calendar_selection(
                                                    account["user_id"],
                                                    calendar["id"],
                                                    False,
                                                )
                                            st.success("Disabled all visible calendars")
                                            st.rerun()

                                    with bulk_col3:
                                        if st.button(
                                            "🔄 Reset Filters",
                                            key=f"reset_filters_{account['user_id']}",
                                        ):
                                            if (
                                                f"filtered_calendars_{account['user_id']}"
                                                in st.session_state
                                            ):
                                                del st.session_state[
                                                    f"filtered_calendars_{account['user_id']}"
                                                ]
                                            st.success(
                                                "Filters reset - showing all calendars"
                                            )
                                            st.rerun()

                                    # Calendar list with filtering
                                    st.write("**📋 Calendar Selection:**")

                                    # Categories for better organization
                                    categories = oauth_manager.categorize_calendars(
                                        display_calendars
                                    )

                                    # Display calendars by category
                                    for category_name, calendars in categories.items():
                                        if calendars:
                                            with st.expander(
                                                f"📁 {category_name} ({len(calendars)})",
                                                expanded=category_name == "Primary",
                                            ):
                                                for calendar in calendars:
                                                    col_check, col_info = st.columns(
                                                        [1, 4]
                                                    )

                                                    with col_check:
                                                        enabled = st.checkbox(
                                                            "",
                                                            value=calendar.get(
                                                                "enabled", True
                                                            ),
                                                            key=f"cal_{account['user_id']}_{calendar['id']}",
                                                        )

                                                        # Update if changed
                                                        if enabled != calendar.get(
                                                            "enabled", True
                                                        ):
                                                            update_calendar_selection(
                                                                account["user_id"],
                                                                calendar["id"],
                                                                enabled,
                                                            )

                                                    with col_info:
                                                        calendar_name = calendar.get(
                                                            "summary",
                                                            "Unnamed Calendar",
                                                        )
                                                        access_role = calendar.get(
                                                            "accessRole", "unknown"
                                                        )

                                                        if calendar.get(
                                                            "primary", False
                                                        ):
                                                            calendar_name += (
                                                                " (Primary)"
                                                            )

                                                        st.write(f"**{calendar_name}**")
                                                        st.caption(
                                                            f"Access: {access_role} | "
                                                            f"ID: {calendar['id'][:20]}..."
                                                        )

                                                        if calendar.get("description"):
                                                            st.caption(
                                                                f"Description: {calendar['description'][:100]}..."
                                                            )
                                else:
                                    st.error("❌ Failed to load calendars")

                        # Account Management Actions
                        st.divider()
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            if st.button("🔄 Refresh", key=f"google_refresh_{i}"):
                                if refresh_google_account(account["user_id"]):
                                    st.rerun()

                        with col2:
                            if st.button("🔃 Reload Calendars", key=f"reload_cal_{i}"):
                                with st.spinner("Reloading calendars..."):
                                    calendars = fetch_google_calendars(
                                        account["user_id"]
                                    )
                                    if calendars:
                                        st.success("✅ Calendars reloaded")
                                    else:
                                        st.error("❌ Failed to reload calendars")

                        with col3:
                            if st.button("❌ Remove", key=f"google_disconnect_{i}"):
                                disconnect_google_account(account["email"])
                                st.rerun()

            else:
                st.warning("⚠️ No Google accounts connected")
                if st.button("🔗 Connect Google Account", key="google_connect"):
                    start_google_oauth()

            # Show Google service summary
            if st.button("📊 Show Google Details", key="google_summary"):
                show_service_summary("google")

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
                        if refresh_todoist_account():
                            refresh_count += 1

                    for account in google_accounts:
                        if refresh_google_account(account["user_id"]):
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
                        show_service_summary("todoist")
                        st.divider()

                    if google_accounts:
                        st.write("**Google Calendar Service:**")
                        show_service_summary("google")
                        st.divider()

                    # Database information
                    st.write("**🗄️ OAuth Database:**")
                    db_info = oauth_manager.get_database_info()

                    if db_info.get("database_enabled"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Storage Type", "Database")
                            if "tokens_by_service" in db_info:
                                for service, count in db_info[
                                    "tokens_by_service"
                                ].items():
                                    st.metric(f"{service.title()} Tokens", count)

                        with col2:
                            if "calendar_preferences" in db_info:
                                cal_stats = db_info["calendar_preferences"]
                                if cal_stats:
                                    st.metric(
                                        "Users with Calendars",
                                        cal_stats.get("users", 0),
                                    )
                                    st.metric(
                                        "Total Calendars",
                                        cal_stats.get("total_calendars", 0),
                                    )
                                    st.metric(
                                        "Enabled Calendars",
                                        cal_stats.get("enabled_calendars", 0),
                                    )

                            # Database size
                            if "database_size_bytes" in db_info:
                                size_mb = db_info["database_size_bytes"] / 1024 / 1024
                                st.metric("Database Size", f"{size_mb:.2f} MB")
                    else:
                        st.info("💾 Using file-based storage (legacy mode)")
                        st.caption("OAuth tokens stored in JSON files")

            # Test Connection Button
            if integrations_connected > 0:
                if st.button("🧪 Test Connections", key="test_connections"):
                    with st.spinner("Testing connections..."):
                        results = []

                        # Test Todoist if connected
                        if todoist_status["connected"]:
                            if test_todoist_connection():
                                results.append("✅ Todoist: Working")
                            else:
                                results.append("❌ Todoist: Failed")

                        # Test Google accounts if connected
                        if google_accounts:
                            for account in google_accounts:
                                if test_google_connection(account["email"]):
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
