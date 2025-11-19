#!/usr/bin/env python3
"""
Test script to verify TavilySearchTool installation and functionality
"""

try:
    from crewai_tools import TavilySearchTool
    print("✅ TavilySearchTool imported successfully")
    
    # Test basic initialization (will need API key for actual search)
    tavily_tool = TavilySearchTool()
    print("✅ TavilySearchTool initialized successfully")
    
    print("🎯 TavilySearchTool is ready for use!")
    print("📋 Make sure to set TAVILY_API_KEY in your .env file")
    
except ImportError as e:
    print("❌ Failed to import TavilySearchTool")
    print(f"Error: {e}")
    print("\n💡 To install, run:")
    print("pip install crewai-tools")

except Exception as e:
    print(f"❌ Error initializing TavilySearchTool: {e}")
    print("📋 Check your environment configuration")