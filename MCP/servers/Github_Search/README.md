# Tool Name: GitHub Search

## 🧠 Tool Description

A comprehensive GitHub repository search and analysis tool that provides:
- Keyword-based repository search with various sorting options
- Detailed repository information retrieval
- Programming language analysis for repositories
- Local caching for improved performance

## 🚀 Features

- **Repository Search**: Search GitHub repositories by keywords with customizable sorting
- **Detailed Analysis**: Get comprehensive repository information including stats, owner details, and README preview
- **Language Statistics**: Analyze programming languages used in repositories with byte counts and percentages
- **Smart Caching**: Local storage of search results to reduce API calls

## 📖 Usage Examples

### Search Repositories
```python
# Search for machine learning repositories
search_repositories("machine learning", max_results=10, sort="stars")
```

### Get Repository Details
```python
# Get detailed information about a specific repository
get_repository_info("tensorflow/tensorflow")
```

### Analyze Languages
```python
# Get programming language statistics
get_repository_languages("microsoft/vscode")
```

## 🔧 Configuration

The tool uses GitHub's public API and doesn't require authentication for basic searches. For higher rate limits, you can set the `GITHUB_TOKEN` environment variable.

## 📖 Citation

If you use this tool in your research, please cite:

```bibtex
@software{github_search,
  title = {GitHub Search MCP Tool},
  author = {AI4Science},
  year = {2024},
  url = {https://github.com/deepmodeling/AI4S-agent-tools}
}
``` 