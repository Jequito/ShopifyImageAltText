#!/usr/bin/env python
"""
Shopify Connection Test Utility

A standalone script to test your Shopify API connection outside of the Streamlit app.
This can help troubleshoot connection issues before running the main application.

Usage:
    python connection_test.py your-store.myshopify.com your-access-token -v
"""

import argparse
import json
import requests
import sys

def test_shopify_connection(shop_url, access_token, verbose=False):
    """
    Test connection to a Shopify store using provided credentials
    
    Parameters:
    shop_url (str): Shopify store URL (e.g., your-store.myshopify.com)
    access_token (str): Shopify Admin API access token
    verbose (bool): Whether to print detailed debug information
    
    Returns:
    tuple: (success, result) where success is a boolean and result is dict or error string
    """
    # Format the shop URL
    formatted_shop_url = shop_url.strip()
    if formatted_shop_url.startswith("https://"):
        formatted_shop_url = formatted_shop_url.replace("https://", "")
    if formatted_shop_url.startswith("http://"):
        formatted_shop_url = formatted_shop_url.replace("http://", "")
    if not ".myshopify.com" in formatted_shop_url:
        formatted_shop_url = f"{formatted_shop_url}.myshopify.com"
    
    url = f"https://{formatted_shop_url}/admin/api/2023-10/shop.json"
    
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    if verbose:
        print(f"Making request to: {url}")
        print(f"Using headers: X-Shopify-Access-Token: {access_token[:6]}...{access_token[-4:] if len(access_token) > 10 else '****'}")
    
    try:
        response = requests.get(url, headers=headers)
        
        if verbose:
            print(f"Response status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
        
        if response.status_code >= 400:
            error_detail = "No detailed error information available"
            try:
                error_json = response.json()
                error_detail = json.dumps(error_json, indent=2)
            except:
                if response.text:
                    error_detail = response.text[:500]
            
            return False, f"API Error ({response.status_code}):\n{error_detail}"
        
        response.raise_for_status()
        shop_data = response.json()
        
        if verbose:
            print(f"Response data: {json.dumps(shop_data, indent=2)}")
        
        return True, shop_data
        
    except requests.exceptions.HTTPError as http_err:
        return False, f"HTTP Error: {http_err}"
    except requests.exceptions.ConnectionError as conn_err:
        return False, f"Connection Error: {conn_err}"
    except requests.exceptions.Timeout as timeout_err:
        return False, f"Timeout Error: {timeout_err}"
    except requests.exceptions.RequestException as req_err:
        return False, f"Request Error: {req_err}"
    except Exception as err:
        return False, f"Error: {err}"

def main():
    parser = argparse.ArgumentParser(description="Test Shopify API Connection")
    parser.add_argument("shop_url", help="Shopify store URL (e.g., your-store.myshopify.com)")
    parser.add_argument("access_token", help="Shopify Admin API access token")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    print(f"Testing connection to Shopify store: {args.shop_url}")
    success, result = test_shopify_connection(args.shop_url, args.access_token, args.verbose)
    
    if success:
        print(f"\n✅ Successfully connected to {result['shop']['name']}")
        print(f"\nShop details:")
        print(f"  - Domain: {result['shop']['domain']}")
        print(f"  - Email: {result['shop']['email']}")
        print(f"  - Country: {result['shop']['country_name']}")
        print(f"  - Plan: {result['shop']['plan_name']}")
        return 0
    else:
        print(f"\n❌ Connection failed: {result}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
