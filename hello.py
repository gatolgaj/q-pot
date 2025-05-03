import os
import asyncio
import json
import base64
import uuid
import time
import hmac
import hashlib
import requests
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from mcp.server.fastmcp import FastMCP, Context

# Initialize our MCP server
mcp = FastMCP("Bunq Banking")

# Environment variables for configuration
BUNQ_API_KEY = os.environ.get("BUNQ_API_KEY")
BUNQ_DEVICE_NAME = os.environ.get("BUNQ_DEVICE_NAME", "MCP Server")
BUNQ_ENVIRONMENT = os.environ.get("BUNQ_ENVIRONMENT", "PRODUCTION")  # or "SANDBOX"

# API configuration
API_URL = "https://api.bunq.com" if BUNQ_ENVIRONMENT == "PRODUCTION" else "https://public-api.sandbox.bunq.com"
API_VERSION = "v1"

# Global session data
SESSION = {
    "token": None,
    "server_public_key": None,
    "installation_id": None,
    "private_key": None,
    "public_key": None,
    "user_id": None,
}

# Helper functions for API communication
def generate_key_pair():
    """Generate a new RSA key pair for API authentication."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Get public key in PEM format
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # Get private key in PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    return private_key_pem, public_key

def sign_request(method, endpoint, headers, data=None):
    """Sign the API request with the private key."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    
    if not SESSION["private_key"]:
        return headers
    
    # Create the data to sign
    data_to_sign = f"{method} {endpoint}"
    
    # Add headers to sign
    headers_to_sign = []
    for header_name in sorted(headers.keys()):
        if header_name.lower().startswith("x-bunq-"):
            headers_to_sign.append(f"{header_name}: {headers[header_name]}")
    
    if headers_to_sign:
        data_to_sign += f"\n{'\n'.join(headers_to_sign)}"
    
    # Add request body if present
    if data:
        data_to_sign += f"\n\n{data}"
    
    # Load the private key
    private_key = load_pem_private_key(
        SESSION["private_key"].encode('utf-8'),
        password=None
    )
    
    # Sign the data
    signature = private_key.sign(
        data_to_sign.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    # Add signature to headers
    headers["X-Bunq-Client-Signature"] = base64.b64encode(signature).decode('utf-8')
    
    return headers

def make_request(method, endpoint, data=None, params=None, auth=True):
    """Make a request to the Bunq API."""
    url = f"{API_URL}/{API_VERSION}/{endpoint}"
    
    headers = {
        "Cache-Control": "no-cache",
        "User-Agent": "Bunq MCP Server",
        "X-Bunq-Client-Request-Id": str(uuid.uuid4()),
        "X-Bunq-Geolocation": "0 0 0 0 000",
        "X-Bunq-Language": "en_US",
        "X-Bunq-Region": "en_US",
    }
    
    # Add authentication headers if required
    if auth and SESSION["token"]:
        headers["X-Bunq-Client-Authentication"] = SESSION["token"]
    
    # Convert data to JSON if present
    json_data = None
    if data:
        json_data = json.dumps(data)
        headers["Content-Type"] = "application/json"
    
    # Sign the request if authentication is required
    if auth:
        headers = sign_request(method, f"/{API_VERSION}/{endpoint}", headers, json_data)
    
    # Make the request
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        data=json_data,
        params=params
    )
    
    # Check for errors
    if response.status_code >= 400:
        error_message = f"API Error: {response.status_code}"
        try:
            error_data = response.json()
            if "Error" in error_data:
                error_message = f"API Error: {error_data['Error'][0]['error_description']}"
        except:
            pass
        raise Exception(error_message)
    
    # Return the response data
    try:
        return response.json()
    except:
        return {"raw_response": response.text}

# API initialization functions
def initialize_installation():
    """Create a new installation."""
    # Generate key pair
    private_key, public_key = generate_key_pair()
    
    # Store keys
    SESSION["private_key"] = private_key
    SESSION["public_key"] = public_key
    
    # Create installation
    response = make_request(
        "POST",
        "installation",
        {"client_public_key": public_key},
        auth=False
    )
    
    # Store installation data
    SESSION["installation_id"] = response["Response"][1]["Id"]["id"]
    SESSION["server_public_key"] = response["Response"][2]["ServerPublicKey"]["server_public_key"]
    
    return True

def register_device():
    """Register a device with the API."""
    response = make_request(
        "POST",
        f"device-server",
        {
            "description": BUNQ_DEVICE_NAME,
            "secret": BUNQ_API_KEY
        }
    )
    return True

def create_session():
    """Create a new session."""
    response = make_request(
        "POST",
        "session-server",
        {"secret": BUNQ_API_KEY}
    )
    
    # Store session data
    SESSION["token"] = response["Response"][1]["Token"]["token"]
    
    # Find user ID
    for item in response["Response"]:
        if "UserPerson" in item:
            SESSION["user_id"] = item["UserPerson"]["id"]
            break
        elif "UserCompany" in item:
            SESSION["user_id"] = item["UserCompany"]["id"]
            break
    
    return True

