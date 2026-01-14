"""
GitHub Tool - Provides GitHub API access for exploring public repositories.
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
logger = logging.getLogger('github_tool')

# ---- Tool Input Models ----

class GitHubExploreRepo(BaseModel):
    """Input model for exploring a GitHub repository"""
    owner: str = Field(description="Repository owner (username or organization)")
    repo: str = Field(description="Repository name")

class GitHubSearchRepos(BaseModel):
    """Input model for searching GitHub repositories"""
    query: str = Field(description="Search query for repositories")
    limit: int = Field(default=5, description="Maximum number of results (max 5)")

class GitHubGetFile(BaseModel):
    """Input model for getting a file from GitHub"""
    owner: str = Field(description="Repository owner")
    repo: str = Field(description="Repository name")
    path: str = Field(description="File path in the repository")

# ---- GitHub Tools ----

class GitHubExploreRepoTool(DirectTool):
    """Tool for exploring GitHub repositories"""
    
    def __init__(self):
        super().__init__("explore-repo", "Explore a GitHub repository structure and metadata", GitHubExploreRepo)
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.api_base = "https://api.github.com"
        
    def _execute(self, owner: str, repo: str) -> Dict[str, Any]:
        """Explore repository structure and metadata"""
        
        try:
            # Get repository info
            repo_url = f"{self.api_base}/repos/{owner}/{repo}"
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'j4ne-slack-bot'
            }
            
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'
            
            response = requests.get(repo_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_data = response.json()
                
                # Get root contents
                contents_url = f"{self.api_base}/repos/{owner}/{repo}/contents"
                contents_response = requests.get(contents_url, headers=headers, timeout=10)
                
                contents = []
                if contents_response.status_code == 200:
                    contents_data = contents_response.json()
                    for item in contents_data[:20]:  # Limit to first 20 items
                        contents.append({
                            'name': item.get('name', ''),
                            'type': item.get('type', ''),
                            'path': item.get('path', ''),
                            'size': item.get('size', 0),
                            'download_url': item.get('download_url')
                        })
                
                return {
                    "repository": {
                        "name": repo_data.get('name', ''),
                        "full_name": repo_data.get('full_name', ''),
                        "description": repo_data.get('description', ''),
                        "language": repo_data.get('language', ''),
                        "stars": repo_data.get('stargazers_count', 0),
                        "forks": repo_data.get('forks_count', 0),
                        "open_issues": repo_data.get('open_issues_count', 0),
                        "created_at": repo_data.get('created_at', ''),
                        "updated_at": repo_data.get('updated_at', ''),
                        "clone_url": repo_data.get('clone_url', ''),
                        "html_url": repo_data.get('html_url', '')
                    },
                    "contents": contents,
                    "total_files": len(contents)
                }
            else:
                return {"error": f"Repository {owner}/{repo} not found (HTTP {response.status_code})"}
                
        except Exception as e:
            return {"error": f"Error exploring repository: {str(e)}"}

class GitHubSearchReposTool(DirectTool):
    """Tool for searching GitHub repositories"""
    
    def __init__(self):
        super().__init__("search-repos", "Search for GitHub repositories", GitHubSearchRepos)
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.api_base = "https://api.github.com"
        
    def _execute(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search for GitHub repositories"""
        
        try:
            limit = min(5, max(1, limit))
            
            search_url = f"{self.api_base}/search/repositories"
            params = {
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': limit
            }
            
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'j4ne-slack-bot'
            }
            
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                results = []
                for item in data.get('items', []):
                    results.append({
                        'name': item.get('name', ''),
                        'full_name': item.get('full_name', ''),
                        'description': item.get('description', ''),
                        'language': item.get('language', ''),
                        'stars': item.get('stargazers_count', 0),
                        'forks': item.get('forks_count', 0),
                        'updated_at': item.get('updated_at', ''),
                        'html_url': item.get('html_url', ''),
                        'clone_url': item.get('clone_url', '')
                    })
                
                return {
                    "query": query,
                    "total_count": data.get('total_count', 0),
                    "results": results
                }
            else:
                return {"error": f"Search failed (HTTP {response.status_code}): {response.text}"}
                
        except Exception as e:
            return {"error": f"Error searching repositories: {str(e)}"}

class GitHubGetFileTool(DirectTool):
    """Tool for getting files from GitHub repositories"""
    
    def __init__(self):
        super().__init__("get-file", "Get the contents of a file from a GitHub repository", GitHubGetFile)
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.api_base = "https://api.github.com"
        
    def _execute(self, owner: str, repo: str, path: str) -> Dict[str, Any]:
        """Get file contents from repository"""
        
        try:
            file_url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'j4ne-slack-bot'
            }
            
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'
            
            response = requests.get(file_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                file_data = response.json()
                
                if file_data.get('type') == 'file':
                    content = file_data.get('content', '')
                    if content:
                        import base64
                        try:
                            decoded_content = base64.b64decode(content).decode('utf-8')
                        except UnicodeDecodeError:
                            decoded_content = content  # Keep as base64 if not decodable
                    else:
                        decoded_content = ""
                    
                    return {
                        "name": file_data.get('name', ''),
                        "path": file_data.get('path', ''),
                        "size": file_data.get('size', 0),
                        "content": decoded_content[:10000],  # Limit to 10k characters
                        "encoding": file_data.get('encoding', ''),
                        "html_url": file_data.get('html_url', ''),
                        "truncated": len(decoded_content) >= 10000
                    }
                else:
                    return {"error": f"Path '{path}' is not a file (type: {file_data.get('type')})"}
            else:
                return {"error": f"Failed to get file (HTTP {response.status_code}): {response.text}"}
                
        except Exception as e:
            return {"error": f"Error getting file: {str(e)}"}

# ---- GitHub Tool Provider ----

class GitHubToolProvider(ToolProvider):
    """Provides GitHub API access for public repositories only"""
    
    def __init__(self):
        super().__init__("github")
        self._register_tools()
        
    def _register_tools(self):
        """Register GitHub tools"""
        self.register_tool(GitHubExploreRepoTool())
        self.register_tool(GitHubSearchReposTool())
        self.register_tool(GitHubGetFileTool())