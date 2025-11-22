import os
import requests
import json
from crewai import Agent, Task, Crew, LLM, Process
from crewai.tools import tool
from crewai_tools import TavilySearchTool
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
load_dotenv()

# Set environment variables
os.environ["OPENAI_API_KEY"] = os.getenv("OPEN_AI_KEY") or ""
os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY") or ""
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY") or ""

# Configure LLM - Choose your model here
# Available O1 models: "o1-preview", "o1-mini"
# Available GPT models: "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"
llm = LLM(
    # model="gpt-5.1",  # Change to "o1-preview" or "o1-mini" for O1 models
    # model="gpt-5-mini",  # Cost efficient
    model="gpt-5-nano",  # Cost efficient and faster,less reasonable than mini
    # temperature=0.7,
    # Note: O1 models don't support temperature, max_tokens same way
)
# For faster performance, use smaller models:
# "ollama/llama3.2:3b" (3B params - fast)
# "ollama/llama3.2:1b" (1B params - very fast)
# "ollama/qwen2.5:7b" (7B params - good balance)

# llm = LLM(
#     # model="ollama/llama3.2:3b",  # Much smaller and faster
#     model="ollama/llama3.1:8b",  # Bigger than llama3.1.3:b, faster than gpt-oss:20b
#     base_url="http://172.30.160.1:11434",
#     temperature=0.7
# )


# =============================================================================
# STEP 1: SPECIALIZED TOOLS
# =============================================================================

# Initialize Tavily Search Tool with image support
tavily_tool = TavilySearchTool(
    api_key=os.environ.get("TAVILY_API_KEY"),
    search_depth="advanced",
    include_images=True,
    include_answer=True,
    max_results=5,
)


@tool("Comprehensive Travel Search Tool")
def travel_search(query: str) -> str:
    """Performs comprehensive travel search with images using Tavily."""
    logging.info(f"🔍 Searching: {query}")
    try:
        # Use Tavily tool for comprehensive search with images
        search_results = tavily_tool.run(query)

        # Tavily returns structured data with content and images
        if isinstance(search_results, str):
            return search_results
        elif isinstance(search_results, dict):
            # Format the results nicely
            formatted_results = []

            if "answer" in search_results:
                formatted_results.append(f"Answer: {search_results['answer']}")

            if "results" in search_results:
                for result in search_results["results"][:3]:
                    title = result.get("title", "No title")
                    content = result.get("content", "No content")
                    formatted_results.append(f"{title}: {content}")

            return "\n".join(formatted_results)
        else:
            return str(search_results)

    except Exception as e:
        logging.error(f"Search error: {str(e)}")
        return f"Search error: {str(e)}"


@tool("Location Optimizer Tool")
def location_optimizer(attractions_list: str, location: str) -> str:
    """Optimizes attraction order by proximity and travel efficiency."""
    logging.info(f"📍 Optimizing locations in: {location}")

    # Return optimization strategy without external search
    optimization_prompt = f"""
    Optimize this list of attractions in {location} for efficient travel:
    {attractions_list}

    Return a structured plan with:
    - Morning block (2-3 nearby attractions)
    - Afternoon block (2-3 nearby attractions)
    - Evening activity (1-2 nearby options)

    Consider travel time, opening hours, and logical flow.
    Group attractions by area/neighborhood for efficient routing.
    """

    return optimization_prompt


@tool("Enhanced Attraction Details Tool")
def attraction_details_with_images(
    attraction_name: str, location: str, visit_date: str
) -> str:
    """Gets detailed information and images for attractions using Tavily."""
    logging.info(f"🏛️ Getting details for: {attraction_name} on {visit_date}")

    # Create comprehensive query for Tavily
    query = f"{attraction_name} {location} opening hours prices tickets {visit_date} 2025 visitor information"

    try:
        # Use Tavily for comprehensive search with images
        search_results = tavily_tool.run(query)

        # Add image search for the attraction
        image_query = f"{attraction_name} {location} photos high quality images"
        image_results = tavily_tool.run(image_query)

        # Combine results
        combined_results = (
            f"ATTRACTION DETAILS:\n{search_results}\n\nIMAGES:\n{image_results}"
        )

        return combined_results

    except Exception as e:
        logging.error(f"Attraction details error: {str(e)}")
        return f"Error getting attraction details: {str(e)}"


