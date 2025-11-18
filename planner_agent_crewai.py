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
    response = openai_client.complete(prompt)
    return response.text


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
    goal="Create a travel itinerary given place and dates using live data",
    backstory="Experienced travel planner using AI and web search tools.",
    verbose=True,
    tools=[serper_search, generate_itinerary],
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
    ),
    expected_output=(
        "A structured itinerary text with recommended places and activities."
    ),
    agent=itinerary_agent,
)

# TODO refine it. It says that on on 3 December there is Sex.Exe event, which is wrong. Furthermore, can be a event > 18, so add a Guardrail tool to filter inappropriate content.

# Define the Crew
"""
Define the Crew
- "agents" lists the agents in the crew
- "tasks" lists the tasks to be accomplished
- "verbose" enables detailed logging
"""
itinerary_crew = Crew(
    agents=[itinerary_agent],
    tasks=[itinerary_task],
    verbose=True,
)


def main():
    # Example input
    place = "Rome"
    date_from = "2025-12-01"
    date_to = "2025-12-05"

    # Update the task with specific inputs
    itinerary_task.description = (
        f"Create a travel itinerary for {place} "
        f"from {date_from} to {date_to}. "
        f"Use the serper_search tool to get current information "
        f"about attractions, events, and activities in {place} "
        f"for December 2025. "
        f"Then use the generate_itinerary tool to create "
        f"a structured itinerary."
    )

    # Execute the crew
    result = itinerary_crew.kickoff()

    print("\nGenerated Itinerary:\n", result)


if __name__ == "__main__":
    main()
