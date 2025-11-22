# Python AI Travel Planner

A Python-based travel planning agent that uses OpenAI's function calling with web search capabilities to create detailed, real-time travel itineraries.

## Features

- 🔍 **Real-time web search** using Serper API
- 🤖 **OpenAI GPT-4** with function calling
- 🌍 **Any destination** worldwide
- 📅 **Custom date ranges**
- 🎯 **Personalized preferences** (culture, adventure, etc.)

## Quick Start

### 1. Setup (One time only)

```bash
chmod +x setup.sh
./setup.sh
```

### 2. Run the Agent

**Option A: Default Morocco Example**

```bash
source venv/bin/activate
python planner_agent.py
```

**Option B: Custom Destination**

```bash
source venv/bin/activate
python planner_agent.py "Build an itinerary for a trip to Japan from 15 to 22 March 2025, focusing on cherry blossoms"
```

**Option C: Interactive Mode**

```bash
source venv/bin/activate
python planner_agent.py "Plan a 5-day cultural trip to Rome in September 2025"
```

## Example Queries

- `"Build an itinerary for a trip to Morocco from 8 to 14 december 2025"`
- `"Plan a 7-day adventure trip to Nepal focusing on hiking and mountains"`
- `"Create a cultural tour of Italy for 10 days in spring 2025"`
- `"Design a relaxing beach vacation in Thailand for 2 weeks"`

## Features in Action

The agent will:

1. **Create a detailed day-by-day itinerary**
2. **Search the web** for current information about:
   - Opening hours and entrance fees
   - Seasonal events (festivals, weather)
   - Transportation options
   - Local recommendations
3. **Provide practical advice** about timing, bookings, and logistics

## Files Structure

- `planner_agent.py` - Main agent script
- `requirements.txt` - All optional dependencies
- `requirements-minimal.txt` - Essential dependencies only
- `setup.sh` - Automated setup script

## API Keys Required

The agent uses hardcoded API keys for demo purposes. For production:

- OpenAI API key (for GPT-4)
- Serper API key (for web search)

## Deactivate Environment

When done:

```bash
deactivate
```

## Comparison with Rust

| Feature           | Python Agent | Rust Agent               |
| ----------------- | ------------ | ------------------------ |
| Development Speed | ✅ Very Fast | ⚪ Moderate              |
| AI Ecosystem      | ✅ Excellent | ⚪ Limited               |
| Performance       | ⚪ Good      | ✅ Excellent             |
| Real-time Search  | ✅ Built-in  | ✅ Custom implementation |
| Iteration Speed   | ✅ Immediate | ⚪ Compile required      |

Both approaches work well - Python for rapid AI development, Rust for production performance and integration with existing backend.

## Add settings.json file in .vscode folder project to define the code formatter for python and rust

```json
{
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.black-formatter",
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true
  },
  "[rust]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "rust-lang.rust-analyzer",
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true
  },
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": false,
  "python.linting.pylintEnabled": false
}
```
