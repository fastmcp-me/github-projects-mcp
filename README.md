# GitHub Projects V2 MCP Server

A Model Context Protocol (MCP) server that provides tools for managing GitHub Projects V2 through Claude and other MCP clients. This server uses the GitHub GraphQL API for interacting with GitHub Projects V2.

## Features

- List and view GitHub Projects V2 for users and organizations
- Get project fields and items (issues, PRs, draft issues)
- Create issues and add them to projects
- Create draft issues directly in projects
- Update project item field values
- Delete items from projects

## Setup

1. Install dependencies:
   ```
   uv pip install .
   ```
   
   Or install direct dependencies:
   ```
   uv pip install fastmcp httpx pydantic python-dotenv
   ```

2. Set your GitHub token as an environment variable:
   ```
   export GITHUB_TOKEN=your_personal_access_token
   ```
   Your token needs permissions: `repo`, `project`, and `read:org` scopes.

3. Run the server:
   ```
   ./run_server.sh
   ```
   
   Or run directly:
   ```
   python -m src.github_projects_mcp.server
   ```

## Usage

This server can be used with any MCP client, such as Claude Desktop. Add it to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "github-projects": {
      "command": "python",
      "args": [
        "-m", "src.github_projects_mcp.server"
      ],
      "workingDir": "/path/to/github-projects",
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Available Tools

- `list_projects`: List GitHub Projects V2 for a given organization or user
- `get_project_fields`: Get fields available in a GitHub Project V2
- `get_project_items`: Get items in a GitHub Project V2
- `create_issue`: Create a new GitHub issue
- `add_issue_to_project`: Add an existing GitHub issue to a Project V2
- `update_project_item_field`: Update a field value for a project item
- `create_draft_issue`: Create a draft issue directly in a GitHub Project V2
- `delete_project_item`: Delete an item from a GitHub Project V2

See tool documentation in the server code for detailed usage information.

## Development

The project is structured as follows:

- `src/github_projects_mcp/`: Main package directory
  - `server.py`: MCP server implementation with tool definitions
  - `github_client.py`: GraphQL client for GitHub API interactions

To contribute, make sure to:
1. Add proper error handling for all GraphQL operations
2. Add type annotations for all functions and parameters
3. Update documentation when adding new tools or features
