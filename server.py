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
        amount = max(1, min(500, amount))
        params["amount"] = amount
    if status:
        params["status"] = status

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/facts", params=params)
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
    """Submit a new cat (or other animal) fact to the Cat Facts database for review. Use this when the user wants to contribute a fact they know. Facts are stored as unverified until reviewed by an admin."""
    payload = {
        "text": text,
        "type": animal_type or "cat",
        "status": {"verified": False}
    }
    if source:
        payload["source"] = source

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(f"{BASE_URL}/facts", json=payload)
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
    name: Optional[str] = None,
    phone_number: Optional[str] = None,
    recipient_id: Optional[str] = None
) -> dict:
    """Add, list, or remove recipients who will receive daily cat facts via SMS. Use this to manage the user's personal list of fact recipients (friends to prank with cat facts)."""
    action = action.lower().strip()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if action == "list":
                response = await client.get(f"{BASE_URL}/users/me/recipients")
                response.raise_for_status()
                data = response.json()
                return {"success": True, "data": data}

            elif action == "add":
                if not name or not phone_number:
                    return {"success": False, "error": "Both 'name' and 'phone_number' are required when action is 'add'."}
                # Clean phone number
                cleaned = "".join(c for c in phone_number if c.isdigit())
                if len(cleaned) not in (10, 11):
                    return {"success": False, "error": "Phone number must be 10 or 11 digits."}
                payload = {"name": name, "phoneNumber": cleaned}
                response = await client.post(f"{BASE_URL}/users/me/recipients", json=payload)
                response.raise_for_status()
                data = response.json()
                return {"success": True, "data": data, "message": f"Recipient '{name}' added successfully."}

            elif action == "remove":
                if not recipient_id:
                    return {"success": False, "error": "'recipient_id' is required when action is 'remove'."}
                response = await client.delete(f"{BASE_URL}/users/me/recipients/{recipient_id}")
                response.raise_for_status()
                return {"success": True, "message": f"Recipient {recipient_id} removed successfully."}

            else:
                return {"success": False, "error": f"Unknown action '{action}'. Valid actions: 'list', 'add', 'remove'."}

        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def send_fact(
    recipient_id: Optional[str] = None,
    fact_id: Optional[str] = None
) -> dict:
    """Manually trigger sending a cat fact via SMS to one or all recipients. Use this when the user wants to send a fact immediately rather than waiting for the daily scheduled send."""
    payload = {}
    if recipient_id:
        payload["recipientId"] = recipient_id
    if fact_id:
        payload["factId"] = fact_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(f"{BASE_URL}/users/me/sendFact", json=payload)
            response.raise_for_status()
            data = response.json()
            return {"success": True, "data": data, "message": "Cat fact sent successfully."}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def get_conversation(
    recipient_id: str,
    limit: Optional[int] = 20
) -> dict:
    """Retrieve the SMS conversation history (catversation) between the Catbot and a specific recipient. Use this to view how a recipient has been responding to cat facts and what the Catbot replied."""
    params = {}
    if limit is not None:
        params["limit"] = max(1, limit)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/users/me/recipients/{recipient_id}/conversation",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return {"success": True, "data": data}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def authenticate_user(action: str) -> dict:
    """Authenticate or manage user session for the Cat Facts app. Use this to log in via Google OAuth, check current session status, or log out. Required before accessing protected features like managing recipients."""
    action = action.lower().strip()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if action == "login":
                login_url = f"{BASE_URL}/auth/google"
                return {
                    "success": True,
                    "message": "To log in with Google OAuth, please visit the following URL in your browser:",
                    "login_url": login_url,
                    "instructions": "After logging in, your session will be established with the Cat Facts server."
                }

            elif action == "logout":
                response = await client.get(f"{BASE_URL}/auth/logout")
                return {
                    "success": True,
                    "message": "Logout request sent.",
                    "status_code": response.status_code
                }

            elif action == "status":
                response = await client.get(f"{BASE_URL}/users/me")
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "authenticated": True, "user": data}
                elif response.status_code in (401, 403):
                    return {"success": True, "authenticated": False, "message": "Not currently authenticated."}
                else:
                    return {"success": True, "authenticated": False, "status_code": response.status_code}

            else:
                return {"success": False, "error": f"Unknown action '{action}'. Valid actions: 'login', 'logout', 'status'."}

        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def import_google_contacts(
    max_contacts: Optional[int] = None,
    confirm: Optional[bool] = False
) -> dict:
    """Import contacts from the user's Google account as cat fact recipients in bulk. Use this when the user wants to add many recipients at once from their Google Contacts instead of adding them one by one."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            if not confirm:
                return {
                    "success": True,
                    "message": "This action will import your Google contacts as cat fact recipients. Set 'confirm' to true to proceed.",
                    "warning": "All contacts with valid phone numbers will be imported (or up to max_contacts if specified).",
                    "max_contacts": max_contacts,
                    "requires_authentication": True,
                    "note": "You must be authenticated via Google OAuth before importing contacts. Use authenticate_user with action='login' first."
                }

            params = {}
            if max_contacts is not None:
                params["max"] = max_contacts

            response = await client.get(f"{BASE_URL}/users/me/contacts/import", params=params)
            response.raise_for_status()
            data = response.json()
            return {"success": True, "data": data, "message": "Google contacts imported successfully."}

        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def get_api_logs(
    limit: Optional[int] = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> dict:
    """Retrieve API usage logs for the Cat Facts developer API. Use this for admin/developer purposes to monitor API activity, track usage patterns, or debug issues with API requests."""
    params = {}
    if limit is not None:
        params["limit"] = max(1, limit)
    if start_date:
        params["start"] = start_date
    if end_date:
        params["end"] = end_date

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/logs", params=params)
            response.raise_for_status()
            data = response.json()
            return {"success": True, "data": data}
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
