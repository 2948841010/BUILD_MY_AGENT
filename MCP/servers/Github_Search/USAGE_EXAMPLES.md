# GitHub Search MCP Server 使用示例

## 功能概览

增强版的GitHub搜索MCP服务器现在支持以下功能：

1. **多维度搜索** - 支持与或非逻辑操作
2. **项目信息获取** - 获取详细的项目信息
3. **语言统计** - 分析项目使用的编程语言
4. **目录结构浏览** - 查看项目的文件和目录结构
5. **文件内容查看** - 读取特定文件的内容

## 完整工作流程示例

### 场景：寻找包含SpringBoot、Vue和Redis的项目

这是一个典型的多技术栈项目搜索场景。以下是完整的操作流程：

#### 步骤1：高级搜索
```python
# 使用高级搜索查找同时包含SpringBoot和Vue的项目
search_repositories("springboot AND vue", max_results=5, search_mode="advanced")

# 结果示例：
# ['jeecgboot/JeecgBoot', 'YunaiV/ruoyi-vue-pro', 'macrozheng/mall-admin-web', ...]
```

#### 步骤2：获取项目基本信息
```python
# 对每个候选项目获取详细信息
get_repository_info("jeecgboot/JeecgBoot")

# 查看结果中的描述、技术栈信息等
```

#### 步骤3：分析项目结构
```python
# 查看项目根目录
get_repository_tree("jeecgboot/JeecgBoot")

# 查看特定目录（如配置目录）
get_repository_tree("jeecgboot/JeecgBoot", "src/main/resources")
```

#### 步骤4：检查关键配置文件
```python
# 检查依赖文件
get_repository_file_content("jeecgboot/JeecgBoot", "pom.xml")

# 检查配置文件
get_repository_file_content("jeecgboot/JeecgBoot", "src/main/resources/application.yml")

# 检查Docker配置
get_repository_file_content("jeecgboot/JeecgBoot", "docker-compose.yml")
```

## 各功能详细使用方法

### 1. search_repositories - 多维度搜索

#### 基本搜索
```python
search_repositories("machine learning", max_results=5, sort="stars")
```

#### 高级搜索语法
```python
# AND操作 - 必须同时包含
search_repositories("springboot AND vue", search_mode="advanced")

# OR操作 - 包含任一即可
search_repositories("react OR vue", search_mode="advanced")

# NOT操作 - 排除特定关键词
search_repositories("python NOT django", search_mode="advanced")

# 复杂组合
search_repositories("(springboot AND vue) OR (react AND redux)", search_mode="advanced")
```

#### 排序选项
- `stars` - 按star数排序（默认）
- `forks` - 按fork数排序
- `updated` - 按更新时间排序

### 2. get_repository_tree - 目录结构浏览

#### 查看根目录
```python
get_repository_tree("owner/repository")
```

#### 查看特定目录
```python
get_repository_tree("owner/repository", "src/main/java")
get_repository_tree("owner/repository", "frontend/src")
```

#### 返回结果示例
```json
{
  "repository": "owner/repository",
  "path": "/",
  "type": "directory",
  "items": [
    {
      "name": "src",
      "type": "dir",
      "path": "src"
    },
    {
      "name": "README.md",
      "type": "file",
      "size": 1234,
      "path": "README.md"
    }
  ],
  "total_items": 15
}
```

### 3. get_repository_file_content - 文件内容查看

#### 基本用法
```python
get_repository_file_content("owner/repository", "README.md")
```

#### 限制文件大小
```python
get_repository_file_content("owner/repository", "large-file.txt", max_size=100000)
```

#### 常用文件检查
```python
# 检查依赖配置
get_repository_file_content("owner/repository", "package.json")
get_repository_file_content("owner/repository", "pom.xml")
get_repository_file_content("owner/repository", "requirements.txt")

# 检查配置文件
get_repository_file_content("owner/repository", "config/application.yml")
get_repository_file_content("owner/repository", ".env.example")

# 检查Docker配置
get_repository_file_content("owner/repository", "Dockerfile")
get_repository_file_content("owner/repository", "docker-compose.yml")
```

## 实际使用场景

### 场景1：技术栈验证
当你需要验证一个项目是否使用了特定的技术栈时：

1. 搜索包含关键技术的项目
2. 查看项目目录结构
3. 检查配置文件确认技术栈

### 场景2：学习最佳实践
当你想学习某个技术栈的最佳实践时：

1. 搜索高star数的相关项目
2. 浏览项目结构了解组织方式
3. 查看关键配置文件学习配置方法

### 场景3：依赖分析
当你需要了解项目的依赖关系时：

1. 获取项目基本信息
2. 查看依赖配置文件
3. 分析项目使用的技术栈

## 注意事项

1. **API限制**：GitHub API有访问频率限制，请合理使用
2. **文件大小**：默认文件大小限制为50KB，超大文件会被拒绝
3. **网络连接**：需要稳定的网络连接访问GitHub API
4. **搜索语法**：高级搜索使用GitHub搜索语法，注意操作符大小写

## 错误处理

所有函数都包含完善的错误处理机制：

- 网络错误会返回错误信息
- 404错误会明确指出项目或文件不存在
- 文件过大会提示使用目录浏览功能

## 扩展建议

基于这些基础功能，你可以构建更复杂的工作流程：

1. 批量项目分析
2. 技术栈趋势分析
3. 项目质量评估
4. 依赖关系图谱构建 