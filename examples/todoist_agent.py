"""
Example of using the Todoist MCP server with LangGraph for task management.

This example demonstrates various real-world use cases for task management using natural language:
- Task organization and prioritization
- Smart task scheduling
- Project and label management
- Task analysis and insights
- Bulk operations

The example includes comprehensive error handling for API rate limits and failures.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import backoff

class DemoError(Exception):
    """Base class for demonstration errors."""
    pass

async def check_api_status(agent) -> Dict[str, Any]:
    """Check the Todoist API status before running demonstrations."""
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Check the Todoist API status"
        }]
    })

    status = response.get("status", "error")
    if status != "ok":
        raise DemoError(f"API Status Check Failed: {response.get('message', 'Unknown error')}")

    return response

async def retry_on_rate_limit(func, agent, max_retries: int = 3) -> Any:
    """Retry a function with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return await func(agent)
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg and attempt < max_retries - 1:
                retry_after = 60  # Default retry delay
                if "retry after" in error_msg:
                    try:
                        retry_after = int(error_msg.split("retry after")[1].split()[0])
                    except (IndexError, ValueError):
                        pass
                print(f"\nRate limit hit. Waiting {retry_after} seconds before retry...")
                await asyncio.sleep(retry_after)
                continue
            raise

async def demonstrate_task_organization(agent) -> None:
    """Demonstrate task organization capabilities."""
    print("\n=== Task Organization ===")

    try:
        # Create a new project and add tasks
        response = await retry_on_rate_limit(
            lambda a: a.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": "Create a new project called 'Home Renovation' and add these tasks to it:\n"
                              "1. Research contractors (high priority, due next week)\n"
                              "2. Create budget spreadsheet (medium priority, due in 3 days)\n"
                              "3. Take before photos (low priority, due tomorrow)\n"
                              "Add the label @renovation to all tasks"
                }]
            }),
            agent
        )
        print("Project setup:", response)

        # Organize tasks by priority
        response = await retry_on_rate_limit(
            lambda a: a.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": "Show me all high priority tasks in the Home Renovation project"
                }]
            }),
            agent
        )
        print("\nHigh priority tasks:", response)

    except Exception as e:
        print(f"\nError in task organization: {str(e)}")
        raise

async def demonstrate_smart_scheduling(agent) -> None:
    """Demonstrate intelligent task scheduling."""
    print("\n=== Smart Scheduling ===")

    # Reschedule overdue tasks
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Find all my overdue tasks and suggest new realistic due dates based on priority"
        }]
    })
    print("Rescheduling overdue tasks:", response)

    # Distribute workload
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "I have too many tasks due this Friday. Can you help distribute them more evenly over the next week?"
        }]
    })
    print("\nWorkload distribution:", response)

async def demonstrate_task_analysis(agent) -> None:
    """Demonstrate task analysis and insights."""
    print("\n=== Task Analysis ===")

    # Project progress analysis
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Analyze my Home Renovation project. Show progress, upcoming deadlines, and suggest any tasks that might be missing."
        }]
    })
    print("Project analysis:", response)

    # Workload analysis
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Analyze my task distribution across projects and suggest ways to better organize my workload"
        }]
    })
    print("\nWorkload analysis:", response)

async def demonstrate_bulk_operations(agent) -> None:
    """Demonstrate bulk task operations."""
    print("\n=== Bulk Operations ===")

    # Add labels to multiple tasks
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Add the labels @important and @q2_2024 to all tasks due between April 1st and June 30th"
        }]
    })
    print("Bulk label update:", response)

    # Move tasks between projects
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Move all tasks with label @renovation from Inbox to the Home Renovation project"
        }]
    })
    print("\nBulk task move:", response)

async def main():
    """Run the example demonstrations."""
    # Load environment variables
    load_dotenv()

    # Configure MCP servers
    servers = {
        "todoist": {
            "url": "http://localhost:8000",  # Use local server
            "transport": "sse",
            "auth": {
                "type": "bearer",
                "token": os.getenv("TODOIST_API_TOKEN")
            }
        }
    }

    # Create MCP client and agent
    async with MultiServerMCPClient(servers) as client:
        agent = create_react_agent(
            "openai:gpt-4-turbo-preview",  # Use GPT-4 instead of Claude
            client.get_tools(),
            temperature=0.0,  # Use deterministic responses for examples
        )

        try:
            # Check API status before starting
            await check_api_status(agent)

            # Run demonstrations with progress tracking
            demos = [
                ("Task Organization", demonstrate_task_organization),
                ("Smart Scheduling", demonstrate_smart_scheduling),
                ("Task Analysis", demonstrate_task_analysis),
                ("Bulk Operations", demonstrate_bulk_operations)
            ]

            for demo_name, demo_func in demos:
                try:
                    print(f"\nStarting {demo_name} demonstration...")
                    await demo_func(agent)
                    print(f"{demo_name} demonstration completed successfully.")
                except Exception as e:
                    print(f"\nError in {demo_name} demonstration: {str(e)}")
                    print("Continuing with next demonstration...")
                    continue

        except DemoError as e:
            print(f"\nDemonstration setup error: {str(e)}")
            print("Please check your API token and try again.")
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            import traceback
            print(traceback.format_exc())
        finally:
            # Final API status check
            try:
                final_status = await check_api_status(agent)
                print("\nFinal API Status:", final_status)
            except Exception as e:
                print(f"\nError checking final API status: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
