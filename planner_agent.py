import os
from openai import OpenAI
import requests
import json
from dotenv import load_dotenv

import nest_asyncio
import asyncio

# Load environment variables from .env file
load_dotenv()

# Define variables required for Session setup and Agent execution
APP_NAME="Google Search_agent"
USER_ID="user1234"
SESSION_ID="1234"

# Set API keys from environment variables
openai_api_key = os.getenv("OPEN_AI_KEY")
serper_api_key = os.getenv("SERPER_API_KEY")

# Validate API keys
if not openai_api_key:
    raise ValueError("OPEN_AI_KEY environment variable is required")
if not serper_api_key:
    raise ValueError("SERPER_API_KEY environment variable is required")

client = OpenAI(api_key=openai_api_key)

# Serper search function (working version)
def serper_search_tool(query):
    """
    Search Google using Serper API (serper.dev)
    Much more generous free tier: 2,500 searches/month
    """
    try:
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': serper_api_key,
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
        if search_data.get("answerBox") and search_data["answerBox"].get("answer"):
            results.append(f"**Quick Answer:** {search_data['answerBox']['answer']}")
            if search_data["answerBox"].get("link"):
                results.append(f"Source: {search_data['answerBox']['link']}\n")
        
        # Add organic results
        if search_data.get("organic"):
            for result in search_data["organic"][:5]:
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No snippet")
                link = result.get("link", "No link")
                results.append(f"**{title}**\n{snippet}\nSource: {link}\n")
        
        if results:
            return "\n".join(results)
        else:
            return "No search results found."
            
    except requests.exceptions.RequestException as e:
        return f"Error searching: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# Define Agent with access to search tool
# root_agent = ADKAgent(
#    name="basic_search_agent",
#    model="gemini-2.0-flash-exp",
#    description="Agent to answer questions using Google Search.",
#    instruction="I can answer your questions by searching the internet. Just ask me anything!",
#    tools=[google_search] # Google Search is a pre-built tool to perform Google searches.
# )
tools = [
    {
        "type": "function",
        "function": {
            "name": "serper_search",
            "description": "Search the internet for information using Serper API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    }
]

# Agent Interaction
# async def call_agent(query):
#    """
#    Helper function to call the agent with a query.
#    """

#    # Session and Runner
#    session_service = InMemorySessionService()
#    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
#    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

#    content = types.Content(role='user', parts=[types.Part(text=query)])
#    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)


#    for event in events:
#        if event.is_final_response():
#            final_response = event.content.parts[0].text
#            print("Agent Response: ", final_response)
async def call_agent(query):
    """
    Helper function to call the agent with a query using OpenAI function calling.
    """
    messages = [
        {"role": "system", "content": "You can search the internet. Use the serper_search function when needed to get current information."},
        {"role": "user", "content": query}
    ]
    
    response = client.chat.completions.create(
        model="gpt-5", 
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    # Debug: Print usage information
    if hasattr(response, 'usage'):
        print(f"💰 Tokens used: {response.usage.total_tokens} (Input: {response.usage.prompt_tokens}, Output: {response.usage.completion_tokens})")
        print(f"💵 Approximate cost: ${response.usage.total_tokens * 0.00003:.4f}")  # Rough estimate for GPT-4
    
    # Check if the model wants to call a function
    if response.choices[0].message.tool_calls:
        # Add the assistant's message to the conversation
        messages.append(response.choices[0].message)
        
        # Execute the function call
        for tool_call in response.choices[0].message.tool_calls:
            if tool_call.function.name == "serper_search":
                # Parse the arguments
                args = json.loads(tool_call.function.arguments)
                search_query = args.get("query", "")
                
                print(f"🔍 Searching for: {search_query}")
                
                # Execute the search
                search_results = serper_search_tool(search_query)
                
                # Add the function result to the conversation
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "serper_search",
                    "content": search_results
                })
        
        # Get the final response with the search results
        final_response = client.chat.completions.create(
            model="gpt-4",  # Fixed: use gpt-4 instead of gpt-5
            messages=messages
        )
        
        # Debug: Print usage for second call
        if hasattr(final_response, 'usage'):
            print(f"💰 Final call tokens: {final_response.usage.total_tokens}")
        
        print("Agent Response:", final_response.choices[0].message.content)
    else:
        # No function call needed
        print("Agent Response:", response.choices[0].message.content)

nest_asyncio.apply()

# Agent examples - change the destination and dates as needed
# asyncio.run(call_agent("what's the latest ai news?"))

# Example 1: Morocco
# asyncio.run(call_agent("Build an itinerary from a travel to Morocco from 8 to 14 december 2025"))

# Example 2: Japan (customize as needed)
# asyncio.run(call_agent("Build an itinerary for a trip to Japan from 15 to 22 March 2025, focusing on culture and traditional experiences"))

# Example 3: Interactive input
import sys
if len(sys.argv) > 1:
    destination_query = " ".join(sys.argv[1:])
    asyncio.run(call_agent(destination_query))
else:
    # Default query
    asyncio.run(call_agent("Build an itinerary from a travel to Morocco from 8 to 14 december 2025"))