def initialize_bunq_api():
    """Initialize the Bunq API."""
    if not BUNQ_API_KEY:
        raise ValueError("BUNQ_API_KEY environment variable is required")
    
    try:
        # Create installation
        initialize_installation()
        
        # Register device
        register_device()
        
        # Create session
        create_session()
        
        return True
    except Exception as e:
        print(f"Error initializing Bunq API: {e}")
        return False

# Initialize Bunq API on server startup
@mcp.lifespan
async def startup():
    """Initialize Bunq API on server startup."""
    success = initialize_bunq_api()
    if not success:
        print("Failed to initialize Bunq API. Please check your API key and environment settings.")
    else:
        print("Bunq API initialized successfully.")
    yield

# Helper functions for formatting data
def format_monetary_account(account):
    """Format a monetary account object into a readable dictionary."""
    return {
        "id": account["id"],
        "description": account["description"],
        "balance": {
            "value": account["balance"]["value"],
            "currency": account["balance"]["currency"]
        },
        "alias": [
            {"type": alias["type"], "value": alias["value"]}
            for alias in account["alias"]
        ],
        "status": account["status"],
        "created": account["created"]
    }

def format_payment(payment):
    """Format a payment object into a readable dictionary."""
    return {
        "id": payment["id"],
        "amount": {
            "value": payment["amount"]["value"],
            "currency": payment["amount"]["currency"]
        },
        "counterparty_alias": {
            "name": payment["counterparty_alias"]["display_name"],
            "iban": payment["counterparty_alias"].get("iban", "N/A"),
        },
        "description": payment["description"],
        "created": payment["created"]
    }

# MCP Tools for Bunq API
@mcp.tool()
async def get_accounts() -> str:
    """Get all monetary accounts for the authenticated user."""
    try:
        response = make_request(
            "GET",
            f"user/{SESSION['user_id']}/monetary-account"
        )
        
        accounts = []
        for item in response["Response"]:
            if "MonetaryAccountBank" in item:
                accounts.append(format_monetary_account(item["MonetaryAccountBank"]))
            elif "MonetaryAccountJoint" in item:
                accounts.append(format_monetary_account(item["MonetaryAccountJoint"]))
            elif "MonetaryAccountSavings" in item:
                accounts.append(format_monetary_account(item["MonetaryAccountSavings"]))
        
        return json.dumps(accounts, indent=2)
    except Exception as e:
        return f"Error retrieving accounts: {str(e)}"

@mcp.tool()
async def get_account_balance(account_id: str) -> str:
    """Get the balance of a specific monetary account.
    
    Args:
        account_id: The ID of the monetary account
    """
    try:
        response = make_request(
            "GET",
            f"user/{SESSION['user_id']}/monetary-account/{account_id}"
        )
        
        account = None
        for item in response["Response"]:
            if "MonetaryAccountBank" in item:
                account = item["MonetaryAccountBank"]
                break
            elif "MonetaryAccountJoint" in item:
                account = item["MonetaryAccountJoint"]
                break
            elif "MonetaryAccountSavings" in item:
                account = item["MonetaryAccountSavings"]
                break
        
        if account:
            balance = account["balance"]
            return f"Balance: {balance['value']} {balance['currency']}"
        else:
            return "Account not found"
    except Exception as e:
        return f"Error retrieving account balance: {str(e)}"

@mcp.tool()
async def get_transactions(account_id: str, limit: int = 10) -> str:
    """Get recent transactions for a specific monetary account.
    
    Args:
        account_id: The ID of the monetary account
        limit: Maximum number of transactions to return (default: 10)
    """
    try:
        response = make_request(
            "GET",
            f"user/{SESSION['user_id']}/monetary-account/{account_id}/payment",
            params={"count": limit}
        )
        
        payments = []
        for item in response["Response"]:
            if "Payment" in item:
                payments.append(format_payment(item["Payment"]))
        
        return json.dumps(payments, indent=2)
    except Exception as e:
        return f"Error retrieving transactions: {str(e)}"

@mcp.tool()
async def make_payment(
    account_id: str, 
    recipient_name: str,
    recipient_iban: str, 
    amount: float, 
    currency: str = "EUR", 
    description: str = ""
) -> str:
    """Make a payment from a specific monetary account.
    
    Args:
        account_id: The ID of the monetary account to pay from
        recipient_name: Name of the recipient
        recipient_iban: IBAN of the recipient
        amount: Amount to transfer (positive number)
        currency: Currency code (default: EUR)
        description: Payment description
    """
    try:
        # Validate amount
        if amount <= 0:
            return "Error: Amount must be positive"
        
        # Create payment
        response = make_request(
            "POST",
            f"user/{SESSION['user_id']}/monetary-account/{account_id}/payment",
            {
                "amount": {
                    "value": str(amount),
                    "currency": currency
                },
                "counterparty_alias": {
                    "type": "IBAN",
                    "value": recipient_iban,
                    "name": recipient_name
                },
                "description": description
            }
        )
        
        payment_id = None
        for item in response["Response"]:
            if "Id" in item:
                payment_id = item["Id"]["id"]
                break
        
        return f"Payment created successfully. Payment ID: {payment_id}"
    except Exception as e:
        return f"Error making payment: {str(e)}"

