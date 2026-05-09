from __future__ import annotations

import json
import os
from typing import Any, Literal
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP(
    "jira-universal",
    instructions=(
        "Universal Jira Cloud MCP server. Use tools to call any Jira REST endpoint, "
        "including Platform, Agile and other product APIs hosted under the site URL."
    ),
)


class JiraConfigError(RuntimeError):
    """Raised when required Jira configuration is missing."""


class JiraClient:
    def __init__(self) -> None:
        base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
        email = os.getenv("JIRA_EMAIL", "").strip()
        api_token = os.getenv("JIRA_API_TOKEN", "").strip()
        timeout_raw = os.getenv("JIRA_TIMEOUT_SECONDS", "30").strip()

        if not base_url:
            raise JiraConfigError("Missing JIRA_BASE_URL environment variable.")
        if not email:
            raise JiraConfigError("Missing JIRA_EMAIL environment variable.")
        if not api_token:
            raise JiraConfigError("Missing JIRA_API_TOKEN environment variable.")

        try:
            timeout_seconds = int(timeout_raw)
        except ValueError as exc:
            raise JiraConfigError("JIRA_TIMEOUT_SECONDS must be an integer.") from exc

        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.client = httpx.Client(
            auth=(email, api_token),
            timeout=timeout_seconds,
            headers={
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self.client.close()

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        path = path.strip()
        if not path:
            raise ValueError("Path cannot be empty.")

        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            if not path.startswith("/"):
                path = f"/{path}"
            url = f"{self.base_url}{path}"

        if query:
            cleaned = {k: v for k, v in query.items() if v is not None}
            if cleaned:
                query_string = urlencode(cleaned, doseq=True)
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}{query_string}"
        return url

    def request(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | list[Any] | None = None,
        body_text: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(path=path, query=query)

        headers: dict[str, str] = {}
        if extra_headers:
            headers.update(
                {
                    key: str(value)
                    for key, value in extra_headers.items()
                    if value is not None
                }
            )

        request_kwargs: dict[str, Any] = {}
        if body is not None:
            request_kwargs["json"] = body
            headers.setdefault("Content-Type", "application/json")
        elif body_text is not None:
            request_kwargs["content"] = body_text

        response = self.client.request(
            method=method.upper(),
            url=url,
            headers=headers or None,
            **request_kwargs,
        )

        content_type = response.headers.get("content-type", "")
        is_json = "application/json" in content_type.lower()

        parsed_body: Any
        if is_json:
            try:
                parsed_body = response.json()
            except json.JSONDecodeError:
                parsed_body = response.text
        else:
            parsed_body = response.text

        result: dict[str, Any] = {
            "ok": response.is_success,
            "status_code": response.status_code,
            "method": method.upper(),
            "url": url,
            "headers": dict(response.headers),
            "body": parsed_body,
        }

        if not response.is_success:
            result["error"] = {
                "message": f"Jira API returned status {response.status_code}",
                "hint": "Check permissions, endpoint path, request body and query params.",
            }

        return result

    def upload_attachment(
        self, issue_key_or_id: str, file_path: str, filename: str | None = None
    ) -> dict[str, Any]:
        if not issue_key_or_id.strip():
            raise ValueError("issue_key_or_id cannot be empty.")

        file_path = file_path.strip()
        if not file_path:
            raise ValueError("file_path cannot be empty.")
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")

        effective_filename = filename or os.path.basename(file_path)
        url = self._build_url(f"/rest/api/3/issue/{issue_key_or_id}/attachments")

        with open(file_path, "rb") as file_handle:
            response = self.client.post(
                url,
                headers={"X-Atlassian-Token": "no-check"},
                files={"file": (effective_filename, file_handle)},
            )

        content_type = response.headers.get("content-type", "")
        is_json = "application/json" in content_type.lower()

        parsed_body: Any
        if is_json:
            try:
                parsed_body = response.json()
            except json.JSONDecodeError:
                parsed_body = response.text
        else:
            parsed_body = response.text

        result: dict[str, Any] = {
            "ok": response.is_success,
            "status_code": response.status_code,
            "method": "POST",
            "url": url,
            "headers": dict(response.headers),
            "body": parsed_body,
        }

        if not response.is_success:
            result["error"] = {
                "message": f"Jira API returned status {response.status_code}",
                "hint": "Check issue permission and attachment settings in Jira.",
            }

        return result


def _client() -> JiraClient:
    try:
        return JiraClient()
    except JiraConfigError as exc:
        raise ValueError(
            f"Configuration error: {exc} Configure JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN."
        ) from exc


@mcp.tool()
def jira_get(
    path: str,
    query: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """GET any Jira endpoint. Example path: /rest/agile/1.0/board/1"""
    client = _client()
    try:
        return client.request(
            method="GET",
            path=path,
            query=query,
            extra_headers=extra_headers,
        )
    finally:
        client.close()


@mcp.tool()
def jira_post(
    path: str,
    body: dict[str, Any] | list[Any] | None = None,
    body_text: str | None = None,
    query: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """POST to any Jira endpoint."""
    client = _client()
    try:
        return client.request(
            method="POST",
            path=path,
            query=query,
            body=body,
            body_text=body_text,
            extra_headers=extra_headers,
        )
    finally:
        client.close()


@mcp.tool()
def jira_put(
    path: str,
    body: dict[str, Any] | list[Any] | None = None,
    body_text: str | None = None,
    query: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """PUT to any Jira endpoint."""
    client = _client()
    try:
        return client.request(
            method="PUT",
            path=path,
            query=query,
            body=body,
            body_text=body_text,
            extra_headers=extra_headers,
        )
    finally:
        client.close()


@mcp.tool()
def jira_patch(
    path: str,
    body: dict[str, Any] | list[Any] | None = None,
    body_text: str | None = None,
    query: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """PATCH to any Jira endpoint."""
    client = _client()
    try:
        return client.request(
            method="PATCH",
            path=path,
            query=query,
            body=body,
            body_text=body_text,
            extra_headers=extra_headers,
        )
    finally:
        client.close()


@mcp.tool()
def jira_delete(
    path: str,
    query: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """DELETE any Jira endpoint."""
    client = _client()
    try:
        return client.request(
            method="DELETE",
            path=path,
            query=query,
            extra_headers=extra_headers,
        )
    finally:
        client.close()


@mcp.tool()
def jira_request(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | list[Any] | None = None,
    body_text: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Universal Jira request tool for any HTTP method and endpoint."""
    client = _client()
    try:
        return client.request(
            method=method,
            path=path,
            query=query,
            body=body,
            body_text=body_text,
            extra_headers=extra_headers,
        )
    finally:
        client.close()


@mcp.tool()
def jira_upload_attachment(
    issue_key_or_id: str,
    file_path: str,
    filename: str | None = None,
) -> dict[str, Any]:
    """Upload a file to a Jira issue attachment list."""
    client = _client()
    try:
        return client.upload_attachment(
            issue_key_or_id=issue_key_or_id,
            file_path=file_path,
            filename=filename,
        )
    finally:
        client.close()


@mcp.tool()
def jira_healthcheck() -> dict[str, Any]:
    """Validate credentials and connectivity with Jira Cloud."""
    client = _client()
    try:
        return client.request(method="GET", path="/rest/api/3/myself")
    finally:
        client.close()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
