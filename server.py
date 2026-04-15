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
    fact_id: Optional[str] = None,
    animal_type: Optional[str] = "cat",
    amount: Optional[int] = 1
) -> dict:
    """Retrieve cat facts from the Cat Facts API. Use this to fetch random facts, browse available facts, or get a specific fact by ID."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        if fact_id:
            url = f"{BASE_URL}/facts/{fact_id}"
            response = await client.get(url)
            response.raise_for_status()
            return {"fact": response.json()}
        else:
            url = f"{BASE_URL}/facts/random"
            params = {}
            if animal_type:
                params["animal_type"] = animal_type
            if amount and amount > 1:
                params["amount"] = amount
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return {"facts": data if isinstance(data, list) else [data]}


@mcp.tool()
async def submit_fact(
    text: str,
    animal_type: Optional[str] = "cat",
    user_id: Optional[str] = None
) -> dict:
    """Submit a new user-contributed cat fact to the Cat Facts database for review."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BASE_URL}/facts"
        payload = {
            "text": text,
            "type": animal_type or "cat"
        }
        if user_id:
            payload["user"] = user_id
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return {"result": response.json(), "status": response.status_code}


@mcp.tool()
async def manage_recipients(
    action: str,
    phone_number: Optional[str] = None,
    name: Optional[str] = None,
    recipient_id: Optional[str] = None
) -> dict:
    """Add, list, update, or remove fact recipients (phone numbers) who will receive daily cat fact text messages."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        if action == "list":
            url = f"{BASE_URL}/users/me/recipients"
            response = await client.get(url)
            response.raise_for_status()
            return {"recipients": response.json()}

        elif action == "add":
            if not phone_number:
                return {"error": "phone_number is required for 'add' action"}
            url = f"{BASE_URL}/users/me/recipients"
            payload = {"phoneNumber": phone_number}
            if name:
                payload["name"] = name
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return {"result": response.json(), "status": response.status_code}

        elif action == "update":
            if not recipient_id:
                return {"error": "recipient_id is required for 'update' action"}
            url = f"{BASE_URL}/users/me/recipients/{recipient_id}"
            payload = {}
            if phone_number:
                payload["phoneNumber"] = phone_number
            if name:
                payload["name"] = name
            response = await client.put(url, json=payload)
            response.raise_for_status()
            return {"result": response.json(), "status": response.status_code}

        elif action == "remove":
            if not recipient_id:
                return {"error": "recipient_id is required for 'remove' action"}
            url = f"{BASE_URL}/users/me/recipients/{recipient_id}"
            response = await client.delete(url)
            response.raise_for_status()
            return {"status": response.status_code, "message": "Recipient removed successfully"}

        else:
            return {"error": f"Unknown action '{action}'. Valid actions: 'list', 'add', 'update', 'remove'"}


@mcp.tool()
async def send_fact(
    recipient_id: Optional[str] = None,
    fact_id: Optional[str] = None
) -> dict:
    """Manually trigger sending a cat fact via SMS to one or all recipients."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {}
        if fact_id:
            params["factId"] = fact_id

        if recipient_id:
            url = f"{BASE_URL}/users/me/recipients/{recipient_id}/send"
        else:
            url = f"{BASE_URL}/users/me/recipients/send"

        response = await client.post(url, params=params)
        response.raise_for_status()
        return {"status": response.status_code, "result": response.json()}


@mcp.tool()
async def get_conversation(
    recipient_id: str,
    limit: Optional[int] = 20
) -> dict:
    """Retrieve the SMS conversation history (catversation) between the Catbot and a specific recipient."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BASE_URL}/users/me/recipients/{recipient_id}/conversation"
        params = {}
        if limit:
            params["limit"] = limit
        response = await client.get(url, params=params)
        response.raise_for_status()
        return {"conversation": response.json()}


@mcp.tool()
async def authenticate_user(action: str) -> dict:
    """Authenticate a user via Google OAuth or manage the current session (login, logout, get current user profile)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        if action == "me":
            url = f"{BASE_URL}/users/me"
            response = await client.get(url)
            response.raise_for_status()
            return {"user": response.json()}

        elif action == "login":
            login_url = f"{BASE_URL}/auth/google"
            return {
                "message": "To authenticate with Google OAuth, please visit the following URL in your browser.",
                "login_url": login_url,
                "instructions": "Navigate to the login_url to initiate Google OAuth flow. After authentication, your session will be established."
            }

        elif action == "logout":
            url = f"{BASE_URL}/auth/logout"
            response = await client.get(url)
            response.raise_for_status()
            return {"status": response.status_code, "message": "Logged out successfully"}

        else:
            return {"error": f"Unknown action '{action}'. Valid actions: 'login', 'logout', 'me'"}


@mcp.tool()
async def import_google_contacts(
    access_token: str,
    filter_numbers_only: Optional[bool] = True
) -> dict:
    """Import a user's Google contacts as fact recipients in bulk."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        url = f"{BASE_URL}/users/me/recipients/import"
        payload = {
            "accessToken": access_token,
            "filterNumbersOnly": filter_numbers_only
        }
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return {"result": response.json(), "status": response.status_code}


@mcp.tool()
async def manage_unsubscribe(
    action: str,
    phone_number: str
) -> dict:
    """Handle unsubscribe requests from recipients who no longer want to receive cat facts."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        if action == "unsubscribe":
            url = f"{BASE_URL}/unsubscribe"
            payload = {"phoneNumber": phone_number}
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return {
                "status": response.status_code,
                "message": f"Phone number {phone_number} has been unsubscribed from cat facts.",
                "result": response.json() if response.content else {}
            }

        elif action == "check":
            url = f"{BASE_URL}/unsubscribe/check"
            params = {"phoneNumber": phone_number}
            response = await client.get(url, params=params)
            response.raise_for_status()
            return {
                "phone_number": phone_number,
                "result": response.json()
            }

        else:
            return {"error": f"Unknown action '{action}'. Valid actions: 'unsubscribe', 'check'"}




async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

mcp_app = mcp.http_app(transport="streamable-http")

app = Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", mcp_app),
    ],
    lifespan=mcp_app.lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
