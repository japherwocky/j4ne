"""
Tool Calling Implementation for Hugging Face Models

This module implements tool calling functionality for Hugging Face models
that don't natively support OpenAI-style function calling.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ToolCallHandler:
    """Handles tool calling for Hugging Face models using prompt engineering"""
    
    def __init__(self):
        # Pattern for the expected format: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
        self.tool_call_pattern = re.compile(
            r'<tool_call>\s*(\{.*?\})\s*</tool_call>',
            re.DOTALL | re.IGNORECASE
        )
        # Pattern for the format the model actually uses: <tool.name>{"param": "value"}</tool.name>
        self.alt_tool_pattern = re.compile(
            r'<([^>]+)>\s*(\{.*?\})',
            re.DOTALL | re.IGNORECASE
        )
    
    def create_tool_prompt(self, tools: List[Dict]) -> str:
        """
        Create a prompt that instructs the model how to use tools.
        
        Args:
            tools: List of tool definitions in OpenAI format
            
        Returns:
            Formatted prompt string for tool usage
        """
        if not tools:
            return ""
        
        tool_descriptions = []
        for tool in tools:
            func_def = tool.get('function', {})
            name = func_def.get('name', 'unknown')
            description = func_def.get('description', 'No description')
            parameters = func_def.get('parameters', {})
            
            # Format parameters
            param_info = []
            if 'properties' in parameters:
                for param_name, param_def in parameters['properties'].items():
                    param_type = param_def.get('type', 'string')
                    param_desc = param_def.get('description', 'No description')
                    required = param_name in parameters.get('required', [])
                    req_str = " (required)" if required else " (optional)"
                    param_info.append(f"  - {param_name} ({param_type}){req_str}: {param_desc}")
            
            tool_desc = f"**{name}**: {description}"
            if param_info:
                tool_desc += "\n" + "\n".join(param_info)
            
            tool_descriptions.append(tool_desc)
        
        prompt = f"""
You have access to the following tools. When a user asks about tools, files, directories, or requests any action, you should use the appropriate tool.

To use a tool, respond with a tool call in this exact format:

<tool_call>
{{"name": "tool_name", "arguments": {{"param1": "value1", "param2": "value2"}}}}
</tool_call>

Available tools:
{chr(10).join(tool_descriptions)}

Examples of when to use tools:
- "what tools do you have?" → Use a tool to show available capabilities
- "list files" → Use filesystem.list-files
- "show me the database" → Use sqlite tools
- "what's in this directory?" → Use filesystem.list-files

If you need to use a tool, format your response exactly as shown above. Only respond normally for simple greetings or general conversation.
"""
        return prompt.strip()
    
    def parse_tool_call(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse a tool call from the model's response.
        
        Args:
            response_text: The model's response text
            
        Returns:
            Tool call dictionary in OpenAI format, or None if no tool call found
        """
        try:
            # First try the expected format: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
            match = self.tool_call_pattern.search(response_text)
            if match:
                json_str = match.group(1)
                tool_data = json.loads(json_str)
                
                # Validate required fields
                if 'name' not in tool_data:
                    logger.warning("Tool call missing 'name' field")
                    return None
                
                # Format in OpenAI style
                tool_call = {
                    "id": f"call_{hash(json_str) % 1000000}",
                    "type": "function",
                    "function": {
                        "name": tool_data['name'],
                        "arguments": json.dumps(tool_data.get('arguments', {}))
                    }
                }
                return tool_call
            
            # Try the alternative format: <tool.name>{"param": "value"}
            alt_match = self.alt_tool_pattern.search(response_text)
            if alt_match:
                tool_name = alt_match.group(1)
                json_str = alt_match.group(2)
                tool_args = json.loads(json_str)
                
                logger.info(f"Detected alternative tool format: {tool_name}")
                
                # Format in OpenAI style
                tool_call = {
                    "id": f"call_{hash(json_str) % 1000000}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args)
                    }
                }
                return tool_call
            
            return None
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse tool call JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing tool call: {e}")
            return None
    
    def format_tool_result(self, tool_name: str, tool_args: Dict, result: Any) -> str:
        """
        Format a tool result for inclusion in the conversation.
        
        Args:
            tool_name: Name of the tool that was called
            tool_args: Arguments passed to the tool
            result: Result from the tool execution
            
        Returns:
            Formatted string for the conversation
        """
        try:
            # Format the result based on its type
            if isinstance(result, dict):
                if "error" in result:
                    formatted_result = f"ERROR: {result['error']}"
                else:
                    formatted_result = json.dumps(result, indent=2)
            elif isinstance(result, str):
                formatted_result = result
            else:
                formatted_result = str(result)
            
            return f"Called tool {tool_name} with arguments {tool_args}, got result:\n{formatted_result}"
            
        except Exception as e:
            logger.error(f"Error formatting tool result: {e}")
            return f"Called tool {tool_name} with arguments {tool_args}, got result: {str(result)}"
    
    def create_system_prompt(self) -> str:
        """
        Create a system prompt that helps the model understand tool calling.
        
        Returns:
            System prompt string
        """
        return """You are a helpful assistant that can use tools to help answer questions and complete tasks. 

When you need to use a tool, format your response with the tool call in XML tags like this:
<tool_call>
{"name": "tool_name", "arguments": {"param1": "value1", "param2": "value2"}}
</tool_call>

After using a tool, you will receive the results and can then provide a helpful response to the user based on those results.

If you don't need to use any tools, respond normally with helpful information."""

    def extract_content_after_tool_call(self, response_text: str) -> str:
        """
        Extract any content that comes after a tool call in the response.
        
        Args:
            response_text: The model's response text
            
        Returns:
            Content after the tool call, or empty string if none
        """
        try:
            match = self.tool_call_pattern.search(response_text)
            if match:
                # Get text after the tool call
                end_pos = match.end()
                remaining_text = response_text[end_pos:].strip()
                return remaining_text
            return ""
        except Exception as e:
            logger.error(f"Error extracting content after tool call: {e}")
            return ""
    
    def has_tool_call(self, response_text: str) -> bool:
        """
        Check if the response contains a tool call.
        
        Args:
            response_text: The model's response text
            
        Returns:
            True if a tool call is found, False otherwise
        """
        return bool(self.tool_call_pattern.search(response_text))
    
    def clean_response_text(self, response_text: str) -> str:
        """
        Clean the response text by removing tool call markers.
        
        Args:
            response_text: The model's response text
            
        Returns:
            Cleaned response text
        """
        try:
            # Remove tool call blocks
            cleaned = self.tool_call_pattern.sub('', response_text)
            return cleaned.strip()
        except Exception as e:
            logger.error(f"Error cleaning response text: {e}")
            return response_text
