#!/usr/bin/env python3
"""
GitHub Repository Search MCP Server
仿照Paper_Search实现，提供GitHub项目搜索和解析功能
"""
import sys
from pathlib import Path
import argparse
import requests
import json
import os
from typing import List, Dict, Any
import time
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

REPO_DIR = "repositories"

def parse_args():
    """Parse command line arguments for MCP server."""
    parser = argparse.ArgumentParser(description="GitHub Search MCP Server")
    parser.add_argument('--port', type=int, default=50001, help='Server port (default: 50001)')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    try:
        args = parser.parse_args()
    except SystemExit:
        class Args:
            port = 50001
            host = '0.0.0.0'
            log_level = 'INFO'
        args = Args()
    return args

args = parse_args()
mcp = FastMCP("github_search", port=args.port, host=args.host)


@mcp.tool()
def search_repositories(query: str, max_results: int = 5, sort: str = "stars", search_mode: str = "simple") -> List[str]:
    """
    Search for repositories on GitHub with support for advanced search modes.

    Args:
        query: The search query. 
               Simple mode: "machine learning", "python web framework"
               Advanced mode: Use operators like:
               - "springboot AND vue" (both keywords must be present)
               - "react OR vue" (either keyword present)  
               - "python NOT django" (exclude django)
               - Complex: "(springboot AND vue) OR (react AND redux)"
        max_results: Maximum number of results to retrieve (default: 5)
        sort: Sort criteria - "stars", "forks", "updated" (default: "stars")
        search_mode: "simple" or "advanced" (default: "simple")

    Returns:
        List of repository full names found in the search
    """
    
    # GitHub Search API endpoint
    url = "https://api.github.com/search/repositories"
    
    # 处理搜索查询
    processed_query = query
    if search_mode == "advanced":
        # 将用户友好的操作符转换为GitHub搜索语法
        processed_query = query.replace(" AND ", " ").replace(" OR ", " OR ").replace(" NOT ", " NOT ")
    
    # 构建搜索参数
    params = {
        "q": processed_query,
        "sort": sort,
        "order": "desc",
        "per_page": min(max_results, 100)  # GitHub API限制每页最多100个
    }
    
    try:
        # 发送API请求
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        search_results = response.json()
        repositories = search_results.get("items", [])
        
        # 创建目录存储搜索结果
        safe_query = query.lower().replace(" ", "_").replace("/", "_")
        path = os.path.join(REPO_DIR, safe_query)
        os.makedirs(path, exist_ok=True)
        
        file_path = os.path.join(path, "repositories_info.json")
        
        # 尝试加载已有的仓库信息
        try:
            with open(file_path, "r", encoding="utf-8") as json_file:
                repos_info = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            repos_info = {}
        
        # 处理每个仓库并添加到repos_info
        repo_names = []
        for repo in repositories:
            full_name = repo["full_name"]
            repo_names.append(full_name)
            
            repo_info = {
                'name': repo["name"],
                'full_name': full_name,
                'description': repo.get("description", ""),
                'url': repo["html_url"],
                'clone_url': repo["clone_url"],
                'language': repo.get("language", ""),
                'stars': repo["stargazers_count"],
                'forks': repo["forks_count"],
                'issues': repo["open_issues_count"],
                'created_at': repo["created_at"],
                'updated_at': repo["updated_at"],
                'owner': {
                    'login': repo["owner"]["login"],
                    'type': repo["owner"]["type"],
                    'url': repo["owner"]["html_url"]
                },
                'topics': repo.get("topics", []),
                'license': repo["license"]["name"] if repo.get("license") else None,
                'default_branch': repo["default_branch"]
            }
            repos_info[full_name] = repo_info
        
        # 保存更新的仓库信息到JSON文件
        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(repos_info, json_file, indent=2, ensure_ascii=False)
        
        print(f"Results saved in: {file_path}")
        print(f"Found {len(repo_names)} repositories for query: {query}")
        
        return repo_names
        
    except requests.RequestException as e:
        error_msg = f"Error searching GitHub repositories: {str(e)}"
        print(error_msg)
        return [error_msg]
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return [error_msg]


