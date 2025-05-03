import os
import asyncio
import json
import base64
import uuid
import time
import hmac
import hashlib
import requests
import httpx
import sys
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file."""
    env_path = Path('.') / '.env'
    if env_path.exists():
        print("Loading environment variables from .env file...", file=sys.stderr)
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                os.environ[key] = value
    else:
        print("No .env file found. Please create one with your Bunq API credentials.", file=sys.stderr)

# Load environment variables before importing MCP
load_env()

from mcp.server.fastmcp import FastMCP, Context

# Initialize our MCP server
mcp = FastMCP("Bunq Banking")

# Environment variables for configuration
BUNQ_API_KEY = os.environ.get("BUNQ_API_KEY")
BUNQ_DEVICE_NAME = os.environ.get("BUNQ_DEVICE_NAME", "MCP Server")
BUNQ_ENVIRONMENT = os.environ.get("BUNQ_ENVIRONMENT", "PRODUCTION")  # or "SANDBOX"

# Print configuration (without API key for security)
print(f"Bunq Device Name: {BUNQ_DEVICE_NAME}", file=sys.stderr)
print(f"Bunq Environment: {BUNQ_ENVIRONMENT}", file=sys.stderr)
print(f"API Key: {'Configured' if BUNQ_API_KEY else 'Not configured'}", file=sys.stderr)

# API configuration
API_URL = "https://api.bunq.com" if BUNQ_ENVIRONMENT == "PRODUCTION" else "https://public-api.sandbox.bunq.com"
API_VERSION = "v1"

# Global session data
SESSION = {
    "token": None,
    "server_public_key": None,
    "installation_id": None,
    "installation_token": None,
    "private_key": None,
    "public_key": None,
    "user_id": "1882233",
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
        print("No private key available for signing", file=sys.stderr)
        return headers
    
    # Create the data to sign
    data_to_sign = f"{method} {endpoint}"
    
    # Build list of headers to sign (alphabetical, but **exclude** the signature header itself)
    headers_to_sign: List[str] = []
    for header_name in sorted(headers.keys()):
        lname = header_name.lower()
        if lname.startswith("x-bunq-") and lname != "x-bunq-client-signature":
            headers_to_sign.append(f"{header_name}: {headers[header_name]}")
    
    if headers_to_sign:
        data_to_sign += f"\n{'\n'.join(headers_to_sign)}"
    
    # Add request body if present
    if data:
        data_to_sign += f"\n\n{data}"
    
    print(f"Data to sign: {data_to_sign}", file=sys.stderr)
    
    try:
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
        
        # Encode and attach the signature (✅ what Bunq expects)
        signature_base64 = base64.b64encode(signature).decode("utf-8")
        headers["X-Bunq-Client-Signature"] = signature_base64
        print(
            f"Request signed successfully. Signature: {signature_base64[:20]}...",
            file=sys.stderr,
        )
        
        return headers
    except Exception as e:
        print(f"Error signing request: {e}", file=sys.stderr)
        return headers

def make_request(method, endpoint, data=None, params=None, auth=True):
    """Make a request to the Bunq API."""
    url = f"{API_URL}/{API_VERSION}/{endpoint}"
    
    # Get headers from environment variables if available
    request_id = os.environ.get("X-Bunq-Client-Request-Id", str(uuid.uuid4()))
    client_auth = os.environ.get("X-Bunq-Client-Authentication")
    client_signature = os.environ.get("X-Bunq-Client-Signature")
    
    headers: Dict[str, str] = {
        "Cache-Control": "no-cache",
        "User-Agent": "Bunq MCP Server",
        "X-Bunq-Client-Request-Id": request_id,
        "X-Bunq-Geolocation": "0 0 0 0 000",
        "X-Bunq-Language": "en_US",
        "X-Bunq-Region": "nl_NL",
    }
    
    # Add authentication headers if required
    if auth:
        if client_auth:
            # Use authentication from environment
            headers["X-Bunq-Client-Authentication"] = client_auth
            print("Using X-Bunq-Client-Authentication from environment", file=sys.stderr)
        elif SESSION["token"]:
            headers["X-Bunq-Client-Authentication"] = SESSION["token"]
        elif endpoint != "installation" and SESSION.get("installation_token"):
            headers["X-Bunq-Client-Authentication"] = SESSION["installation_token"]

    # Convert data to JSON if present
    json_data = None
    if data:
        json_data = json.dumps(data)
        headers["Content-Type"] = "application/json"
    
    # Add signature if available in environment, otherwise generate it
    if client_signature and auth and endpoint != "installation":
        headers["X-Bunq-Client-Signature"] = client_signature
        print("Using X-Bunq-Client-Signature from environment " + client_signature , file=sys.stderr)
    elif SESSION["private_key"] and endpoint != "installation":
        print(f"Signing request for {endpoint}", file=sys.stderr)
        headers = sign_request(method, f"/{API_VERSION}/{endpoint}", headers, json_data)
    else:
        print(f"Not signing request for {endpoint}", file=sys.stderr)
    
    # Print request details for debugging
    print(f"Making {method} request to {url}", file=sys.stderr)
    #print(f"Headers: {json.dumps({k: v for k, v in headers.items() if not k.lower().startswith('x-bunq-client-signature')}, indent=2)}", file=sys.stderr)
    if data:
        print(f"Data: {json.dumps(data, indent=2)}", file=sys.stderr)
    
    # Check if signature is present when it should be
    if endpoint != "installation" and "X-Bunq-Client-Signature" not in headers:
        print("WARNING: Request is missing X-Bunq-Client-Signature header!", file=sys.stderr)
    
    print(headers)
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
            print(f"Error response: {json.dumps(error_data, indent=2)}", file=sys.stderr)
            if "Error" in error_data:
                error_message = f"API Error: {error_data['Error'][0]['error_description']}"
        except:
            print(f"Raw error response: {response.text}", file=sys.stderr)
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
    
    # Print response for debugging
    print("Installation response:", json.dumps(response, indent=2), file=sys.stderr)
    
    # Store installation data - more robust parsing
    installation_id = None
    server_public_key = None
    installation_token = None
    
    for item in response.get("Response", []):
        if "Id" in item:
            installation_id = item["Id"].get("id")
        elif "ServerPublicKey" in item:
            server_public_key = item["ServerPublicKey"].get("server_public_key")
        elif "Token" in item:
            installation_token = item["Token"].get("token")
    
    if not installation_id or not server_public_key or not installation_token:
        print("Failed to extract installation data from response", file=sys.stderr)
        return False
    
    SESSION["installation_id"] = installation_id
    SESSION["server_public_key"] = server_public_key
    SESSION["installation_token"] = installation_token
    
    return True

def register_device():
    """Register a device with the API."""
    try:
        # Prepare the request data
        data = {
            "description": BUNQ_DEVICE_NAME,
            "secret": BUNQ_API_KEY,
            "permitted_ips": ["*"]  # Allow all IPs
        }
        json_data = json.dumps(data)
        
        # Prepare headers
        headers = {
            "Cache-Control": "no-cache",
            "User-Agent": "Bunq MCP Server",
            "X-Bunq-Client-Request-Id": os.environ.get("X-Bunq-Client-Request-Id", str(uuid.uuid4())),
            "X-Bunq-Geolocation": "0 0 0 0 000",
            "X-Bunq-Language": "en_US",
            "X-Bunq-Region": "nl_NL",
            "Content-Type": "application/json"
        }
        
        # Add authentication from environment or session
        if os.environ.get("X-Bunq-Client-Authentication"):
            headers["X-Bunq-Client-Authentication"] = os.environ.get("X-Bunq-Client-Authentication")
            print("Using X-Bunq-Client-Authentication from environment", file=sys.stderr)
        elif SESSION.get("installation_token"):
            headers["X-Bunq-Client-Authentication"] = SESSION["installation_token"]
        else:
            print("No authentication token available", file=sys.stderr)
            return False
        
        # Add signature from environment or generate it
        if os.environ.get("X-Bunq-Client-Signature"):
            headers["X-Bunq-Client-Signature"] = os.environ.get("X-Bunq-Client-Signature")
            print("Using X-Bunq-Client-Signature from environment", file=sys.stderr)
        else:
            # Sign the request
            endpoint = f"/{API_VERSION}/device-server"
            headers = sign_request("POST", endpoint, headers, json_data)
        
        # Verify signature is present
        if "X-Bunq-Client-Signature" not in headers:
            print("ERROR: Signature is missing from headers!", file=sys.stderr)
            return False
            
        print(f"Device registration request headers: {json.dumps({k: v for k, v in headers.items() if not k.lower().startswith('x-bunq-client-signature')}, indent=2)}", file=sys.stderr)
        print(f"Device registration request data: {json_data}", file=sys.stderr)
        
        # Make the request
        url = f"{API_URL}/{API_VERSION}/device-server"
        response = requests.post(
            url=url,
            headers=headers,
            data=json_data
        )
        
        # Check for errors
        if response.status_code >= 400:
            error_message = f"API Error: {response.status_code}"
            try:
                error_data = response.json()
                print(f"Error response: {json.dumps(error_data, indent=2)}", file=sys.stderr)
                if "Error" in error_data:
                    error_message = f"API Error: {error_data['Error'][0]['error_description']}"
            except:
                print(f"Raw error response: {response.text}", file=sys.stderr)
            raise Exception(error_message)
        
        # Parse response
        response_data = response.json()
        print("Device registration response:", json.dumps(response_data, indent=2), file=sys.stderr)
        
        return True
    except Exception as e:
        print(f"Error registering device: {e}", file=sys.stderr)
        return False

def create_session():
    """Create a new session."""
    try:
        # Prepare the request data
        data = {"secret": BUNQ_API_KEY}
        json_data = json.dumps(data)
        
        # Prepare headers
        headers = {
            "Cache-Control": "no-cache",
            "User-Agent": "Bunq MCP Server",
            "X-Bunq-Client-Request-Id": str(uuid.uuid4()),
            "X-Bunq-Geolocation": "0 0 0 0 000",
            "X-Bunq-Language": "en_US",
            "X-Bunq-Region": "nl_NL",
            "Content-Type": "application/json"
        }
        
        # Add authentication from environment or session
        if os.environ.get("X-Bunq-Client-Authentication"):
            headers["X-Bunq-Client-Authentication"] = os.environ.get("X-Bunq-Client-Authentication")
            print("Using X-Bunq-Client-Authentication from environment", file=sys.stderr)
        elif SESSION.get("installation_token"):
            headers["X-Bunq-Client-Authentication"] = SESSION["installation_token"]
        else:
            print("No authentication token available", file=sys.stderr)
            return False
        
        # Add signature from environment or generate it
        if os.environ.get("X-Bunq-Client-Signature"):
            headers["X-Bunq-Client-Signature"] = os.environ.get("X-Bunq-Client-Signature")
            print("Using X-Bunq-Client-Signature from environment", file=sys.stderr)
        else:
            # Sign the request
            endpoint = f"/{API_VERSION}/session-server"
            headers = sign_request("POST", endpoint, headers, json_data)
        
        # Verify signature is present
        if "X-Bunq-Client-Signature" not in headers:
            print("ERROR: Signature is missing from headers!", file=sys.stderr)
            return False
            
        print(headers)
       # print(f"Session request headers: {json.dumps({k: v for k, v in headers.items() if not k.lower().startswith('x-bunq-client-signature')}, indent=2)}")
        print(f"Session request data: {json_data}", file=sys.stderr)
        
        # Make the request
        url = f"{API_URL}/{API_VERSION}/session-server"
        response = requests.post(
            url=url,
            headers=headers,
            data=json_data
        )
        
        # Check for errors
        if response.status_code >= 400:
            error_message = f"API Error: {response.status_code}"
            try:
                error_data = response.json()
                print(f"Error response: {json.dumps(error_data, indent=2)}", file=sys.stderr)
                if "Error" in error_data:
                    error_message = f"API Error: {error_data['Error'][0]['error_description']}"
            except:
                print(f"Raw error response: {response.text}", file=sys.stderr)
            raise Exception(error_message)
        
        # Parse response
        response_data = response.json()
        print("Session creation response:", json.dumps(response_data, indent=2), file=sys.stderr)
        
        # Store session data
        session_token = None
        user_id = None
        
        for item in response_data.get("Response", []):
            if "Token" in item:
                session_token = item["Token"].get("token")
            elif "UserPerson" in item:
                user_id = item["UserPerson"].get("id")
            elif "UserCompany" in item:
                user_id = item["UserCompany"].get("id")
        
        if not session_token or not user_id:
            print("Failed to extract session data from response", file=sys.stderr)
            return False
        
        SESSION["token"] = session_token
        SESSION["user_id"] = user_id
        
        return True
    except Exception as e:
        print(f"Error creating session: {e}", file=sys.stderr)
        return False

def initialize_bunq_api():
    """Initialize the Bunq API."""
    global BUNQ_API_KEY
    
    try:
        # For sandbox, always create a new user first
        if BUNQ_ENVIRONMENT == "SANDBOX":
            print("Creating a new sandbox user...", file=sys.stderr)
            response = requests.post(
                f"{API_URL}/{API_VERSION}/sandbox-user-person",
                headers={
                    "Cache-Control": "no-cache",
                    "User-Agent": "Bunq MCP Server",
                    "X-Bunq-Client-Request-Id": str(uuid.uuid4()),
                }
            )
            
            if response.status_code >= 400:
                print(f"Error creating sandbox user: {response.status_code}", file=sys.stderr)
                return False
                
            data = response.json()
            print("Sandbox user creation response:", json.dumps(data, indent=2), file=sys.stderr)
            
            # Extract API key
            api_key = None
            for item in data.get("Response", []):
                if "ApiKey" in item:
                    api_key = item["ApiKey"].get("api_key")
            
            if not api_key:
                print("Failed to extract API key from response", file=sys.stderr)
                return False
                
            # Update the API key
            BUNQ_API_KEY = api_key
            os.environ["BUNQ_API_KEY"] = api_key
            
            # Update the .env file
            env_path = Path('.') / '.env'
            if env_path.exists():
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                
                with open(env_path, 'w') as f:
                    for line in lines:
                        if line.startswith('BUNQ_API_KEY='):
                            f.write(f'BUNQ_API_KEY={api_key}\n')
                        else:
                            f.write(line)
                print(f"Updated .env file with new API key: {api_key[:5]}...{api_key[-5:]}", file=sys.stderr)
        
        # Create installation
        if not initialize_installation():
            return False
        
        # Register device
        if not register_device():
            return False
        
        # Create session
        if not create_session():
            return False
        
        return True
    except Exception as e:
        print(f"Error initializing Bunq API: {e}", file=sys.stderr)
        return False

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

@mcp.tool()
async def get_user_info() -> str:
    """Get information about the authenticated user."""
    try:
        if not SESSION["user_id"]:
            return "Not authenticated. Please initialize the API first."
            
        response = make_request(
            "GET",
            f"user/{SESSION['user_id']}"
        )
        
        user_info = None
        for item in response["Response"]:
            if "UserPerson" in item:
                user_info = item["UserPerson"]
                break
            elif "UserCompany" in item:
                user_info = item["UserCompany"]
                break
        
        if user_info:
            # Format the user info to make it more readable
            formatted_info = {
                "id": user_info["id"],
                "created": user_info["created"],
                "updated": user_info["updated"],
                "name": user_info.get("display_name", "N/A"),
                "public_nick_name": user_info.get("public_nick_name", "N/A"),
                "alias": [
                    {"type": alias["type"], "value": alias["value"]}
                    for alias in user_info.get("alias", [])
                ]
            }
            return json.dumps(formatted_info, indent=2)
        else:
            return "User information not found"
    except Exception as e:
        return f"Error retrieving user information: {str(e)}"

# ----------------------------------------------------------------------
# Realistic sample-data tools for user profile, goals, risk, etc.
# ----------------------------------------------------------------------
@mcp.tool()
async def personal_information() -> str:
    """Return realistic personal information."""
    data = {
        "age": 34,
        "marital_status": "Married",
        "dependents": [
            {"age": 8},
            {"age": 5}
        ],
        "employment_status": "Employed",
        "health_status": "Good"
    }
    return json.dumps(data, indent=2)

@mcp.tool()
async def income_expenses() -> str:
    """Return realistic income and expense details."""
    data = {
        "primary_income": {"type": "Salary", "amount": 5500},
        "secondary_income": [
            {"type": "Rental income", "amount": 1200},
            {"type": "Dividends", "amount": 150}
        ],
        "monthly_expenses": {
            "rent": 1500,
            "utilities": 200,
            "groceries": 400,
            "transport": 150,
            "entertainment": 250
        },
        "debt_obligations": [
            {"type": "Mortgage", "monthly_payment": 1200},
            {"type": "Credit Card", "monthly_payment": 100}
        ]
    }
    return json.dumps(data, indent=2)

@mcp.tool()
async def assets_liabilities() -> str:
    """Return realistic assets and liabilities."""
    data = {
        "bank_balances": {"checking": 3200.75, "savings": 10450.00},
        "investments": [
            {"type": "Stocks", "value": 15000},
            {"type": "Bonds", "value": 5000},
            {"type": "Mutual Funds", "value": 8000}
        ],
        "real_estate": [
            {"address": "123 Main St", "value": 250000},
            {"address": "456 Elm St", "value": 175000}
        ],
        "business_ownership": [
            {"name": "Acme Corp", "ownership_percent": 25, "value": 50000}
        ],
        "retirement_accounts": [
            {"type": "401(k)", "value": 35000},
            {"type": "IRA", "value": 15000}
        ],
        "insurance_policies": [
            {"type": "Life", "coverage": 200000},
            {"type": "Health", "status": "Active"}
        ],
        "liabilities": [
            {"type": "Personal Loan", "balance": 5000},
            {"type": "Credit Card", "balance": 1200}
        ]
    }
    return json.dumps(data, indent=2)

@mcp.tool()
async def financial_goals() -> str:
    """Return realistic financial goals."""
    data = {
        "short_term": [
            {"goal": "Emergency fund", "target_amount": 10000, "horizon_months": 6},
            {"goal": "Vacation",       "target_amount": 3000,  "horizon_months": 12}
        ],
        "medium_term": [
            {"goal": "Home down payment", "target_amount": 30000, "horizon_months": 60},
            {"goal": "Start a business",  "target_amount": 20000, "horizon_months": 48}
        ],
        "long_term": [
            {"goal": "Retirement",          "target_amount": 500000, "horizon_years": 25},
            {"goal": "Children's education", "target_amount": 100000, "horizon_years": 15}
        ]
    }
    return json.dumps(data, indent=2)

@mcp.tool()
async def risk_profile() -> str:
    """Return realistic risk profile."""
    data = {
        "risk_tolerance": "Moderate",
        "investment_experience": "5 years",
        "reaction_to_volatility": "Stay invested during drops",
        "liquidity_needs": "Low"
    }
    return json.dumps(data, indent=2)

@mcp.tool()
async def tax_situation() -> str:
    """Return realistic tax situation."""
    data = {
        "tax_bracket": "22%",
        "filing_status": "Married Filing Jointly",
        "capital_gains": {"long_term": 5000, "short_term": 1200},
        "tax_advantaged_accounts": ["401(k)", "Roth IRA"]
    }
    return json.dumps(data, indent=2)

@mcp.tool()
async def legal_estate_planning() -> str:
    """Return realistic legal & estate planning data."""
    data = {
        "wills_and_trusts": ["Basic Will", "Revocable Trust"],
        "power_of_attorney": True,
        "beneficiaries": [
            {"account": "401(k)",         "beneficiary": "Spouse"},
            {"account": "Life Insurance", "beneficiary": "Children"}
        ],
        "estate_goals": "Minimize estate tax and provide for family"
    }
    return json.dumps(data, indent=2)

@mcp.tool()
async def preferences_values() -> str:
    """Return realistic preferences & values."""
    data = {
        "ethical_investing": "ESG",
        "cultural_considerations": "Halal-compliant investments",
        "management_style": "Passive",
        "values": ["Environmental sustainability", "Social responsibility"]
    }
    return json.dumps(data, indent=2)

# ----------------------------------------------------------------------
# 5-Year Financial Statement Tool
# ----------------------------------------------------------------------
@mcp.tool()
async def financial_statement_last_5_years() -> str:
    """
    Return a realistic financial statement for the last 5 years,
    with monthly recurring expenses & salary, plus yearly credits
    (bonus, tax refund) in EUR for an upper-middle-class Dutch household.
    """
    statements: Dict[str, Any] = {}

    # Standard monthly expenses (EUR)
    monthly_expenses = {
        "Mortgage": 1200,
        "Utilities": 200,
        "Groceries": 350,
        "Netflix": 12.99,
        "Spotify": 9.99,
        "Gym membership": 35,
        "Mobile phone": 29.99,
        "Insurance": 80,
        "Transport": 100
    }

    # Build one entry per year from 2019–2023
    for year in range(2019, 2024):
        # Simulate a slight annual salary increase
        salary = 5300 + (year - 2019) * 50

        # Simulate yearly one-off credits
        bonus = 7000 + (year - 2019) * 500
        tax_refund = 1500 + (year - 2019) * 200

        statements[str(year)] = {
            "monthly": {
                "income": {"Salary": salary},
                "expenses": monthly_expenses
            },
            "yearly": {
                "Bonus": bonus,
                "Tax refund": tax_refund
            }
        }

    return json.dumps(statements, indent=2)

# ----------------------------------------------------------------------
# Web-search tool
# ----------------------------------------------------------------------
@mcp.tool()
async def search(query: str, max_results: int = 5) -> str:
    """
    Perform a web search via the DuckDuckGo Search API.
    Use this tool to research on items that Financial advisor can use to suggest the user. 
    example comparing better deals on subscription, approximate cost of a wedding in a location, cost of a holiday in a destination etc.
    This tool returns up to `max_results` suggestions—each a dict with
    'title', 'url', and 'summary'—and is ideal for:
      • Retrieving concise facts or definitions
      • Discovering alternative perspectives or solutions
      • Identifying related documentation, articles or examples

    Args:
        query:       The search query string.
        max_results: Maximum number of results to return (default: 5).

    Returns:
        A JSON-formatted string of a list of result objects:
          [
            {"title": "…", "url": "…", "summary": "…"},
            …
          ]
    """
    # Import within function to avoid global import issues
    from duckduckgo_search import DDGS
    import certifi          # only used to show which CA bundle is ignored

    async def _ddgs_search() -> List[Dict[str, str]]:
        """
        Primary search using duckduckgo-search (can raise TLS errors
        behind corporate proxies).  We pass verify=False to skip CA
        validation.
        """
        def _run() -> List[Dict[str, str]]:
            with DDGS(verify=False) as ddgs:        # <-- ignore invalid certs
                raw = list(ddgs.text(query, max_results=max_results))
                return [{"title": hit["title"], "url": hit["href"]} for hit in raw]

        return await asyncio.to_thread(_run)

    async def _json_fallback() -> List[Dict[str, str]]:
        """
        Secondary search via official JSON endpoint.
        """
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            resp = await client.get(
                "https://api.duckduckgo.com",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        hits: List[Dict[str, str]] = []
        for item in data.get("RelatedTopics", []):
            if "Text" in item and "FirstURL" in item:
                hits.append({"title": item["Text"], "url": item["FirstURL"]})
            elif "Topics" in item:
                for sub in item["Topics"]:
                    if "Text" in sub and "FirstURL" in sub:
                        hits.append({"title": sub["Text"], "url": sub["FirstURL"]})
            if len(hits) >= max_results:
                break
        return hits[:max_results]

    try:
        results = await _ddgs_search()
    except Exception as primary_exc:
        print(
            f"Primary DDGS search failed ({primary_exc!s}). "
            f"Trying JSON fallback…",
            file=sys.stderr,
        )
        try:
            results = await _json_fallback()
        except Exception as secondary_exc:
            err = {
                "primary_error": str(primary_exc),
                "fallback_error": str(secondary_exc),
                "note": "Both DDGS & JSON fallback failed.",
            }
            return json.dumps({"error": err}, indent=2)

    return json.dumps(results, indent=2)

# ----------------------------------------------------------------------
# Mortgage account – recent transactions & interest-rate
# ----------------------------------------------------------------------
@mcp.tool()
async def mortgage_account_transactions() -> str:
    """
    Return the most-recent mortgage-payment transactions **and** the
    current interest-rate applied to the loan.  All values are mock
    data (EUR).
    """
    data: Dict[str, Any] = {
        "account_id": "MORT-12345",
        "lender": "ING Hypotheken",
        "current_interest_rate": 2.35,          # % p.a. fixed
        "next_rate_reset": "2030-06-01",
        "currency": "EUR",
        "transactions": [
            {
                "date": "2025-05-01",
                "description": "Monthly mortgage payment",
                "amount": -1_200.00,
                "principal_component": -730.00,
                "interest_component": -470.00,
            },
            {
                "date": "2025-04-01",
                "description": "Monthly mortgage payment",
                "amount": -1_200.00,
                "principal_component": -728.00,
                "interest_component": -472.00,
            },
            {
                "date": "2025-03-01",
                "description": "Monthly mortgage payment",
                "amount": -1_200.00,
                "principal_component": -726.00,
                "interest_component": -474.00,
            },
            {
                "date": "2025-02-01",
                "description": "Monthly mortgage payment",
                "amount": -1_200.00,
                "principal_component": -724.00,
                "interest_component": -476.00,
            },
            {
                "date": "2025-01-01",
                "description": "Monthly mortgage payment",
                "amount": -1_200.00,
                "principal_component": -722.00,
                "interest_component": -478.00,
            },
        ],
    }
    return json.dumps(data, indent=2)

# ----------------------------------------------------------------------
# Investment portfolio – holdings & performance
# ----------------------------------------------------------------------
@mcp.tool()
async def investment_portfolio() -> str:
    """
    Return a snapshot of the user's investment portfolio with current
    market values and performance figures.  (All numbers are mock data,
    currency = EUR.)
    """
    portfolio: Dict[str, Any] = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d"),
        "currency": "EUR",
        "total_value": 125_430.75,
        "ytd_return_pct": 7.2,
        "holdings": [
            {
                "ticker": "VWCE",
                "name": "Vanguard FTSE All-World ETF",
                "units": 320,
                "avg_cost": 95.30,
                "market_price": 103.20,
                "value": 33_024.00,
                "gain_pct": 8.3,
            },
            {
                "ticker": "IUSA",
                "name": "iShares S&P 500 ETF",
                "units": 210,
                "avg_cost": 38.10,
                "market_price": 41.55,
                "value": 8_725.50,
                "gain_pct": 9.0,
            },
            {
                "ticker": "ASML",
                "name": "ASML Holding NV",
                "units": 45,
                "avg_cost": 520.00,
                "market_price": 610.00,
                "value": 27_450.00,
                "gain_pct": 17.3,
            },
            {
                "ticker": "EUNL",
                "name": "iShares Core MSCI World",
                "units": 400,
                "avg_cost": 53.70,
                "market_price": 56.10,
                "value": 22_440.00,
                "gain_pct": 4.5,
            },
            {
                "ticker": "BNQGREEN",
                "name": "Bunq Green Savings",
                "units": None,
                "avg_cost": None,
                "market_price": None,
                "value": 33_791.25,
                "gain_pct": 2.1,
            },
        ],
    }
    return json.dumps(portfolio, indent=2)

# Main execution
if __name__ == "__main__":
    # Initialize Bunq API before starting the server
    success = initialize_bunq_api()
    if not success:
        print("Failed to initialize Bunq API. Please check your API key and environment settings.", file=sys.stderr)
    else:
        print("Bunq API initialized successfully.", file=sys.stderr)
    
    # Run the MCP server
    mcp.run(transport='stdio') 