@tool("JSON Formatter Tool")
def format_travel_json(
    itinerary_text: str, destination: str, start_date: str, end_date: str
) -> str:
    """Formats the complete itinerary into the required JSON structure."""
    logging.info("📋 Formatting itinerary into JSON structure")

    try:
        # Try to parse if it's already JSON
        if itinerary_text.strip().startswith("{"):
            parsed_json = json.loads(itinerary_text)

            # Add images to the existing structure
            if "itinerary" in parsed_json and "days" in parsed_json["itinerary"]:
                for day in parsed_json["itinerary"]["days"]:
                    # Add images_day field with sample images for each day
                    day["images_day"] = [
                        {
                            "url": f"https://upload.wikimedia.org/wikipedia/commons/placeholder_day_{day.get('day_number', 1)}.jpg",
                            "description": f"Beautiful view of {day.get('title', 'Rome')} attractions",
                        }
                    ]
                    # Ensure standard field names
                    if "day_number" in day:
                        day["day"] = day["day_number"]
                    if "title" in day:
                        day["location"] = day["title"]
                        day["description"] = day.get("day_description", "")

            return json.dumps(parsed_json, indent=2)

        # If not JSON, parse as text (original logic)
        lines = itinerary_text.split("\n")
        days = []
        current_day = None
        current_activities = []
        current_images = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect day headers
            if line.startswith("Day ") and (":" in line or "–" in line):
                # Save previous day if exists
                if current_day is not None:
                    current_day["activities"] = current_activities
                    current_day["images_day"] = current_images
                    days.append(current_day)

                # Parse day header
                if "–" in line:
                    parts = line.split("–")
                    day_num = parts[0].strip().replace("Day ", "")
                    day_location = parts[1].strip() if len(parts) > 1 else destination
                else:
                    # Handle "Day X:" format
                    day_num = line.split(":")[0].strip().replace("Day ", "")
                    day_location = destination

                current_day = {
                    "day": int(day_num),
                    "location": day_location,
                    "description": "",
                    "activities": [],
                    "images_day": [
                        {
                            "url": f"https://upload.wikimedia.org/wikipedia/commons/placeholder_day_{day_num}.jpg",
                            "description": f"Sample image for day {day_num} in {destination}",
                        }
                    ],
                }
                current_activities = []
                current_images = []

            # Parse activities (numbered or bulleted items)
            elif (line and line[0].isdigit() and "." in line) or line.startswith("- "):
                if line.startswith("- "):
                    activity_name = line[2:].strip()
                else:
                    activity_name = line.split(".", 1)[1].strip()

                current_activity = {
                    "time": "",
                    "name": activity_name,
                    "description": "",
                }
                current_activities.append(current_activity)

        # Add the last day
        if current_day is not None:
            current_day["activities"] = current_activities
            current_day["images_day"] = current_images
            days.append(current_day)

        # Create final structured JSON
        formatted_json = {
            "success": True,
            "message": "Itinerary generated successfully",
            "itinerary": {"days": days},
        }

        return json.dumps(formatted_json, indent=2)

    except Exception as e:
        logging.error(f"JSON formatting error: {str(e)}")
        # Enhanced fallback with placeholder images
        fallback_json = {
            "success": True,
            "message": "Itinerary generated successfully",
            "itinerary": {
                "days": [
                    {
                        "day": 1,
                        "location": destination,
                        "description": "See detailed itinerary text",
                        "activities": [],
                        "images_day": [
                            {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/placeholder.jpg",
                                "description": f"Sample image for {destination}",
                            }
                        ],
                    }
                ]
            },
            "raw_itinerary": itinerary_text,
        }
        return json.dumps(fallback_json, indent=2)


# =============================================================================
# STEP 2: SPECIALIZED AGENTS
# =============================================================================

# Only if using hierarchical process
# manager_agent = Agent(
#     role="Project Manager",
#     goal="Coordinate and manage the travel planning workflow",
#     backstory="Experienced project manager who coordinates tasks between agents.",
#     llm=llm,
#     allow_delegation=True
# )


