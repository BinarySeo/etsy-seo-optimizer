"""
my_shop.py
----------
Fetches my own Etsy shop listings and tags via OAuth.
This gives us real tag data for SEO gap analysis.

Usage:
    python -m scraper.my_shop
"""

import os
import sys
import requests
import webbrowser
import hashlib
import base64
import secrets
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY       = os.getenv("ETSY_API_KEY")
SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
REDIRECT_URI  = "https://www.etsy.com/"
BASE_URL      = "https://api.etsy.com/v3/application"
SCOPES = "listings_r transactions_r shops_r"


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def generate_pkce() -> tuple:
    """
    Generate a PKCE code_verifier and code_challenge pair.
    Required by Etsy OAuth2 for secure authorization.
    """
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode()
    return code_verifier, code_challenge


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------

def get_auth_url(code_challenge: str) -> str:
    """Build the Etsy authorization URL."""
    return (
        f"https://www.etsy.com/oauth/connect"
        f"?response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES.replace(' ', '%20')}"
        f"&client_id={API_KEY}"
        f"&state=superstate"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )


def exchange_code(code: str, code_verifier: str) -> dict:
    """Exchange authorization code for access token."""
    url = "https://api.etsy.com/v3/public/oauth/token"
    response = requests.post(url, data={
    "grant_type":    "authorization_code",
    "client_id":     API_KEY,
    "client_secret": SHARED_SECRET,
    "redirect_uri":  REDIRECT_URI,
    "code":          code,
    "code_verifier": code_verifier,
    })
    print(f"[DEBUG] Token exchange status: {response.status_code}")
    print(f"[DEBUG] Token response: {response.text}")
    return response.json()


# ---------------------------------------------------------------------------
# Shop data fetchers
# ---------------------------------------------------------------------------

def get_my_shop_id(access_token: str) -> str:
    user_id = access_token.split(".")[0]
    url = f"{BASE_URL}/users/{user_id}/shops"
    headers = {
        "x-api-key":     f"{API_KEY}:{SHARED_SECRET}",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(url, headers=headers)
    print(f"[DEBUG] Shop URL: {url}")
    print(f"[DEBUG] Shop response status: {response.status_code}")
    print(f"[DEBUG] Shop response: {response.text}")
    data = response.json()
    # Direct object (not array)
    if "shop_id" in data:
        return str(data["shop_id"])
    # Array format fallback
    results = data.get("results", [])
    if results:
        return str(results[0].get("shop_id", ""))
    return ""


def fetch_my_listings(access_token: str, shop_id: str) -> pd.DataFrame:
    """Fetch all active listings from my shop with tags."""
    url = f"{BASE_URL}/shops/{shop_id}/listings/active"
    headers = {
        "x-api-key":     f"{API_KEY}:{SHARED_SECRET}",
        "Authorization": f"Bearer {access_token}",
    }

    all_listings = []
    offset = 0

    while True:
        params = {"limit": 100, "offset": offset}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"[ERROR] {response.status_code}: {response.text}")
            break

        data     = response.json()
        results  = data.get("results", [])

        if not results:
            break

        for item in results:
            all_listings.append({
                "listing_id":   item.get("listing_id", ""),
                "title":        item.get("title", ""),
                "tags":         ", ".join(item.get("tags", [])),
                "num_favorers": item.get("num_favorers", 0),
                "views":        item.get("views", 0),
                "price_usd":    item.get("price", {}).get("amount", 0) / 100 if item.get("price") else 0,
                "url":          item.get("url", ""),
                "fetched_at":   datetime.utcnow().isoformat(),
            })

        offset += len(results)
        if len(results) < 100:
            break

    return pd.DataFrame(all_listings)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("[INFO] Starting Etsy OAuth flow...\n")

    # Generate PKCE pair
    code_verifier, code_challenge = generate_pkce()

    # Step 1 — Open browser for authorization
    auth_url = get_auth_url(code_challenge)
    print("[INFO] Opening browser for authorization...")
    print(f"\nIf browser doesn't open, go to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Step 2 — User pastes the redirect URL
    print("After authorizing, you'll be redirected to etsy.com")
    print("Copy the FULL URL from your browser and paste it here:")
    redirect_url = input("Paste URL: ").strip()

    # Extract code from URL
    if "code=" in redirect_url:
        code = redirect_url.split("code=")[1].split("&")[0]
        print(f"\n[INFO] Got code: {code[:10]}...")
    else:
        print("[ERROR] No code found in URL")
        exit(1)

    # Step 3 — Exchange code for access token
    print("\n[INFO] Exchanging code for access token...")
    token_data = exchange_code(code, code_verifier)
    access_token = token_data.get("access_token", "")

    if not access_token:
        print("[ERROR] Failed to get access token")
        exit(1)

    print(f"\n[INFO] Got access token ✅")

    # Step 4 — Get shop ID
    print("\n[INFO] Fetching your shop...")
    shop_id = get_my_shop_id(access_token)

    if not shop_id:
        print("[ERROR] Could not find shop ID")
        exit(1)

    print(f"[INFO] Shop ID: {shop_id}")

    # Step 5 — Fetch listings
    print("\n[INFO] Fetching your listings...")
    df = fetch_my_listings(access_token, shop_id)

    if df.empty:
        print("[WARN] No listings found")
    else:
        print(f"\n✅ Found {len(df)} listings\n")
        print(df[["title", "tags", "num_favorers", "views"]].head(10).to_string())

        # Save
        os.makedirs("data/processed", exist_ok=True)
        filepath = f"data/processed/my_shop_listings_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filepath, index=False)
        print(f"\n[SAVED] {filepath}")

    print("\n[DONE]")