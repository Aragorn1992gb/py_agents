import os
import requests
import json
from crewai import Agent, Task, Crew, LLM, Process
from crewai.tools import tool
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
load_dotenv()

# Set environment variables
os.environ["OPENAI_API_KEY"] = os.getenv("OPEN_AI_KEY") or ""
os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY") or ""

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

@tool("Serper Search Tool")
def serper_search(query: str) -> str:
    """Performs a web search using Serper API."""
    logging.info(f"🔍 Searching: {query}")
    try:
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': os.environ.get("SERPER_API_KEY"),
            'Content-Type': 'application/json'
        }
        data = {"q": query, "num": 5}

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        search_data = response.json()

        results = []
        if (search_data.get("answerBox") and search_data["answerBox"].get("answer")):
            results.append(f"Answer: {search_data['answerBox']['answer']}")

        if search_data.get("organic"):
            for result in search_data["organic"][:3]:
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No snippet")
                results.append(f"{title}: {snippet}")

        return "\n".join(results) if results else "No results found."

    except Exception as e:
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


@tool("Attraction Details Tool")
def attraction_details(attraction_name: str, location: str,
                       visit_date: str) -> str:
    """Gets detailed information about a specific attraction."""
    logging.info(f"🏛️ Getting details for: {attraction_name} on {visit_date}")
    
    attraction_details_prompt = f"""
    Find detailed information for the attraction "{attraction_name}" in {location} for visit date {visit_date}.

    Focus on:
    - Opening hours and ticket prices for {visit_date}
    - Current events, exhibitions, or special activities happening on {visit_date}
    - Visitor tips and practical information for that specific date
    - Day-of-week considerations (weekday vs weekend crowds, closures)
    - Seasonal factors affecting the visit on {visit_date}
    - Best times to visit on {visit_date} to avoid crowds

    Provide a concise summary with practical details for travelers visiting on {visit_date}.
    """

    return attraction_details_prompt


@tool("Enhanced Image Finder Tool")
def image_finder(attraction_name: str, location: str) -> str:
    """Provides guidance for finding high-quality images of attractions."""
    logging.info(f"📸 Finding images for: {attraction_name}")

    image_search_prompt = f"""
    Find high-quality, representative images for "{attraction_name}" in {location}.

    Search for:
    - Professional photos showing the attraction's key features
    - Images that capture the architectural or natural beauty
    - Photos taken during different times of day (golden hour preferred)
    - Images that show the scale and context of the attraction
    - Current photos (not historical unless specifically relevant)

    Focus on finding images that would help travelers:
    - Recognize the attraction when they arrive
    - Understand what makes it visually impressive
    - See the best angles or viewpoints for their own photos

    Return image data in this format:
    {{
        "location": "{attraction_name}, {location}",
        "image_url": "[actual URL from search results]",
        "image_description": "Brief description of what the image shows"
    }}

    Use web search to find actual image URLs from reliable sources.
    """

    return image_search_prompt


@tool("JSON Formatter Tool")
def format_travel_json(itinerary_text: str, destination: str, 
                      start_date: str, end_date: str) -> str:
    """Formats the complete itinerary into the required JSON structure."""
    logging.info("📋 Formatting itinerary into JSON structure")

    try:
        # Parse the itinerary text and extract structured data
        lines = itinerary_text.split('\n')
        days = []
        current_day = None
        current_activities = []
        current_images = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect day headers (e.g., "Day 1 – 1 Dec 2025 – Colosseum...")
            if line.startswith('Day ') and '–' in line:
                # Save previous day if exists
                if current_day is not None:
                    current_day['activities'] = current_activities
                    current_day['images_day'] = current_images
                    days.append(current_day)
                
                # Parse day header
                parts = line.split('–')
                day_num = parts[0].strip().replace('Day ', '')
                day_date = parts[1].strip() if len(parts) > 1 else ""
                day_location = parts[2].strip() if len(parts) > 2 else destination
                
                current_day = {
                    "day": int(day_num),
                    "location": day_location,
                    "description": "",
                    "activities": [],
                    "images_day": []
                }
                current_activities = []
                current_images = []
            
            # Parse activities (numbered items like "1. Colosseum")
            elif line and line[0].isdigit() and '.' in line:
                activity_name = line.split('.', 1)[1].strip()
                current_activity = {
                    "time": "",
                    "name": activity_name,
                    "description": ""
                }
                current_activities.append(current_activity)
            
            # Parse time information
            elif '- Time:' in line:
                time_info = line.split('Time:')[1].strip()
                if current_activities:
                    current_activities[-1]['time'] = time_info
            
            # Parse description
            elif '- Description:' in line:
                desc_info = line.split('Description:')[1].strip()
                if current_activities:
                    current_activities[-1]['description'] = desc_info
            
            # Parse images
            elif '- Images:' in line or line.strip().startswith('-') and 'image' in line.lower():
                # Extract image descriptions for later conversion to URLs
                img_desc = line.replace('-', '').strip()
                if img_desc and current_day:
                    current_images.append({
                        "url": "https://upload.wikimedia.org/wikipedia/commons/placeholder.jpg",
                        "description": img_desc
                    })

        # Add the last day
        if current_day is not None:
            current_day['activities'] = current_activities
            current_day['images_day'] = current_images
            days.append(current_day)
        
        # Create final structured JSON
        formatted_json = {
            "success": True,
            "message": "Itinerary generated successfully",
            "itinerary": {
                "days": days
            }
        }

        return json.dumps(formatted_json, indent=2)

    except Exception as e:
        logging.error(f"JSON formatting error: {str(e)}")
        # Fallback to simple structure
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
                        "images_day": []
                    }
                ]
            },
            "raw_itinerary": itinerary_text
        }
        return json.dumps(fallback_json, indent=2)

