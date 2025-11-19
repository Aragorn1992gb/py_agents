import os
import requests
from crewai import Agent, Task, Crew
from crewai.tools import tool
from langchain_openai import OpenAI
from dotenv import load_dotenv
# langchain-openai is a wrapper around OpenAI's API. This is the LangChain integration of the OpenAI API. It provides a higher-level abstraction specifically designed to work within the LangChain framework.

import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Set your environment variables for API keys before running:
os.environ["OPENAI_API_KEY"] = os.getenv("OPEN_AI_KEY") or ""
os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY") or ""


# Tool to get live search results from Serper
@tool("Serper Search Tool")
def serper_search(query: str) -> str:
    """
    Performs a web search using Serper for the given query.
    Returns the search result snippet as a string.
    """
    logging.info(f"Serper searching for: {query}")

    try:
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': os.environ.get("SERPER_API_KEY"),
            'Content-Type': 'application/json'
        }
        data = {
            "q": query,
            "num": 5
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        search_data = response.json()

        # Format search results
        results = []

        # Add answer box if available
        if (search_data.get("answerBox") and
                search_data["answerBox"].get("answer")):
            results.append(
                f"Quick Answer: {search_data['answerBox']['answer']}"
            )

        # Add organic results
        if search_data.get("organic"):
            for result in search_data["organic"][:3]:
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No snippet")
                results.append(f"{title}: {snippet}")

        return "\n".join(results) if results else "No search results found."

    except Exception as e:
        return f"Error searching: {str(e)}"


@tool("Content Filter Tool")
def content_filter(content: str) -> str:
    """Filter inappropriate content from search results."""
    inappropriate_keywords = [
        "sex", "adult", "18+", "porn", "explicit", "mature",
        "nude", "xxx", "erotic", "nsfw"
    ]

    lines = content.split('\n')
    filtered_lines = []

    for line in lines:
        line_lower = line.lower()
        if not any(keyword in line_lower for keyword in inappropriate_keywords):
            filtered_lines.append(line)
        else:
            logging.info(f"Filtered inappropriate content: {line[:50]}...")

    return '\n'.join(filtered_lines)


# Tool to generate itinerary text using OpenAI
@tool("OpenAI Itinerary Generator")
def generate_itinerary(place: str, date_from: str, date_to: str,
                       live_info: str) -> str:
    """Generate a travel itinerary using OpenAI based on parameters."""
    openai_client = OpenAI()
    prompt = (
        f"Create a travel itinerary for {place} "
        f"from {date_from} to {date_to}.\n"
        f"Use the following live info: {live_info}\n"
        "Make it structured and clear."
    )
    response = openai_client.invoke(prompt)
    # return response.text
    return response


# Define the Agent
"""
Define the Agent
- "role" identifies the agent's function
- "goal" specifies what the agent aims to achieve
- "backstory" provides context about the agent's expertise
- "verbose" enables detailed logging
- "tools" lists the tools the agent can use
- "allow_delegation" controls if the agent can delegate tasks
"""
itinerary_agent = Agent(
    role="Travel Planner",
    goal="Create a travel itinerary given place and dates using live data."
    "Include only attractions of the place, no events/restaurants",
    backstory="Experienced travel planner using AI and web search tools.",
    verbose=True,
    tools=[serper_search, generate_itinerary],
    allow_delegation=False,
)

researcher_agent = Agent(
    role='Event Researcher',
    goal='Find family-friendly events and activities for each day'
    'of the itinerary that match the travel dates and locations.',
    backstory="You are an experienced event researcher specializing in"
    "finding current, family-friendly events and activities. You verify"
    "dates and locations carefully and filter out inappropriate content.",
    verbose=True,
    tools=[serper_search, content_filter],
    allow_delegation=False,
)

# Define the Task
"""
Define the Task
- "description" outlines what the task entails
- "expected_output" describes the desired result of the task
- "agent" assigns the agent responsible for the task
"""
itinerary_task = Task(
    description=(
        "Given a place and date range, create a travel itinerary "
        "using serper to fetch live info and OpenAI to generate text."
        "Don't include events."
    ),
    expected_output=(
        "A structured itinerary text with recommended places and activities."
    ),
    agent=itinerary_agent,
)

researcher_task = Task(
    description=(
        "Based on the itinerary provided, find specific family-friendly events"
        "and activities for each day and location mentioned. "
        "Search for events that match the exact dates and verify they exist. "
        "Filter out any inappropriate content using the content_filter tool. "
        "Focus on cultural events, festivals, exhibitions, concerts, "
        "workshops, and family activities."
    ),
    expected_output=(
        "A detailed list of verified events for each day, including: "
        "- Event name and type\n"
        "- Exact date and time\n"
        "- Location/venue\n"
        "- Brief description\n"
        "- Target audience (family-friendly, adults, etc.)\n"
        "- Ticket information if available\n"
        "Format as a structured day-by-day event schedule."
    ),
    agent=researcher_agent,
)


# Define the Crew
"""
Define the Crew
- "agents" lists the agents in the crew
- "tasks" lists the tasks to be accomplished
- "verbose" enables detailed logging
"""
itinerary_crew = Crew(
    agents=[itinerary_agent, researcher_agent],
    tasks=[itinerary_task, researcher_task],
    verbose=True,
)


def main():
    # Example input
    place = "Rome"
    date_from = "2025-12-01"
    date_to = "2025-12-05"

    # Update the tasks with specific inputs
    itinerary_task.description = (
        f"Create a travel itinerary for {place} "  # → place parameter
        f"from {date_from} to {date_to}. "  # → date_from, date_to parameters
        f"Use the serper_search tool to get current information " # → live_info comes from this
        f"about attractions and activities in {place} for December 2025. "
        f"Focus on tourist attractions, museums, landmarks, and activities. "
        f"DO NOT include events, festivals, or time-specific activities. "
        f"Then use the generate_itinerary tool to create a structured itinerary."
    )

    print(f"🗺️  Creating itinerary for {place} ({date_from} to {date_to})")
    print("📋 Task 1: Generating base itinerary...")
    print("🎯 Task 2: Researching events for each day...")
    
    # Execute the crew (both tasks will run in sequence)
    result = itinerary_crew.kickoff()

    print("\n" + "="*50)
    print("✅ COMPLETE TRAVEL PLAN")
    print("="*50)
    print(result)


if __name__ == "__main__":
    main()