# 📋 PLANNER AGENT - Creates structure and optimizes routes
planner_agent = Agent(
    role="Travel Itinerary Planner",
    goal="Create structured, optimized daily itineraries",
    backstory="Expert travel planner specializing in route optimization and time management. You create logical daily schedules without needing detailed attraction information.",
    verbose=True,
    tools=[location_optimizer],  # Only route optimization
    llm=llm,  # Use configured LLM
    allow_delegation=False,
)

# 🔍 RESEARCHER AGENT - Gathers detailed information
researcher_agent = Agent(
    role="Travel Information Researcher",
    goal="Gather comprehensive details about attractions, transport, accommodation, and practical travel information",
    backstory="You are a meticulous travel researcher who finds detailed, accurate information about destinations. You specialize in opening hours, ticket prices, transport options, and practical visitor information.",
    verbose=True,
    tools=[travel_search, attraction_details_with_images],
    llm=llm,  # Use configured LLM
    allow_delegation=False,
)


# =============================================================================
# STEP 3: SEQUENTIAL TASKS WITH DEPENDENCIES
# =============================================================================

# planning_task.description = f"""
# Create a structured travel itinerary for {destination} from {start_date} to {end_date}.

# OUTPUT FORMAT: Structure each day as:
# Day X: [Location Name]
# - HH:MM-HH:MM Activity name (specific details)
# - HH:MM-HH:MM Next activity (specific details)
# [Brief day description explaining the cultural/historical significance]

# This format will be parsed into the final JSON structure.
# """

# 📋 TASK 1: Planning & Structure (Planner Agent)
planning_task = Task(
    description="""
    Create a structured travel itinerary with the following requirements:

    INPUT: You will receive destination, dates, and traveler preferences

    YOUR TASKS:
    1. Search for top attractions and activities in the destination
    2. Optimize the order and grouping by proximity and logistics
    3. Create a day-by-day structure with time slots
    4. Balance activity intensity and travel time

    OUTPUT FORMAT: Return a structured list for each day containing:
    - Day number
    - Main location/area focus
    - Time-based activity schedule
    - Logical flow and transitions

    Use your tools to research attractions and optimize routing.
    """,
    expected_output="Structured itinerary with optimized daily schedules, activity timing, and logical flow between attractions",
    agent=planner_agent,
)

# 🔍 TASK 2: Research & Details (Researcher Agent)
research_task = Task(
    description="""
    Take the structured itinerary from the planning task and enrich it with detailed information.

    IMPORTANT: Use the exact travel dates from the planning task when calling attraction_details tool.

    YOUR TASKS:
    1. Research detailed information for each attraction/activity using specific visit dates
    2. Find opening hours, prices, and practical details for the planned dates
    3. Add transport information between locations
    4. Include relevant tips and descriptions
    5. Verify current information and availability for the specific dates
    6. When using attraction_details tool, extract the actual date from the itinerary

    OUTPUT FORMAT: Enhanced itinerary with:
    - Detailed descriptions for each activity
    - Practical visitor information for specific dates
    - Transport and timing details
    - Cultural and historical context
    - Date-specific information (events, hours, etc.)

    Build upon the previous task's structure and use the exact dates provided.
    """,
    expected_output="Comprehensive itinerary with detailed attraction information, practical details, opening hours, prices, and rich descriptions for the specific travel dates",
    agent=researcher_agent,
    context=[planning_task],  # Gets input from planning_task
)

# 📋 TASK 4: Final JSON Assembly
json_assembly_task = Task(
    description="""
    Take all the information from previous tasks and format it into the exact JSON structure required.

    YOUR TASKS:
    1. Parse the planning task output for day structure
    2. Extract detailed information from research task
    3. Incorporate images from image collection task
    4. Use format_travel_json tool with the complete itinerary text
    5. Return properly structured JSON with success, message, and itinerary.days

    IMPORTANT: Call format_travel_json with the full itinerary text from previous tasks.
    The tool will parse and structure everything correctly.

    OUTPUT: Complete JSON matching the required format exactly.
    """,
    expected_output="Complete JSON-formatted itinerary with success, message, and itinerary.days containing all travel information in proper structure",
    agent=planner_agent,  # Reuse planner agent for final assembly
    context=[planning_task, research_task],  # Images included in research task
    tools=[format_travel_json],  # Add the JSON formatter tool
)

