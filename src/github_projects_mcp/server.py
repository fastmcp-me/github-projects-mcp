#!/usr/bin/env python3
"""
GitHub Projects V2 MCP Server

A Model Context Protocol server that provides tools for managing GitHub Projects V2.
"""

import json
import logging
import os
from typing import Any, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from .github_client import GitHubClient, GitHubClientError

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP(
    name="GitHub Projects V2",
    instructions="This server provides tools for managing GitHub Projects V2.",
)

# GitHub client for GraphQL API interactions
github_client = GitHubClient(
    token=os.environ.get("GITHUB_TOKEN"),
)

# --- Tool definitions ---


@mcp.tool()
async def list_projects(owner: str) -> str:
    """List GitHub Projects V2 for a given organization or user.

    Args:
        owner: The GitHub organization or user name

    Returns:
        A formatted string with project details
    """
    try:
        projects = await github_client.get_projects(owner)

        if not projects:
            return f"No projects found for {owner}"

        result = f"Projects for {owner}:\n\n"
        for project in projects:
            result += f"- ID: {project['id']}\n"
            result += f"  Number: {project['number']}\n"
            result += f"  Title: {project['title']}\n"
            result += f"  URL: {project['url']}\n"
            result += "\n"

        return result
    except GitHubClientError as e:
        logger.error(f"Error listing projects for {owner}: {e}")
        return f"Error: Could not list projects for {owner}. Details: {e}"


@mcp.tool()
async def get_project_fields(owner: str, project_number: int) -> str:
    """Get fields available in a GitHub Project V2.

    Args:
        owner: The GitHub organization or user name
        project_number: The project number

    Returns:
        A formatted string with field details
    """
    try:
        fields = await github_client.get_project_fields(owner, project_number)

        if not fields:
            return f"No fields found for project #{project_number} in {owner}"

        result = f"Fields for project #{project_number} in {owner}:\n\n"
        for field in fields:
            result += f"- ID: {field['id']}\n"
            result += f"  Name: {field['name']}\n"
            result += f"  Type: {field['__typename']}\n"

            # If single select field, show options
            if field.get("options"):
                result += f"  Options:\n"
                for option in field["options"]:
                    result += f"    - {option['name']} (ID: {option['id']})\n"

            # If iteration field, show iterations
            if field.get("configuration") and field["configuration"].get("iterations"):
                result += f"  Iterations:\n"
                for iteration in field["configuration"]["iterations"]:
                    result += f"    - {iteration.get('title', 'Unnamed')} "
                    result += f"(ID: {iteration['id']}, "
                    result += f"Start: {iteration.get('startDate', 'N/A')})\n"

            result += "\n"

        return result
    except GitHubClientError as e:
        logger.error(f"Error getting fields for project {owner}/{project_number}: {e}")
        return f"Error: Could not get fields for project {owner}/{project_number}. Details: {e}"


@mcp.tool()
async def get_project_items(
    owner: str, project_number: int, limit: int = 20, state: Optional[str] = None
) -> str:
    """Get items in a GitHub Project V2.

    Args:
        owner: The GitHub organization or user name
        project_number: The project number
        limit: Maximum number of items to return (default: 20)
        state: Optional state to filter items by (e.g., "OPEN", "CLOSED").
               Applies only to linked Issues and Pull Requests, not Draft Issues.

    Returns:
        A formatted string with item details
    """
    try:
        items = await github_client.get_project_items(
            owner, project_number, limit, state
        )

        if not items:
            state_msg = f" with state '{state.upper()}'" if state else ""
            return f"No items found in project #{project_number} for {owner}{state_msg}"

        state_msg = f" (State: {state.upper()})" if state else ""
        result = f"Items in project #{project_number} for {owner}{state_msg}:\n\n"
        for item in items:
            content = item.get("content", {})
            result += f"- Item ID: {item['id']}\n"

            # Handle different content types
            item_type = content.get("__typename")
            if item_type == "Issue":
                result += f"  Type: Issue\n"
                result += f"  Number: #{content.get('number')}\n"
                result += f"  Title: {content.get('title')}\n"
                result += f"  State: {content.get('state')}\n"
                result += f"  URL: {content.get('url')}\n"
                repo_info = content.get("repository", {})
                result += f"  Repo: {repo_info.get('owner', {}).get('login')}/{repo_info.get('name')}\n"
            elif item_type == "PullRequest":
                result += f"  Type: Pull Request\n"
                result += f"  Number: #{content.get('number')}\n"
                result += f"  Title: {content.get('title')}\n"
                result += f"  State: {content.get('state')}\n"
                result += f"  URL: {content.get('url')}\n"
                repo_info = content.get("repository", {})
                result += f"  Repo: {repo_info.get('owner', {}).get('login')}/{repo_info.get('name')}\n"
            elif item_type == "DraftIssue":
                result += f"  Type: Draft Issue\n"
                result += f"  ID: {content.get('id')}\n"  # Use DraftIssue ID
                result += f"  Title: {content.get('title')}\n"
            else:
                result += f"  Type: {item_type or 'Unknown'}\n"
                result += f"  Content: {json.dumps(content)}\n"

            # Show processed field values
            if item.get("fieldValues"):
                result += f"  Field Values:\n"
                for field_name, value in item["fieldValues"].items():
                    result += f"    - {field_name}: {value}\n"

            result += "\n"

        return result
    except GitHubClientError as e:
        logger.error(f"Error getting items for project {owner}/{project_number}: {e}")
        return f"Error: Could not get items for project {owner}/{project_number}. Details: {e}"


