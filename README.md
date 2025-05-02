# GitHub Projects V2 MCP Server

A Model Context Protocol (MCP) server that provides tools for managing GitHub
Projects V2 through Claude and other MCP clients. This server uses the GitHub
GraphQL API for interacting with GitHub Projects V2.

## Features

- List and view GitHub Projects V2 for users and organizations
- Get project fields and items (issues, PRs, draft issues)
- Create issues and add them to projects
- Create draft issues directly in projects
- Update project item field values
- Delete items from projects

## Usage

This server can be used with any MCP client, such as Claude Desktop. Add it to
your MCP client configuration (e.g., `claude_desktop_config.json`).

### Option 1: Using Published Package

Here's an example configuration using `uvx` as the command runner:

```json
{
  "mcpServers": {
    "github-projects": {
      "command": "uvx",
      "args": [
        "mcp-github-projects"
      ],
      "env": {
        "GITHUB_TOKEN": "your_pat_here"
      }
    }
  }
}
```

Make sure to replace `your_pat_here` with your actual GitHub Personal Access
Token.

### Option 2: From Source Code

To run the project directly from source code, follow these steps:

#### Setup

1. Clone the repository:

   ```
   git clone git@github.com:Arclio/github-projects-mcp.git
   cd github-projects-mcp
   ```

2. Create and activate a virtual environment:

   ```
   uv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```
   uv pip install -e .
   ```

4. Set your GitHub token as an environment variable:

   [Create a GitHub Personal Access Token](https://github.com/settings/personal-access-tokens/new) and give it the necessary permissions.
   The required permissions are: `repo`, `project`, and `read:org`.


   Add the token to your `.env` file after running this command:

   ```
   cp .env.example .env
   ```

   Then add the following to your `.env` file:

   ```
   export GITHUB_TOKEN=your_personal_access_token
   ```

### Usage from source code

  When using from source code, configure your MCP client as follows:

  ```json
  {
    "mcpServers": {
      "github-projects": {
        "command": "uv",
        "args": [
          "--directory",
          "/path/to/github-projects-mcp",
          "run",
          "mcp-github-projects"
        ],
        "env": {
          "GITHUB_TOKEN": "your_pat_here"
        }
      }
    }
  }
  ```

  Make sure to replace `/path/to/github-projects-mcp` and `your_pat_here` with
  your actual repository path and GitHub Personal Access Token.

## Available Tools

- `list_projects`: List GitHub Projects V2 for a given organization or user
- `get_project_fields`: Get fields available in a GitHub Project V2
- `get_project_items`: Get items in a GitHub Project V2 (supports filtering by
  state or custom single-select fields)
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