@mcp.tool()
async def request_payment(
    account_id: str,
    counterparty_name: str,
    counterparty_email: str,
    amount: float,
    currency: str = "EUR",
    description: str = ""
) -> str:
    """Request a payment from someone.
    
    Args:
        account_id: The ID of the monetary account to request payment to
        counterparty_name: Name of the person you're requesting from
        counterparty_email: Email of the person you're requesting from
        amount: Amount to request (positive number)
        currency: Currency code (default: EUR)
        description: Request description
    """
    try:
        # Validate amount
        if amount <= 0:
            return "Error: Amount must be positive"
        
        # Create payment request
        response = make_request(
            "POST",
            f"user/{SESSION['user_id']}/monetary-account/{account_id}/request-inquiry",
            {
                "amount_inquired": {
                    "value": str(amount),
                    "currency": currency
                },
                "counterparty_alias": {
                    "type": "EMAIL",
                    "value": counterparty_email,
                    "name": counterparty_name
                },
                "description": description,
                "allow_bunqme": True
            }
        )
        
        request_id = None
        for item in response["Response"]:
            if "Id" in item:
                request_id = item["Id"]["id"]
                break
        
        return f"Payment request created successfully. Request ID: {request_id}"
    except Exception as e:
        return f"Error requesting payment: {str(e)}"

@mcp.tool()
async def get_cards() -> str:
    """Get all cards for the authenticated user."""
    try:
        response = make_request(
            "GET",
            f"user/{SESSION['user_id']}/card"
        )
        
        cards = []
        for item in response["Response"]:
            if "Card" in item:
                card = item["Card"]
                cards.append({
                    "id": card["id"],
                    "type": card["type"],
                    "status": card["status"],
                    "expiry_date": card.get("expiry_date", "N/A"),
                    "name_on_card": card.get("name_on_card", "N/A"),
                    "primary_account_id": card.get("primary_account_id", "N/A")
                })
        
        return json.dumps(cards, indent=2)
    except Exception as e:
        return f"Error retrieving cards: {str(e)}"

@mcp.tool()
async def block_card(card_id: str) -> str:
    """Block a specific card.
    
    Args:
        card_id: The ID of the card to block
    """
    try:
        make_request(
            "PUT",
            f"user/{SESSION['user_id']}/card/{card_id}",
            {
                "status": "BLOCKED"
            }
        )
        return f"Card {card_id} has been blocked successfully."
    except Exception as e:
        return f"Error blocking card: {str(e)}"

@mcp.tool()
async def unblock_card(card_id: str) -> str:
    """Unblock a specific card.
    
    Args:
        card_id: The ID of the card to unblock
    """
    try:
        make_request(
            "PUT",
            f"user/{SESSION['user_id']}/card/{card_id}",
            {
                "status": "ACTIVE"
            }
        )
        return f"Card {card_id} has been unblocked successfully."
    except Exception as e:
        return f"Error unblocking card: {str(e)}"

# Add resource for account overview
@mcp.resource("bunq://accounts")
async def get_accounts_resource() -> str:
    """Get an overview of all accounts as a resource."""
    try:
        response = make_request(
            "GET",
            f"user/{SESSION['user_id']}/monetary-account"
        )
        
        accounts = []
        for item in response["Response"]:
            if "MonetaryAccountBank" in item:
                accounts.append(format_monetary_account(item["MonetaryAccountBank"]))
            elif "MonetaryAccountJoint" in item:
                accounts.append(format_monetary_account(item["MonetaryAccountJoint"]))
            elif "MonetaryAccountSavings" in item:
                accounts.append(format_monetary_account(item["MonetaryAccountSavings"]))
        
        return json.dumps(accounts, indent=2)
    except Exception as e:
        return f"Error retrieving accounts: {str(e)}"

# Add resource for specific account details
@mcp.resource("bunq://accounts/{account_id}")
async def get_account_resource(account_id: str) -> str:
    """Get details for a specific account as a resource."""
    try:
        response = make_request(
            "GET",
            f"user/{SESSION['user_id']}/monetary-account/{account_id}"
        )
        
        account = None
        for item in response["Response"]:
            if "MonetaryAccountBank" in item:
                account = format_monetary_account(item["MonetaryAccountBank"])
                break
            elif "MonetaryAccountJoint" in item:
                account = format_monetary_account(item["MonetaryAccountJoint"])
                break
            elif "MonetaryAccountSavings" in item:
                account = format_monetary_account(item["MonetaryAccountSavings"])
                break
        
        if account:
            return json.dumps(account, indent=2)
        else:
            return json.dumps({"error": "Account not found"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

# Add prompt for payment flow
@mcp.prompt()
def payment_prompt(recipient_name: str, recipient_iban: str, amount: float) -> str:
    """Create a prompt for confirming a payment."""
    return f"""
I'd like to make a payment of {amount} EUR to {recipient_name} (IBAN: {recipient_iban}).
Please help me complete this transaction and confirm when it's done.
"""

# Main execution
if __name__ == "__main__":
    mcp.run() 