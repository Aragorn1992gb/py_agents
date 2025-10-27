#!/bin/bash

# Setup script for Python AI agents

echo "🚀 Setting up Python AI Agents environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements-minimal.txt

echo "✅ Setup complete!"
echo ""
echo "To run the planner agent:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the agent: python planner_agent.py"
echo ""
echo "To deactivate the virtual environment: deactivate"