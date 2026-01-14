"""
Web Search Tool - Provides web search functionality for Slack users.
Simple implementation that follows existing tool patterns.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from tools.direct_tools import ToolProvider, DirectTool

# Configure logging
logger = logging.getLogger('web_search_tool')

# ---- Tool Input Models ----

class WebSearch(BaseModel):
    """Input model for web search"""
    query: str = Field(description="Search query to search the web for")
    num_results: int = Field(default=5, description="Number of search results to return (max 5)")

# ---- Web Search Tools ----

class WebSearchTool(DirectTool):
    """Tool for searching the web"""
    
    def __init__(self):
        super().__init__("search", "Search the web for information using a search API", WebSearch)
        self.search_api_key = os.getenv('SEARCH_API_KEY') or os.getenv('SERPER_API_KEY')
        
    def _execute(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Perform web search using available APIs"""
        
        # Validate parameters
        num_results = max(1, min(5, num_results))
        
        if self.search_api_key:
            # Use Serper API (Google Search API alternative)
            return self._search_with_serper(query, num_results)
        else:
            # Fallback to a free search method or return helpful error
            return self._search_fallback(query, num_results)
    
    def _search_with_serper(self, query: str, num_results: int) -> Dict[str, Any]:
        """Search using Serper API"""
        
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': self.search_api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'q': query,
            'num': num_results
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                results = []
                if 'organic' in data:
                    for item in data['organic'][:num_results]:
                        results.append({
                            'title': item.get('title', ''),
                            'link': item.get('link', ''),
                            'snippet': item.get('snippet', ''),
                            'position': item.get('position', 0)
                        })
                
                return {
                    "results": results,
                    "total_results": len(results),
                    "query": query,
                    "search_engine": "Google (via Serper)"
                }
            else:
                return {"error": f"Search API error {response.status_code}: {response.text}"}
                
        except Exception as e:
            logger.error(f"Serper search error: {str(e)}")
            return self._search_fallback(query, num_results)
    
    def _search_fallback(self, query: str, num_results: int) -> Dict[str, Any]:
        """Fallback search method when API is not available"""
        
        # For now, return a helpful message about setting up search API
        return {
            "error": "Web search API not configured. To enable web search, set SEARCH_API_KEY or SERPER_API_KEY environment variable with a Serper API key (https://serper.dev/).",
            "setup_help": {
                "step1": "Get an API key from https://serper.dev/",
                "step2": "Set environment variable: export SERPER_API_KEY=your_key_here",
                "step3": "Restart the application"
            },
            "query": query
        }

# ---- Web Search Tool Provider ----

class WebSearchToolProvider(ToolProvider):
    """Provides web search capabilities"""
    
    def __init__(self):
        super().__init__("web")
        self._register_tools()
        
    def _register_tools(self):
        """Register web search tools"""
        self.register_tool(WebSearchTool())