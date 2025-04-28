"""
GitHub GraphQL API client for the GitHub Projects V2 MCP Server.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class GitHubClientError(Exception):
    """Custom exception for GitHubClient errors."""

    pass


class GitHubClient:
    """Client for interacting with the GitHub GraphQL API."""

    def __init__(self, token: Optional[str] = None):
        """Initialize the GitHub client.

        Args:
            token: GitHub personal access token. If None, it will use the GITHUB_TOKEN env var.
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required")

        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v4+json",
        }

    async def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against the GitHub API.

        Args:
            query: The GraphQL query string
            variables: Variables for the GraphQL query

        Returns:
            The parsed JSON response data

        Raises:
            GitHubClientError: If the query fails or returns errors.
        """
        query_variables = variables or {}

        payload = {"query": query, "variables": query_variables}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, headers=self.headers, json=payload, timeout=30.0
                )
                response.raise_for_status()  # Raise HTTP errors
                result = response.json()

                if "errors" in result:
                    error_message = f"GraphQL query errors: {result['errors']}"
                    logger.error(error_message)
                    raise GitHubClientError(error_message)

                data = result.get("data")
                if data is None:
                    # Should not happen if no errors, but safeguard
                    raise GitHubClientError(
                        "GraphQL query returned no data and no errors."
                    )
                return data
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error executing GraphQL query: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error executing GraphQL query: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_projects(self, owner: str) -> List[Dict[str, Any]]:
        """Get Projects V2 for an organization or user.

        Args:
            owner: The GitHub organization or user name

        Returns:
            List of projects

        Raises:
            GitHubClientError: If the owner is not found or projects cannot be retrieved.
        """
        # First determine if this is a user or organization
        query = """
        query GetOwnerType($login: String!) {
          organization(login: $login) {
            id
            login
            __typename
          }
          user(login: $login) {
            id
            login
            __typename
          }
        }
        """

        variables = {"login": owner}

        try:
            result = await self.execute_query(query, variables)
        except GitHubClientError as e:
            logger.error(f"Failed to determine owner type for {owner}: {e}")
            raise  # Re-raise the error

        # Determine if the owner is a user or organization
        owner_type = None
        owner_id = None

        if result.get("organization"):
            owner_type = "organization"
            owner_id = result["organization"]["id"]
        elif result.get("user"):
            owner_type = "user"
            owner_id = result["user"]["id"]
        else:
            error_message = f"Owner {owner} not found or type could not be determined."
            logger.error(error_message)
            raise GitHubClientError(error_message)

        # Now get the projects based on owner type
        if owner_type == "organization":
            query = """
            query GetOrgProjects($login: String!, $first: Int!) {
              organization(login: $login) {
                projectsV2(first: $first) {
                  nodes {
                    id
                    number
                    title
                    shortDescription
                    url
                    closed
                    public
                  }
                }
              }
            }
            """

            variables = {"login": owner, "first": 50}

            try:
                result = await self.execute_query(query, variables)
                if not result.get("organization") or not result["organization"].get(
                    "projectsV2"
                ):
                    raise GitHubClientError(
                        f"Could not retrieve projects for organization {owner}"
                    )
                return result["organization"]["projectsV2"]["nodes"]
            except GitHubClientError as e:
                logger.error(f"Failed to get projects for organization {owner}: {e}")
                raise

        elif owner_type == "user":
            query = """
            query GetUserProjects($login: String!, $first: Int!) {
              user(login: $login) {
                projectsV2(first: $first) {
                  nodes {
                    id
                    number
                    title
                    shortDescription
                    url
                    closed
                    public
                  }
                }
              }
            }
            """

            variables = {"login": owner, "first": 50}

            try:
                result = await self.execute_query(query, variables)
                if not result.get("user") or not result["user"].get("projectsV2"):
                    raise GitHubClientError(
                        f"Could not retrieve projects for user {owner}"
                    )
                return result["user"]["projectsV2"]["nodes"]
            except GitHubClientError as e:
                logger.error(f"Failed to get projects for user {owner}: {e}")
                raise

        # This part should be unreachable if owner_type is determined correctly
        raise GitHubClientError(f"Unexpected error retrieving projects for {owner}")

    async def get_project_node_id(self, owner: str, project_number: int) -> str:
        """Get the node ID of a project.

        Args:
            owner: The GitHub organization or user name
            project_number: The project number

        Returns:
            The project node ID

        Raises:
            GitHubClientError: If the project is not found.
        """
        # First determine if this is a user or organization
        query = """
        query GetProjectId($login: String!, $number: Int!) {
          organization(login: $login) {
            projectV2(number: $number) {
              id
            }
          }
          user(login: $login) {
            projectV2(number: $number) {
              id
            }
          }
        }
        """

        variables = {"login": owner, "number": project_number}

        try:
            result = await self.execute_query(query, variables)
        except GitHubClientError as e:
            logger.error(
                f"Failed to query project ID for {owner}/{project_number}: {e}"
            )
            raise

        if result.get("organization") and result["organization"].get("projectV2"):
            return result["organization"]["projectV2"]["id"]
        elif result.get("user") and result["user"].get("projectV2"):
            return result["user"]["projectV2"]["id"]
        else:
            error_message = f"Project {project_number} not found for owner {owner}."
            logger.error(error_message)
            raise GitHubClientError(error_message)

    async def get_project_fields(
        self, owner: str, project_number: int
    ) -> List[Dict[str, Any]]:
        """Get fields for a GitHub Project V2.

        Args:
            owner: The GitHub organization or user name
            project_number: The project number

        Returns:
            List of fields

        Raises:
            GitHubClientError: If project or fields cannot be retrieved.
        """
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(
                f"Cannot get fields: {e}"
            )  # Already logged in get_project_node_id
            raise

        query = """
        query GetProjectFields($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 50) {
                nodes {
                  ... on ProjectV2Field {
                    id
                    name
                    __typename
                  }
                  ... on ProjectV2IterationField {
                    id
                    name
                    __typename
                    configuration {
                      iterations {
                        id
                        title
                        startDate
                        duration
                      }
                    }
                  }
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    __typename
                    options {
                      id
                      name
                      color
                      description
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"projectId": project_id}

        try:
            result = await self.execute_query(query, variables)
            if not result.get("node") or not result["node"].get("fields"):
                raise GitHubClientError(
                    f"Could not retrieve fields for project {owner}/{project_number}"
                )
            return result["node"]["fields"]["nodes"]
        except GitHubClientError as e:
            logger.error(
                f"Failed to get fields for project {owner}/{project_number}: {e}"
            )
            raise

    async def get_project_items(
        self, owner: str, project_number: int, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get items in a GitHub Project V2.

        Args:
            owner: The GitHub organization or user name
            project_number: The project number
            limit: Maximum number of items to return (default: 20)

        Returns:
            List of project items

        Raises:
            GitHubClientError: If project or items cannot be retrieved.
        """
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot get items: {e}")
            raise

        query = """
        query GetProjectItems($projectId: ID!, $first: Int!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: $first) {
                nodes {
                  id
                  type
                  fieldValues(first: 20) {
                    nodes {
                      ... on ProjectV2ItemFieldTextValue {
                        __typename
                        text
                        field {
                          ... on ProjectV2FieldCommon {
                            name
                          }
                        }
                      }
                      ... on ProjectV2ItemFieldDateValue {
                        __typename
                        date
                        field {
                          ... on ProjectV2FieldCommon {
                            name
                          }
                        }
                      }
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        __typename
                        name
                        field {
                          ... on ProjectV2FieldCommon {
                            name
                          }
                        }
                      }
                      # Add other field value types as needed
                      ... on ProjectV2ItemFieldNumberValue {
                         __typename
                         number
                         field {
                           ... on ProjectV2FieldCommon {
                             name
                           }
                         }
                       }
                      ... on ProjectV2ItemFieldIterationValue {
                         __typename
                         title
                         startDate
                         duration
                         field {
                           ... on ProjectV2FieldCommon {
                             name
                           }
                         }
                       }
                    }
                  }
                  content {
                    ... on Issue {
                      __typename
                      id
                      number
                      title
                      state
                      url
                      repository {
                        name
                        owner {
                          login
                        }
                      }
                    }
                    ... on PullRequest {
                      __typename
                      id
                      number
                      title
                      state
                      url
                      repository {
                        name
                        owner {
                          login
                        }
                      }
                    }
                    ... on DraftIssue {
                      __typename
                      id
                      title
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"projectId": project_id, "first": limit}

        try:
            result = await self.execute_query(query, variables)
            if not result.get("node") or not result["node"].get("items"):
                raise GitHubClientError(
                    f"Could not retrieve items for project {owner}/{project_number}"
                )

            items = result["node"]["items"]["nodes"]

            # Process field values to make them easier to use
            for item in items:
                if item.get("fieldValues") and item["fieldValues"].get("nodes"):
                    processed_values = {}
                    for fv in item["fieldValues"]["nodes"]:
                        field_name = fv.get("field", {}).get("name", "UnknownField")
                        value = "N/A"
                        fv_type = fv.get("__typename")
                        if fv_type == "ProjectV2ItemFieldTextValue":
                            value = fv.get("text", "N/A")
                        elif fv_type == "ProjectV2ItemFieldDateValue":
                            value = fv.get("date", "N/A")
                        elif fv_type == "ProjectV2ItemFieldSingleSelectValue":
                            value = fv.get("name", "N/A")
                        elif fv_type == "ProjectV2ItemFieldNumberValue":
                            value = fv.get("number", "N/A")
                        elif fv_type == "ProjectV2ItemFieldIterationValue":
                            value = f"{fv.get('title', 'N/A')} (Start: {fv.get('startDate', 'N/A')})"
                        # Add other types as needed
                        processed_values[field_name] = value
                    item["fieldValues"] = (
                        processed_values  # Replace original list with dict
                    )

            return items
        except GitHubClientError as e:
            logger.error(
                f"Failed to get items for project {owner}/{project_number}: {e}"
            )
            raise

    async def create_issue(
        self, owner: str, repo: str, title: str, body: str = ""
    ) -> Dict[str, Any]:
        """Create a new GitHub issue.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            title: The issue title
            body: The issue body (optional)

        Returns:
            The created issue data

        Raises:
            GitHubClientError: If repository is not found or issue creation fails.
        """
        query = """
        mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String) {
          createIssue(input: {
            repositoryId: $repositoryId,
            title: $title,
            body: $body
          }) {
            issue {
              id
              number
              title
              url
              state
            }
          }
        }
        """

        # First get the repository ID
        repo_query = """
        query GetRepositoryId($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
          }
        }
        """

        repo_variables = {"owner": owner, "name": repo}

        try:
            repo_result = await self.execute_query(repo_query, repo_variables)
            if not repo_result.get("repository"):
                raise GitHubClientError(f"Repository {owner}/{repo} not found")
        except GitHubClientError as e:
            logger.error(f"Failed to get repository ID for {owner}/{repo}: {e}")
            raise

        repository_id = repo_result["repository"]["id"]

        variables = {"repositoryId": repository_id, "title": title, "body": body}

        try:
            result = await self.execute_query(query, variables)
            if not result.get("createIssue") or not result["createIssue"].get("issue"):
                raise GitHubClientError(f"Failed to create issue in {owner}/{repo}")
            return result["createIssue"]["issue"]
        except GitHubClientError as e:
            logger.error(f"Failed to create issue in {owner}/{repo}: {e}")
            raise

    async def add_issue_to_project(
        self,
        owner: str,
        project_number: int,
        issue_owner: str,
        issue_repo: str,
        issue_number: int,
    ) -> Dict[str, Any]:
        """Add an existing GitHub issue to a Project V2.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            issue_owner: The owner of the repository containing the issue
            issue_repo: The repository name containing the issue
            issue_number: The issue number

        Returns:
            The project item data

        Raises:
            GitHubClientError: If project or issue is not found, or adding fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot add issue: {e}")
            raise

        # Get issue ID
        issue_query = """
        query GetIssueId($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) {
              id
            }
          }
        }
        """

        issue_variables = {
            "owner": issue_owner,
            "repo": issue_repo,
            "number": issue_number,
        }

        try:
            issue_result = await self.execute_query(issue_query, issue_variables)
            if not issue_result.get("repository") or not issue_result["repository"].get(
                "issue"
            ):
                raise GitHubClientError(
                    f"Issue {issue_number} not found in {issue_owner}/{issue_repo}"
                )
        except GitHubClientError as e:
            logger.error(
                f"Failed to get issue ID for {issue_owner}/{issue_repo}#{issue_number}: {e}"
            )
            raise

        issue_id = issue_result["repository"]["issue"]["id"]

        # Add issue to project
        add_query = """
        mutation AddItemToProject($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {
            projectId: $projectId,
            contentId: $contentId
          }) {
            item {
              id
              content {
                ... on Issue {
                  title
                  number
                }
                ... on PullRequest {
                  title
                  number
                }
              }
            }
          }
        }
        """

        variables = {"projectId": project_id, "contentId": issue_id}

        try:
            result = await self.execute_query(add_query, variables)
            if not result.get("addProjectV2ItemById") or not result[
                "addProjectV2ItemById"
            ].get("item"):
                raise GitHubClientError(
                    f"Failed to add issue {issue_number} to project {project_number}"
                )
            return result["addProjectV2ItemById"]["item"]
        except GitHubClientError as e:
            logger.error(
                f"Failed to add issue {issue_number} to project {project_number}: {e}"
            )
            raise

    async def add_draft_issue_to_project(
        self, owner: str, project_number: int, title: str, body: str = ""
    ) -> Dict[str, Any]:
        """Add a draft issue to a GitHub Project V2.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            title: The draft issue title
            body: The draft issue body (optional)

        Returns:
            The project item data

        Raises:
            GitHubClientError: If project not found or adding fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot add draft issue: {e}")
            raise

        # Add draft issue to project
        add_query = """
        mutation AddDraftIssueToProject($projectId: ID!, $title: String!, $body: String) {
          addProjectV2DraftIssue(input: {
            projectId: $projectId,
            title: $title,
            body: $body
          }) {
            projectItem {
              id
            }
          }
        }
        """

        variables = {"projectId": project_id, "title": title, "body": body}

        try:
            result = await self.execute_query(add_query, variables)
            if not result.get("addProjectV2DraftIssue") or not result[
                "addProjectV2DraftIssue"
            ].get("projectItem"):
                raise GitHubClientError(
                    f"Failed to add draft issue to project {project_number}"
                )
            return result["addProjectV2DraftIssue"]["projectItem"]
        except GitHubClientError as e:
            logger.error(f"Failed to add draft issue to project {project_number}: {e}")
            raise

    async def update_project_item_field(
        self,
        owner: str,
        project_number: int,
        item_id: str,
        field_id: str,
        value: Any,  # Value type depends on the field
    ) -> Dict[str, Any]:
        """Update a field value for an item in a GitHub Project V2.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            item_id: The project item ID
            field_id: The field ID to update
            value: The new value (type depends on field: string, number, date, boolean, iteration ID, single select option ID)

        Returns:
            The updated project item data (containing the item ID)

        Raises:
            GitHubClientError: If project not found or update fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot update item field: {e}")
            raise

        # Prepare value based on its type and field ID convention
        # This mapping might need refinement based on actual field types fetched separately
        field_value_input: Dict[str, Any] = {}

        # Heuristic based on ID prefix - A better approach would be to fetch field type first
        if field_id.startswith("PVTSSF_"):  # Single Select Field (assumed prefix)
            if isinstance(value, str):
                field_value_input = {"singleSelectOptionId": value}
            else:
                raise GitHubClientError(
                    f"Invalid value type for single select field {field_id}. Expected option ID string."
                )
        elif field_id.startswith("PVTIF_"):  # Iteration Field (assumed prefix)
            if isinstance(value, str):
                field_value_input = {"iterationId": value}
            else:
                raise GitHubClientError(
                    f"Invalid value type for iteration field {field_id}. Expected iteration ID string."
                )
        # Add more field types based on prefixes or fetched field info
        elif field_id.startswith("PVTF_"):  # Text Field (assumed prefix)
            if isinstance(value, str):
                field_value_input = {"text": value}
            else:  # Attempt to convert
                field_value_input = {"text": str(value)}
        elif field_id.startswith("PVTDF_"):  # Date Field (assumed prefix)
            if isinstance(value, str):  # Assuming date string like YYYY-MM-DD
                field_value_input = {"date": value}
            else:
                raise GitHubClientError(
                    f"Invalid value type for date field {field_id}. Expected date string (YYYY-MM-DD)."
                )
        elif field_id.startswith("PVTNU_"):  # Number Field (assumed prefix)
            if isinstance(value, (int, float)):
                field_value_input = {
                    "number": float(value)
                }  # GraphQL uses Float for numbers
            else:
                raise GitHubClientError(
                    f"Invalid value type for number field {field_id}. Expected int or float."
                )
        else:  # Default to text if type unknown
            logger.warning(
                f"Unknown field type for {field_id}. Attempting to set as text."
            )
            field_value_input = {"text": str(value)}

        # Update field value
        update_query = """
        mutation UpdateProjectFieldValue($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $fieldId,
            value: $value
          }) {
            projectV2Item {
              id
            }
          }
        }
        """

        variables = {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field_id,
            "value": field_value_input,
        }

        try:
            result = await self.execute_query(update_query, variables)
            if not result.get("updateProjectV2ItemFieldValue") or not result[
                "updateProjectV2ItemFieldValue"
            ].get("projectV2Item"):
                raise GitHubClientError(
                    f"Failed to update field value for item {item_id}"
                )
            return result["updateProjectV2ItemFieldValue"]["projectV2Item"]
        except GitHubClientError as e:
            logger.error(f"Failed to update field {field_id} for item {item_id}: {e}")
            raise

    async def delete_project_item(
        self, owner: str, project_number: int, item_id: str
    ) -> str:
        """Delete an item from a GitHub Project V2.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            item_id: The project item ID

        Returns:
            The ID of the deleted item.

        Raises:
            GitHubClientError: If project not found or deletion fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot delete item: {e}")
            raise

        # Delete item
        delete_query = """
        mutation DeleteProjectItem($projectId: ID!, $itemId: ID!) {
          deleteProjectV2Item(input: {
            projectId: $projectId,
            itemId: $itemId
          }) {
            deletedItemId
          }
        }
        """

        variables = {"projectId": project_id, "itemId": item_id}

        try:
            result = await self.execute_query(delete_query, variables)
            if not result.get("deleteProjectV2Item") or not result[
                "deleteProjectV2Item"
            ].get("deletedItemId"):
                raise GitHubClientError(f"Failed to delete item {item_id}")
            return result["deleteProjectV2Item"]["deletedItemId"]
        except GitHubClientError as e:
            logger.error(f"Failed to delete item {item_id}: {e}")
            raise

    async def update_project_settings(
        self,
        owner: str,
        project_number: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        public: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update GitHub Project V2 settings.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            title: New project title (optional)
            description: New project description (optional)
            public: Whether the project should be public (optional)

        Returns:
            The updated project data

        Raises:
            GitHubClientError: If project not found or update fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot update project settings: {e}")
            raise

        # Build input parameters
        input_params: Dict[str, Any] = {"projectId": project_id}  # Use Dict[str, Any]

        if title is not None:
            input_params["title"] = title

        if description is not None:
            input_params["shortDescription"] = description

        if public is not None:
            input_params["public"] = public  # Keep as boolean

        # Update project
        update_query = """
        mutation UpdateProject($input: UpdateProjectV2Input!) {
          updateProjectV2(input: $input) {
            projectV2 {
              id
              title
              shortDescription
              public
              url
            }
          }
        }
        """

        variables = {"input": input_params}

        try:
            result = await self.execute_query(update_query, variables)
            if not result.get("updateProjectV2") or not result["updateProjectV2"].get(
                "projectV2"
            ):
                raise GitHubClientError(f"Failed to update project {project_number}")
            return result["updateProjectV2"]["projectV2"]
        except GitHubClientError as e:
            logger.error(f"Failed to update project {project_number}: {e}")
            raise
