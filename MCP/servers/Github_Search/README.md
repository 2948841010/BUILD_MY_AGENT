# Tool Name: GitHub Search

## 🧠 Tool Description

A comprehensive GitHub repository search and analysis tool that provides:
- **Advanced Search**: Multi-dimensional search with AND/OR/NOT operators
- **Repository Information**: Detailed repository information retrieval
- **Directory Browsing**: Navigate project file structures
- **File Content Viewing**: Read specific files from repositories
- **Language Analysis**: Programming language statistics
- **Smart Caching**: Local storage for improved performance

## 🚀 Features

- **Multi-dimensional Search**: Advanced search with logical operators (AND, OR, NOT)
- **Directory Navigation**: Browse repository file and folder structures
- **File Content Access**: Read and analyze specific files within repositories  
- **Detailed Analysis**: Comprehensive repository information including stats, owner details, and README preview
- **Language Statistics**: Analyze programming languages used in repositories with byte counts and percentages
- **Smart Caching**: Local storage of search results to reduce API calls

## 📖 Usage Examples

### Basic Search
```python
# Search for machine learning repositories
search_repositories("machine learning", max_results=10, sort="stars")
```

### Advanced Search with Logical Operators
```python
# Find repositories containing both SpringBoot and Vue
search_repositories("springboot AND vue", search_mode="advanced")

# Find repositories with React or Vue
search_repositories("react OR vue", search_mode="advanced")

# Find Python projects excluding Django
search_repositories("python NOT django", search_mode="advanced")
```

### Get Repository Details
```python
# Get detailed information about a specific repository
get_repository_info("tensorflow/tensorflow")
```

### Browse Repository Structure
```python
# View root directory
get_repository_tree("owner/repository")

# View specific directory
get_repository_tree("owner/repository", "src/main/java")
```

### Read File Contents
```python
# Read configuration files
get_repository_file_content("owner/repository", "package.json")
get_repository_file_content("owner/repository", "pom.xml")

# Read documentation
get_repository_file_content("owner/repository", "README.md", max_size=50000)
```

### Analyze Languages
```python
# Get programming language statistics
get_repository_languages("microsoft/vscode")
```

### Complete Workflow Example
```python
# 1. Search for projects with specific tech stack
repos = search_repositories("springboot AND vue", search_mode="advanced")

# 2. Get details for each repository
for repo in repos:
    info = get_repository_info(repo)
    
    # 3. Browse project structure
    structure = get_repository_tree(repo)
    
    # 4. Check configuration files to verify Redis usage
    config = get_repository_file_content(repo, "application.yml")
    # Look for Redis configuration in the config content
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