# =============================================================================
# STEP 2: SPECIALIZED AGENTS
# =============================================================================


# 📋 PLANNER AGENT - Creates structure and optimizes routes
planner_agent = Agent(
    role="Travel Itinerary Planner",
    goal="Create structured, optimized daily itineraries",
    backstory="Expert travel planner specializing in route optimization and time management. You create logical daily schedules without needing detailed attraction information.",
    verbose=True,
    tools=[location_optimizer],  # Only route optimization
    llm=llm,  # Use configured LLM
    allow_delegation=False
)

# 🔍 RESEARCHER AGENT - Gathers detailed information  
researcher_agent = Agent(
    role="Travel Information Researcher",
    goal="Gather comprehensive details about attractions, transport, accommodation, and practical travel information",
    backstory="You are a meticulous travel researcher who finds detailed, accurate information about destinations. You specialize in opening hours, ticket prices, transport options, and practical visitor information.",
    verbose=True,
    tools=[serper_search, attraction_details],
    llm=llm,  # Use configured LLM
    allow_delegation=False
)

# 📸 IMAGE COLLECTOR AGENT - Finds relevant images
image_collector_agent = Agent(
    role="Visual Content Curator",
    goal="Find high-quality, relevant images for each day's main attractions and activities", 
    backstory="You are a visual content specialist who finds the best representative images for travel destinations. You focus on finding images that showcase the key attractions and experiences for each day.",
    verbose=True,
    tools=[serper_search, image_finder],
    llm=llm,  # Use configured LLM
    allow_delegation=False
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
    agent=planner_agent
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
    context=[planning_task]  # Gets input from planning_task
)

# 📸 TASK 3: Image Collection (Image Collector Agent)
image_collection_task = Task(
    description="""
    Take the detailed itinerary and add visual elements for each day.

    YOUR TASKS:
    1. Find relevant images for each day's main attractions
    2. Select 1-3 key images per day representing main highlights  
    3. Ensure images match the specific attractions mentioned
    4. Provide image descriptions and context

    OUTPUT FORMAT: Complete itinerary with image sections:
    - Image URLs for key attractions
    - Descriptive captions
    - Location context for each image

    Focus on the most important attractions from each day.
    """,
    expected_output="Final comprehensive itinerary with relevant images, URLs, and descriptions for each day's key attractions",
    agent=image_collector_agent,
    # TODO maybe is better to don't wait for the research task
    # context=[planning_task, research_task]  # Gets input from both previous tasks
    context=[planning_task] 
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
    context=[planning_task, research_task, image_collection_task],
    tools=[format_travel_json]  # Add the JSON formatter tool
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
    # sequential=True
    process=Process.hierarchical  # Allows parallel execution where possible
)

# =============================================================================
# STEP 5: MAIN EXECUTION FUNCTION
# =============================================================================


def create_travel_itinerary(destination: str, start_date: str, end_date: str,
                           preferences: str = "adventure and cultural activities"):
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

    Build upon the previous task's structure.
    """

    image_collection_task.description = f"""
    Take the detailed itinerary for {destination} and add visual elements for each day.

    YOUR TASKS:
    1. Find relevant images for each day's main attractions in {destination}
    2. Select 1-3 key images per day representing main highlights
    3. Ensure images match the specific attractions mentioned
    4. Provide image descriptions and context

    Focus on the most important attractions from each day in {destination}.
    """
    print(f"🚀 Starting multi-agent travel planning for {destination}")
    print(f"📅 Dates: {start_date} to {end_date}")
    print(f"🎯 Preferences: {preferences}")
    print("\n" + "="*60)

    # Execute the crew - all tasks run sequentially
    result = travel_crew.kickoff()

    print("\n" + "="*60)
    print("✅ COMPLETE TRAVEL ITINERARY")
    print("="*60)

    return result


def main():
    # Example: Create itinerary for Rome (smaller example for testing)
    destination = "Rome, Italy"
    start_date = "2025-12-01" 
    end_date = "2025-12-03"  # 3 days
    preferences = "cultural sites, history, traditional food"

    # Log which model CrewAI is using
    print(f"🤖 Using OpenAI model: {llm.model}")
    api_key_status = "Yes" if os.environ.get('OPENAI_API_KEY') else "No"
    print(f"🔑 API Key configured: {api_key_status}")

    try:
        itinerary = create_travel_itinerary(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            preferences=preferences
        )

        print("\n" + "="*60)
        print("📋 RAW OUTPUT FOR ANALYSIS:")
        print("="*60)
        print(itinerary)
        print("="*60)

    except Exception as e:
        print(f"❌ Error creating itinerary: {e}")


if __name__ == "__main__":
    main()