@mcp.tool()
async def create_issue(owner: str, repo: str, title: str, body: str = "") -> str:
    """Create a new GitHub issue.

    Args:
        owner: The GitHub organization or user name
        repo: The repository name
        title: The issue title
        body: The issue body (optional)

    Returns:
        A formatted string with the created issue details
    """
    try:
        issue = await github_client.create_issue(owner, repo, title, body)
        return (
            f"Issue created successfully!\n\n"
            f"Repository: {owner}/{repo}\n"
            f"Issue Number: #{issue['number']}\n"
            f"Title: {issue['title']}\n"
            f"URL: {issue['url']}\n"
        )
    except GitHubClientError as e:
        logger.error(f"Error creating issue in {owner}/{repo}: {e}")
        return f"Error: Could not create issue in {owner}/{repo}. Details: {e}"


@mcp.tool()
async def add_issue_to_project(
    owner: str,
    project_number: int,
    issue_owner: str,
    issue_repo: str,
    issue_number: int,
) -> str:
    """Add an existing GitHub issue to a Project V2.

    Args:
        owner: The GitHub organization or user name that owns the project
        project_number: The project number
        issue_owner: The owner of the repository containing the issue
        issue_repo: The repository name containing the issue
        issue_number: The issue number

    Returns:
        A formatted string confirming the addition
    """
    try:
        result = await github_client.add_issue_to_project(
            owner, project_number, issue_owner, issue_repo, issue_number
        )
        return (
            f"Successfully added issue {issue_owner}/{issue_repo}#{issue_number} to project #{project_number}!\n"
            f"Item ID: {result['id']}"
        )
    except GitHubClientError as e:
        logger.error(
            f"Error adding issue {issue_owner}/{issue_repo}#{issue_number} to project {owner}/{project_number}: {e}"
        )
        return f"Error: Could not add issue to project. Details: {e}"


@mcp.tool()
async def update_project_item_field(
    owner: str, project_number: int, item_id: str, field_id: str, field_value: str
) -> str:
    """Update a field value for a project item.

    Args:
        owner: The GitHub organization or user name
        project_number: The project number
        item_id: The ID of the item to update
        field_id: The ID of the field to update
        field_value: The new value for the field (text, date, or option ID for single select)

    Returns:
        A confirmation message
    """
    try:
        # The GitHub client's update method expects the raw value, not just string
        # We might need a way to parse field_value based on field_id or context
        # For now, we pass the string directly, but this might fail for non-text fields.
        # A better implementation would fetch field info first to determine expected type.
        logger.warning(
            f"Attempting to update field {field_id} with value '{field_value}'. Type conversion might be needed."
        )

        # Attempt basic type inference (example - needs improvement)
        parsed_value: Any = field_value
        try:
            parsed_value = float(field_value)
            if parsed_value.is_integer():
                parsed_value = int(parsed_value)
        except ValueError:
            # Check if looks like a date?
            pass  # Keep as string if not obviously numeric

        result = await github_client.update_project_item_field(
            owner,
            project_number,
            item_id,
            field_id,
            parsed_value,  # Pass potentially parsed value
        )
        return (
            f"Successfully updated field for item in project #{project_number}!\n"
            f"Item ID: {item_id}\n"
            f"Field ID: {field_id}\n"
            f"Value Set: {field_value}"  # Report the value as passed to the tool
        )
    except GitHubClientError as e:
        logger.error(f"Error updating field {field_id} for item {item_id}: {e}")
        return f"Error: Could not update field value. Details: {e}"


@mcp.tool()
async def create_draft_issue(
    owner: str, project_number: int, title: str, body: str = ""
) -> str:
    """Create a draft issue directly in a GitHub Project V2.

    Args:
        owner: The GitHub organization or user name
        project_number: The project number
        title: The draft issue title
        body: The draft issue body (optional)

    Returns:
        A confirmation message with the new draft issue details
    """
    try:
        result = await github_client.add_draft_issue_to_project(
            owner, project_number, title, body
        )
        return (
            f"Successfully created draft issue in project #{project_number}!\n"
            f"Item ID: {result['id']}\n"
            f"Title: {title}"
        )
    except GitHubClientError as e:
        logger.error(f"Error creating draft issue in project {project_number}: {e}")
        return f"Error: Could not create draft issue. Details: {e}"