@mcp.tool()
def get_repository_info(full_name: str) -> str:
    """
    Get detailed information about a specific repository.

    Args:
        full_name: The full name of the repository (e.g., "owner/repository")

    Returns:
        JSON string with repository information if found, error message if not found
    """
    
    # 首先尝试从本地存储中查找
    for item in os.listdir(REPO_DIR) if os.path.exists(REPO_DIR) else []:
        item_path = os.path.join(REPO_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "repositories_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as json_file:
                        repos_info = json.load(json_file)
                        if full_name in repos_info:
                            return json.dumps(repos_info[full_name], indent=2, ensure_ascii=False)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
    
    # 如果本地没有找到，尝试从GitHub API获取
    try:
        url = f"https://api.github.com/repos/{full_name}"
        response = requests.get(url)
        
        if response.status_code == 404:
            return f"Repository '{full_name}' not found on GitHub."
        
        response.raise_for_status()
        repo_data = response.json()
        
        # 获取README内容（如果存在）
        readme_content = ""
        try:
            readme_url = f"https://api.github.com/repos/{full_name}/readme"
            readme_response = requests.get(readme_url)
            if readme_response.status_code == 200:
                readme_data = readme_response.json()
                # GitHub返回base64编码的内容
                import base64
                readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")[:1000]  # 限制长度
        except:
            pass
        
        # 构建详细信息
        detailed_info = {
            'name': repo_data["name"],
            'full_name': repo_data["full_name"],
            'description': repo_data.get("description", ""),
            'url': repo_data["html_url"],
            'clone_url': repo_data["clone_url"],
            'ssh_url': repo_data["ssh_url"],
            'language': repo_data.get("language", ""),
            'stars': repo_data["stargazers_count"],
            'forks': repo_data["forks_count"],
            'watchers': repo_data["watchers_count"],
            'issues': repo_data["open_issues_count"],
            'size': repo_data["size"],
            'created_at': repo_data["created_at"],
            'updated_at': repo_data["updated_at"],
            'pushed_at': repo_data["pushed_at"],
            'owner': {
                'login': repo_data["owner"]["login"],
                'type': repo_data["owner"]["type"],
                'url': repo_data["owner"]["html_url"],
                'avatar_url': repo_data["owner"]["avatar_url"]
            },
            'topics': repo_data.get("topics", []),
            'license': repo_data["license"]["name"] if repo_data.get("license") else None,
            'default_branch': repo_data["default_branch"],
            'archived': repo_data["archived"],
            'disabled': repo_data["disabled"],
            'private': repo_data["private"],
            'readme_preview': readme_content[:500] + "..." if len(readme_content) > 500 else readme_content
        }
        
        return json.dumps(detailed_info, indent=2, ensure_ascii=False)
        
    except requests.RequestException as e:
        error_msg = f"Error fetching repository info from GitHub: {str(e)}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return error_msg


@mcp.tool()
def get_repository_languages(full_name: str) -> str:
    """
    Get programming languages used in a repository.

    Args:
        full_name: The full name of the repository (e.g., "owner/repository")

    Returns:
        JSON string with language statistics
    """
    
    try:
        url = f"https://api.github.com/repos/{full_name}/languages"
        response = requests.get(url)
        
        if response.status_code == 404:
            return f"Repository '{full_name}' not found on GitHub."
        
        response.raise_for_status()
        languages_data = response.json()
        
        # 计算总字节数
        total_bytes = sum(languages_data.values())
        
        # 计算每种语言的百分比
        language_stats = {}
        for language, bytes_count in languages_data.items():
            percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
            language_stats[language] = {
                'bytes': bytes_count,
                'percentage': round(percentage, 2)
            }
        
        result = {
            'repository': full_name,
            'total_bytes': total_bytes,
            'languages': language_stats
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except requests.RequestException as e:
        error_msg = f"Error fetching language data from GitHub: {str(e)}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return error_msg


@mcp.tool()
def get_repository_tree(full_name: str, path: str = "") -> str:
    """
    Get the directory structure of a repository at a specific path.

    Args:
        full_name: The full name of the repository (e.g., "owner/repository")
        path: The path within the repository (default: "" for root directory)

    Returns:
        JSON string with directory structure information
    """
    
    try:
        # GitHub Contents API endpoint
        url = f"https://api.github.com/repos/{full_name}/contents/{path}"
        response = requests.get(url)
        
        if response.status_code == 404:
            return f"Repository '{full_name}' or path '{path}' not found on GitHub."
        
        response.raise_for_status()
        contents_data = response.json()
        
        # 处理返回的内容
        if isinstance(contents_data, list):
            # 这是一个目录，包含多个文件/文件夹
            items = []
            for item in contents_data:
                item_info = {
                    'name': item['name'],
                    'type': item['type'],  # 'file' or 'dir'
                    'size': item['size'] if item['type'] == 'file' else None,
                    'path': item['path'],
                    'download_url': item.get('download_url'),
                    'html_url': item['html_url']
                }
                items.append(item_info)
            
            result = {
                'repository': full_name,
                'path': path if path else "/",
                'type': 'directory',
                'items': items,
                'total_items': len(items)
            }
        else:
            # 这是一个文件
            result = {
                'repository': full_name,
                'path': path,
                'type': 'file',
                'name': contents_data['name'],
                'size': contents_data['size'],
                'download_url': contents_data.get('download_url'),
                'html_url': contents_data['html_url']
            }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except requests.RequestException as e:
        error_msg = f"Error fetching repository tree from GitHub: {str(e)}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return error_msg


@mcp.tool()
def get_repository_file_content(full_name: str, file_path: str, max_size: int = 50000) -> str:
    """
    Get the content of a specific file in a repository.

    Args:
        full_name: The full name of the repository (e.g., "owner/repository")
        file_path: The path to the file within the repository
        max_size: Maximum file size to retrieve in bytes (default: 50000, ~50KB)

    Returns:
        JSON string with file content and metadata
    """
    
    try:
        # GitHub Contents API endpoint for specific file
        url = f"https://api.github.com/repos/{full_name}/contents/{file_path}"
        response = requests.get(url)
        
        if response.status_code == 404:
            return f"Repository '{full_name}' or file '{file_path}' not found on GitHub."
        
        response.raise_for_status()
        file_data = response.json()
        
        # 检查是否是文件而不是目录
        if file_data['type'] != 'file':
            return f"'{file_path}' is not a file, it's a {file_data['type']}."
        
        # 检查文件大小
        file_size = file_data['size']
        if file_size > max_size:
            return f"File '{file_path}' is too large ({file_size} bytes). Maximum allowed size is {max_size} bytes. Use get_repository_tree to browse directories instead."
        
        # 获取文件内容
        content = ""
        if file_data.get('content'):
            import base64
            try:
                # GitHub返回base64编码的内容
                content = base64.b64decode(file_data['content']).decode('utf-8')
            except UnicodeDecodeError:
                # 如果无法解码为UTF-8，可能是二进制文件
                content = f"[Binary file - {file_size} bytes]"
        
        result = {
            'repository': full_name,
            'file_path': file_path,
            'name': file_data['name'],
            'size': file_size,
            'encoding': file_data.get('encoding', 'unknown'),
            'content': content,
            'sha': file_data['sha'],
            'html_url': file_data['html_url'],
            'download_url': file_data.get('download_url')
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except requests.RequestException as e:
        error_msg = f"Error fetching file content from GitHub: {str(e)}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    # Get transport type from environment variable, default to SSE
    transport_type = os.getenv('MCP_TRANSPORT', 'sse')
    mcp.run(transport=transport_type) 