# =============================================================================
# STEP 4: CREW SETUP
# =============================================================================

# travel_crew = Crew(
#     agents=[planner_agent, researcher_agent, image_collector_agent],
#     tasks=[planning_task, research_task, image_collection_task],
#     verbose=True,
#     sequential=True
# )

# travel_crew = Crew(
#     agents=[planner_agent, researcher_agent, image_collector_agent],
#     tasks=[planning_task, research_task, image_collection_task, json_assembly_task],
#     verbose=True,
#     # sequential=True
#     process=Process.hierarchical  # Allows parallel execution where possible
# )
travel_crew = Crew(
    agents=[planner_agent, researcher_agent],
    tasks=[planning_task, research_task, json_assembly_task],
    verbose=True,
    sequential=True,
    # process=Process.hierarchical  # Allows parallel execution where possible
    # manager_agent=manager_agent  # Need to add this when using hierarchical
)

# =============================================================================
# STEP 5: MAIN EXECUTION FUNCTION
# =============================================================================


def create_travel_itinerary(
    destination: str,
    start_date: str,
    end_date: str,
    preferences: str = "adventure and cultural activities",
):
    """
    Main function to create a comprehensive travel itinerary.
    """

    # Update task descriptions with specific input parameters
    planning_task.description = f"""
    Create a structured travel itinerary for {destination} from {start_date} to {end_date}.

    Traveler preferences: {preferences}

    YOUR TASKS:
    1. Search for top attractions and activities in {destination}
    2. Optimize the order and grouping by proximity and logistics
    3. Create a day-by-day structure with time slots
    4. Balance activity intensity and travel time
    5. Consider the traveler's preferences: {preferences}

    OUTPUT FORMAT: Structure each day as:
    Day X: [Location Name]
    - HH:MM-HH:MM Activity name (specific details)
    - HH:MM-HH:MM Next activity (specific details)
    [Brief day description explaining the cultural/historical significance]

    Use your tools to research attractions and optimize routing for {destination}.
    """

    research_task.description = f"""
    Take the structured itinerary for {destination} and enrich it with detailed information.

    YOUR TASKS:
    1. Research detailed information for each attraction/activity in {destination}
    2. Find opening hours, prices, and practical details
    3. Add transport information between locations
    4. Include relevant tips and descriptions
    5. Verify current information and availability for {start_date} to {end_date}
    6. Find high-quality images for each day's main attractions

    Build upon the previous task's structure.
    """
    print(f"🚀 Starting multi-agent travel planning for {destination}")
    print(f"📅 Dates: {start_date} to {end_date}")
    print(f"🎯 Preferences: {preferences}")
    print("\n" + "=" * 60)

    # Execute the crew - all tasks run sequentially
    result = travel_crew.kickoff()

    print("\n" + "=" * 60)
    print("✅ COMPLETE TRAVEL ITINERARY")
    print("=" * 60)

    return result


def main():
    # Example: Create itinerary for Rome (smaller example for testing)
    destination = "Rome, Italy"
    start_date = "2025-12-01"
    end_date = "2025-12-03"  # 3 days
    preferences = "cultural sites, history, traditional food"

    # Log which model CrewAI is using
    print(f"🤖 Using OpenAI model: {llm.model}")
    api_key_status = "Yes" if os.environ.get("OPENAI_API_KEY") else "No"
    print(f"🔑 API Key configured: {api_key_status}")

    try:
        itinerary = create_travel_itinerary(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            preferences=preferences,
        )

        print("\n" + "=" * 60)
        print("📋 RAW OUTPUT FOR ANALYSIS:")
        print("=" * 60)
        print(itinerary)
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error creating itinerary: {e}")


if __name__ == "__main__":
    main()


# TODO map well the images, insert corerctly hours (like the old json), delete lasr day 1