@mcp.tool()
async def delete_project_item(owner: str, project_number: int, item_id: str) -> str:
    """Delete an item from a GitHub Project V2.

    Args:
        owner: The GitHub organization or user name
        project_number: The project number
        item_id: The ID of the item to delete

    Returns:
        A confirmation message
    """
    try:
        deleted_item_id = await github_client.delete_project_item(
            owner, project_number, item_id
        )
        return (
            f"Successfully deleted item from project #{project_number}!\n"
            f"Deleted Item ID: {deleted_item_id}"
        )
    except GitHubClientError as e:
        logger.error(
            f"Error deleting item {item_id} from project {project_number}: {e}"
        )
        return f"Error: Could not delete item. Details: {e}"


# --- Search Tool ---
@mcp.tool()
async def search_project_items(  # Note: Renamed from search_project_issues for clarity
    owner: str, project_number: int, search_query: str, limit: int = 10
) -> str:
    """Search for Issues or Pull Requests within a specific GitHub Project V2 using GitHub's search syntax.

    This searches across GitHub issues/PRs and filters for those linked to the project.
    It WILL NOT find Draft Issues, as they are not searchable via the standard GitHub search.

    Args:
        owner: The GitHub organization or user name that owns the project.
        project_number: The project number.
        search_query: The search query string. Supports GitHub issue search syntax
                      (e.g., "bug label:backend", "assignee:user state:open keyword").
                      Use "repo:owner/repo-name" to scope the search for efficiency.
        limit: Maximum number of *matching project items* to return (default: 10).

    Returns:
        A formatted string listing the project items matching the search query.
    """
    try:
        # 1. Call the new github_client method
        matching_items = await github_client.search_and_filter_project_items(
            owner=owner,
            project_number=project_number,
            search_query=search_query,
            limit=limit,
        )

        if not matching_items:
            return f"No items found in project #{project_number} matching query: '{search_query}'"

        # 2. Format the results (reuse formatting logic)
        result = (
            f"Found items in project #{project_number} matching '{search_query}':\n\n"
        )
        for item in matching_items:
            content = item.get("content", {})
            result += f"- Item ID: {item['id']}\n"
            item_type = content.get("__typename")
            repo_info = content.get("repository", {})
            repo_str = (
                f"{repo_info.get('owner', {}).get('login')}/{repo_info.get('name')}"
                if repo_info
                else "N/A"
            )

            if item_type == "Issue":
                result += f"  Type: Issue #{content.get('number')} ({repo_str})\n"
                result += f"  Title: {content.get('title')}\n"
                result += f"  State: {content.get('state')}\n"
                result += f"  URL: {content.get('url')}\n"
            elif item_type == "PullRequest":
                result += f"  Type: PR #{content.get('number')} ({repo_str})\n"
                result += f"  Title: {content.get('title')}\n"
                result += f"  State: {content.get('state')}\n"
                result += f"  URL: {content.get('url')}\n"
            # Draft issues are not searchable via this method
            else:
                result += f"  Type: {item_type or 'Unknown'}\n"
                result += f"  Content: {json.dumps(content)}\n"

            # Add field values if needed
            if item.get("fieldValues"):
                result += f"  Field Values:\n"
                for field_name, value in item["fieldValues"].items():
                    result += f"    - {field_name}: {value}\n"

            result += "\n"
        return result

    except GitHubClientError as e:
        logger.error(f"Error searching project {owner}/{project_number}: {e}")
        return f"Error searching project items. Details: {e}"
    except ValueError as e:  # Catch potential validation errors from client
        logger.error(f"Invalid input for search: {e}")
        return f"Error: Invalid search input. {e}"


# --- Helper for updating project item field ---
# TODO: Add a helper tool to get field details (ID, name, type) to allow
#       users/LLM to specify fields by name and provide correct value types.
# Example:
# @mcp.tool()
# async def get_project_field_details(owner: str, project_number: int, field_name: str) -> str:
#    ...


# Main entry point function that can be imported
def main():
    """Main entry point for the GitHub Projects MCP server.

    Checks for required environment variables and starts the MCP server.
    """
    # Check for GitHub token
    if not os.environ.get("GITHUB_TOKEN"):
        logger.error("GITHUB_TOKEN environment variable is required")
        print("Error: GITHUB_TOKEN environment variable is required")
        exit(1)

    # Run the MCP server
    mcp.run(transport="stdio")


# Run the main function if executed directly
if __name__ == "__main__":
    main()
