"""AI Agent implementation using OpenAI Agents SDK for weather queries."""
import logging
import json
from datetime import datetime, date
from typing import Dict, Any, List
from openai import OpenAI
from openai import RateLimitError, APIError
from config.settings import settings
from agent.weather_tools import (
    get_current_weather_tool,
    get_weather_history_tool,
    calculate_average_temperature_tool
)

logger = logging.getLogger(__name__)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class WeatherAgent:
    """AI agent that can answer weather-related queries using stored weather data."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the weather agent.
        
        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY from settings.
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file.")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Define tools for the agent
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current (latest) weather data for a specific city. Use this when asked about current weather conditions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "The name of the city (e.g., 'Colombo', 'Galle', 'London', 'New York')"
                            }
                        },
                        "required": ["city"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather_history",
                    "description": "Get historical weather data for a city over a specified number of days. Use this when asked about past weather or weather trends.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "The name of the city"
                            },
                            "days": {
                                "type": "integer",
                                "description": "Number of days of history to retrieve (default: 7)",
                                "default": 7
                            }
                        },
                        "required": ["city"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_average_temperature",
                    "description": "Calculate the average, minimum, and maximum temperature for a city over a specified number of days. Use this when asked about average temperatures, temperature statistics, or temperature trends.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "The name of the city"
                            },
                            "days": {
                                "type": "integer",
                                "description": "Number of days to calculate average over (default: 7)",
                                "default": 7
                            }
                        },
                        "required": ["city"]
                    }
                }
            }
        ]
        
        # Tool function mapping
        self.tool_functions = {
            "get_current_weather": get_current_weather_tool,
            "get_weather_history": get_weather_history_tool,
            "calculate_average_temperature": calculate_average_temperature_tool
        }
    
    def query(self, user_message: str, model: str = "gpt-4o-mini") -> str:
        """
        Process a user query and return a response.
        
        Args:
            user_message: The user's question or query
            model: The OpenAI model to use (default: gpt-4o-mini)
        
        Returns:
            The agent's response as a string
        """
        try:
            # Check if query is weather-related (guardrails)
            # First, do a quick keyword check for efficiency
            weather_keywords = [
                "weather", "temperature", "climate", "rain", "snow", "wind", "humidity",
                "forecast", "storm", "sunny", "cloudy", "rainy", "hot", "cold", "warm",
                "cool", "precipitation", "barometric", "pressure", "celsius", "fahrenheit",
                "degrees", "meteorology", "atmospheric", "city", "cities"
            ]
            
            query_lower = user_message.lower()
            has_weather_keyword = any(keyword in query_lower for keyword in weather_keywords)
            
            # If no weather keywords found, use LLM to check if it's weather-related
            if not has_weather_keyword:
                # Quick LLM check for weather-related queries
                check_messages = [
                    {
                        "role": "system",
                        "content": "You are a classifier. Determine if a user query is related to weather, climate, or meteorological conditions. Respond with only 'YES' or 'NO'."
                    },
                    {
                        "role": "user",
                        "content": f"Is this query about weather, climate, or meteorological conditions? Query: {user_message}"
                    }
                ]
                
                try:
                    check_response = self.client.chat.completions.create(
                        model=model,
                        messages=check_messages,
                        max_tokens=10,
                        temperature=0
                    )
                    is_weather_related = "YES" in check_response.choices[0].message.content.upper()
                except Exception as e:
                    logger.warning(f"Failed to check query with LLM, using keyword fallback: {e}")
                    is_weather_related = False
            else:
                is_weather_related = True
            
            # If not weather-related, refuse politely
            if not is_weather_related:
                return """I'm a weather assistant specialized in answering questions about weather conditions, 
temperatures, forecasts, and climate data for cities around the world. 

I can help you with:
- Current weather conditions in any city
- Historical weather data and trends
- Temperature averages and statistics
- Weather comparisons between cities

I'm not able to answer questions outside of weather and climate topics. If you have a weather-related question, 
I'd be happy to help!"""
            
            # Create a chat completion with function calling
            messages = [
                {
                    "role": "system",
                    "content": """You are a helpful weather assistant that can answer questions about weather data 
stored in a database. You have access to current weather data and historical weather data for various cities.

IMPORTANT RULES:
- ONLY answer questions related to weather, climate, temperature, and meteorological conditions
- If asked about non-weather topics, politely decline and redirect to weather questions
- Be concise and friendly
- Include specific numbers (temperatures, humidity, etc.) when available
- If data is not available for a city, politely inform the user
- For average temperature questions, use the calculate_average_temperature tool
- For current weather questions, use the get_current_weather tool
- For historical trends or past weather, use the get_weather_history tool
- If a tool call fails, the system will automatically fall back to the OpenWeatherMap API"""
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
            
            # Initial API call
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            # Handle function calls if any
            messages.append(response.choices[0].message)
            
            # Process tool calls (if any)
            while response.choices[0].message.tool_calls and len(response.choices[0].message.tool_calls) > 0:
                tool_calls = response.choices[0].message.tool_calls
                
                # Execute tool calls
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)  # Parse JSON string
                    
                    # Call the appropriate tool function
                    if function_name in self.tool_functions:
                        tool_result = self.tool_functions[function_name](**function_args)
                        
                        # Serialize tool result to JSON, handling datetime objects
                        if isinstance(tool_result, dict):
                            try:
                                content = json.dumps(tool_result, default=json_serial)
                            except TypeError:
                                # Fallback: convert all values to strings if serialization fails
                                content = json.dumps({k: str(v) for k, v in tool_result.items()}, default=json_serial)
                        else:
                            content = str(tool_result)
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": content
                        })
                    else:
                        logger.warning(f"Unknown tool function: {function_name}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": f"Error: Unknown tool function {function_name}"
                        })
                
                # Get next response from the model
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=self.tools
                )
                messages.append(response.choices[0].message)
            
            # Return the final response
            return response.choices[0].message.content
            
        except RateLimitError as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                logger.error(f"OpenAI API quota exceeded: {e}")
                return """I'm unable to process your query because the OpenAI API quota has been exceeded. 
Please check your OpenAI account billing and quota at https://platform.openai.com/account/billing
Once you've resolved the quota issue, you can try again."""
            else:
                logger.error(f"OpenAI API rate limit error: {e}")
                return f"I'm experiencing rate limiting from the OpenAI API. Please wait a moment and try again. Error: {str(e)}"
        except APIError as e:
            logger.exception(f"OpenAI API error: {e}")
            return f"I encountered an API error while processing your query: {str(e)}. Please check your OpenAI API key and account status."
        except Exception as e:
            logger.exception(f"Error processing query: {e}")
            return f"I encountered an error while processing your query: {str(e)}"
    
    def chat(self, model: str = "gpt-4o-mini"):
        """
        Start an interactive chat session with the agent.
        
        Args:
            model: The OpenAI model to use
        """
        print("Weather Agent is ready! Type 'quit' or 'exit' to end the conversation.")
        print("-" * 60)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("\nAgent: ", end="", flush=True)
                response = self.query(user_input, model=model)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.exception(f"Error in chat session: {e}")
                print(f"\nError: {str(e)}")

