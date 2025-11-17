"""Main script to run the weather agent interactively."""
import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agent.weather_agent import WeatherAgent
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the weather agent."""
    try:
        # Initialize the agent
        agent = WeatherAgent()
        
        # Check if command line arguments are provided (non-interactive mode)
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
            print(f"Query: {query}\n")
            response = agent.query(query)
            print(f"Response: {response}")
        else:
            # Interactive mode
            agent.chat()
            
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set OPENAI_API_KEY in your .env file.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

