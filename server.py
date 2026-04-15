from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
from fastmcp import FastMCP
import httpx
import os
from typing import Optional

mcp = FastMCP("Cat Facts API")

BASE_URL = "https://cat-fact.herokuapp.com"


@mcp.tool()
async def get_facts(
    animal_type: Optional[str] = "cat",
    amount: Optional[int] = 1,
    status: Optional[str] = "verified"
) -> dict:
    """Retrieve cat facts from the Cat Facts API. Use this when the user wants to browse, search, or get a random cat fact. Supports filtering by animal type, status, and pagination."""
    params = {}
    if animal_type:
        params["animal_type"] = animal_type
    if amount is not None:
        params["amount"] = amount
    if status and status != "all":
        params["status"] = status

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/facts", params=params)
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "data": data,
                "count": len(data) if isinstance(data, list) else 1
            }
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def get_fact_by_id(fact_id: str) -> dict:
    """Retrieve a specific cat fact by its unique ID. Use this when you have a fact ID and need to look up its full details."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/facts/{fact_id}")
            response.raise_for_status()
            data = response.json()
            return {"success": True, "data": data}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def submit_fact(
    text: str,
    animal_type: Optional[str] = "cat",
    source: Optional[str] = None
) -> dict:
    """Submit a new cat fact to the Cat Facts database for review. Use this when the user wants to contribute their own interesting animal fact. Facts are submitted with 'unverified' status until reviewed by an admin."""
    payload = {
        "text": text,
        "type": animal_type or "cat",
        "status": {"verified": False}
    }
    if source:
        payload["source"] = source

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/facts",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            return {"success": True, "data": data, "message": "Fact submitted successfully and is pending review."}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def manage_recipients(
    action: str,
    phone_number: Optional[str] = None,
    name: Optional[str] = None
) -> dict:
    """Add, list, or remove recipients who will receive daily cat facts via SMS. Use this when the user wants to manage their list of friends/contacts to prank with cat facts."""
    action = action.lower().strip()

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            if action == "list":
                response = await client.get(f"{BASE_URL}/users/me/recipients")
                response.raise_for_status()
                data = response.json()
                return {"success": True, "action": "list", "data": data}

            elif action == "add":
                if not phone_number:
                    return {"success": False, "error": "phone_number is required for 'add' action"}
                # Clean phone number - remove non-digits
                cleaned = "".join(filter(str.isdigit, phone_number)).lstrip("1")
                if len(cleaned) not in (10, 11):
                    return {"success": False, "error": "Phone number must be 10 or 11 digits"}
                payload = {"phoneNumber": cleaned}
                if name:
                    payload["name"] = name
                response = await client.post(
                    f"{BASE_URL}/users/me/recipients",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                data = response.json()
                return {"success": True, "action": "add", "data": data, "message": f"Recipient added successfully."}

            elif action == "remove":
                if not phone_number:
                    return {"success": False, "error": "phone_number is required for 'remove' action"}
                cleaned = "".join(filter(str.isdigit, phone_number)).lstrip("1")
                response = await client.delete(
                    f"{BASE_URL}/users/me/recipients/{cleaned}"
                )
                response.raise_for_status()
                return {"success": True, "action": "remove", "message": f"Recipient with phone number {cleaned} removed successfully."}

            else:
                return {"success": False, "error": f"Unknown action '{action}'. Valid actions are: 'list', 'add', 'remove'"}

        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def send_fact(
    recipient_id: Optional[str] = None,
    fact_id: Optional[str] = None
) -> dict:
    """Manually send a cat fact via SMS to one or all recipients immediately, without waiting for the daily scheduled send. Use this when the user wants to send a fact on demand."""
    payload = {}
    if fact_id:
        payload["factId"] = fact_id

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            if recipient_id:
                url = f"{BASE_URL}/users/me/recipients/{recipient_id}/send"
            else:
                url = f"{BASE_URL}/users/me/recipients/send"

            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            target = f"recipient {recipient_id}" if recipient_id else "all recipients"
            return {"success": True, "data": data, "message": f"Cat fact sent to {target}."}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def authenticate_user(
    action: str,
    provider: Optional[str] = "google"
) -> dict:
    """Authenticate a user with the Cat Facts API using Google OAuth or local credentials. Use this to log in, log out, or check the current authentication status before performing actions that require authorization."""
    action = action.lower().strip()

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            if action == "status":
                response = await client.get(f"{BASE_URL}/users/me")
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "action": "status", "authenticated": True, "data": data}
                elif response.status_code in (401, 403):
                    return {"success": True, "action": "status", "authenticated": False, "message": "Not currently authenticated."}
                else:
                    return {"success": True, "action": "status", "authenticated": False, "message": f"Unexpected status: {response.status_code}"}

            elif action == "login":
                login_url = f"{BASE_URL}/auth/{provider or 'google'}"
                return {
                    "success": True,
                    "action": "login",
                    "message": f"To log in with {provider or 'google'}, please visit the following URL in your browser:",
                    "login_url": login_url
                }

            elif action == "logout":
                response = await client.get(f"{BASE_URL}/auth/logout")
                if response.status_code in (200, 302):
                    return {"success": True, "action": "logout", "message": "Logged out successfully."}
                else:
                    return {"success": False, "error": f"Logout failed with status {response.status_code}"}

            else:
                return {"success": False, "error": f"Unknown action '{action}'. Valid actions are: 'login', 'logout', 'status'"}

        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def get_conversation(
    recipient_id: str,
    limit: Optional[int] = 20,
    page: Optional[int] = 1
) -> dict:
    """Retrieve the catversation (chat history) between the Catbot and a specific recipient. Use this to view the SMS exchange history, see how recipients responded to cat facts, and review Catbot auto-replies."""
    params = {}
    if limit is not None:
        params["limit"] = limit
    if page is not None:
        params["page"] = page

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/users/me/recipients/{recipient_id}/conversation",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "recipient_id": recipient_id,
                "page": page,
                "limit": limit,
                "data": data
            }
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def get_api_logs(
    limit: Optional[int] = 50,
    page: Optional[int] = 1,
    filter_endpoint: Optional[str] = None,
    filter_status: Optional[int] = None
) -> dict:
    """Retrieve API usage logs for monitoring and debugging. Use this when an admin needs to audit API activity, troubleshoot issues, or review request history including IP addresses, endpoints hit, and response codes."""
    params = {}
    if limit is not None:
        params["limit"] = limit
    if page is not None:
        params["page"] = page
    if filter_endpoint:
        params["endpoint"] = filter_endpoint
    if filter_status is not None:
        params["status"] = filter_status

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/admin/logs", params=params)
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "page": page,
                "limit": limit,
                "filters": {
                    "endpoint": filter_endpoint,
                    "status": filter_status
                },
                "data": data
            }
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}




async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

mcp_app = mcp.http_app(transport="streamable-http")

class _FixAcceptHeader:
    """Ensure Accept header includes both types FastMCP requires."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            accept = headers.get(b"accept", b"").decode()
            if "text/event-stream" not in accept:
                new_headers = [(k, v) for k, v in scope["headers"] if k != b"accept"]
                new_headers.append((b"accept", b"application/json, text/event-stream"))
                scope = dict(scope, headers=new_headers)
        await self.app(scope, receive, send)

app = _FixAcceptHeader(Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", mcp_app),
    ],
    lifespan=mcp_app.lifespan,
))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
