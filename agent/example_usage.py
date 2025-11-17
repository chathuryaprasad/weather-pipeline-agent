"""Example usage of the weather agent."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agent.weather_agent import WeatherAgent
from config.settings import settings


def example_queries():
    """Run example queries to demonstrate the agent."""
    try:
        agent = WeatherAgent()
        
        print("=" * 60)
        print("Weather Agent - Example Queries")
        print("=" * 60)
        
        # Example 1: Current weather
        print("\n1. Query: What is the current weather in Colombo?")
        print("-" * 60)
        response = agent.query("What is the current weather in Colombo?")
        print(f"Response: {response}\n")
        
        # Example 2: Average temperature
        print("\n2. Query: What was the average temperature in Galle last week?")
        print("-" * 60)
        response = agent.query("What was the average temperature in Galle last week?")
        print(f"Response: {response}\n")
        
        # Example 3: Weather history
        print("\n3. Query: Show me the weather history for London over the past 7 days")
        print("-" * 60)
        response = agent.query("Show me the weather history for London over the past 7 days")
        print(f"Response: {response}\n")
        
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set OPENAI_API_KEY in your .env file.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    example_queries()

