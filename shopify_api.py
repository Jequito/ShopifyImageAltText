import streamlit as st
import requests
import json
from typing import Dict, List, Any
import traceback

def make_shopify_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    """Make a direct request to the Shopify API"""
    if not hasattr(st.session_state, 'shopify_connected') or not st.session_state.shopify_connected:
        st.error("Shopify not connected")
        return {}
    
    # Format the shop URL correctly
    shop_url = st.session_state.shop_url.strip()
    # Remove https:// if present
    if shop_url.startswith("https://"):
        shop_url = shop_url.replace("https://", "")
    # Ensure .myshopify.com is in the URL
    if not ".myshopify.com" in shop_url:
        shop_url = f"{shop_url}.myshopify.com"
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": st.session_state.access_token,
    }
    
    url = f"https://{shop_url}/admin/api/2023-10{endpoint}"
    
    try:
        st.info(f"Making {method} request to: {url}")
        
        # Add detailed request information (for debugging)
        request_details = {
            "url": url,
            "method": method,
            "headers": {k: (v if k.lower() != "x-shopify-access-token" else f"{v[:6]}...{v[-4:]}" if len(v) > 10 else "****") for k, v in headers.items()},
        }
        if data:
            request_details["data"] = data
        st.session_state.last_request = request_details
        
        # Make the actual request
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=15)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=15)
        
        # Store response details (for debugging)
        response_details = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }
        st.session_state.last_response = response_details
        
        # Log the response status code
        st.info(f"Response status code: {response.status_code}")
        
        # Try to get detailed error info if available
        if response.status_code >= 400:
            error_detail = "No detailed error information available"
            try:
                error_json = response.json()
                error_detail = json.dumps(error_json, indent=2)
                response_details["json"] = error_json
            except:
                if response.text:
                    error_detail = response.text[:500]  # Limit text length
                    response_details["text"] = response.text[:500]
            
            st.error(f"API Error ({response.status_code}):\n{error_detail}")
            return {}
        
        response.raise_for_status()
        json_response = response.json()
        response_details["json"] = json_response
        return json_response
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        traceback_str = traceback.format_exc()
        st.code(traceback_str)
        
        # Store error details
        if not hasattr(st.session_state, 'api_errors'):
            st.session_state.api_errors = []
        
        st.session_state.api_errors.append({
            "error": str(e),
            "traceback": traceback_str,
            "request": request_details if 'request_details' in locals() else None
        })
        
        return {}

def fetch_products() -> List[Dict]:
    """Fetch products from Shopify using GraphQL API"""
    query = """
    {
      products(first: 50) {
        edges {
          node {
            id
            title
            description
            vendor
            productType
            tags
            images(first: 20) {
              edges {
                node {
                  id
                  url
                  altText
                }
              }
            }
            variants(first: 10) {
              edges {
                node {
                  id
                  title
                  price
                }
              }
            }
          }
        }
      }
    }
    """
    
    data = {"query": query}
    result = make_shopify_request("/graphql.json", "POST", data)
    
    products = []
    if result and "data" in result and "products" in result["data"]:
        for edge in result["data"]["products"]["edges"]:
            product = edge["node"]
            
            # Process images
            images = []
            if "images" in product and "edges" in product["images"]:
                for img_edge in product["images"]["edges"]:
                    image_node = img_edge["node"]
                    images.append({
                        "id": image_node["id"],
                        "src": image_node["url"],
                        "alt": image_node["altText"] or "",
                        "applied_template": None
                    })
            
            # Process variants
            variants = []
            if "variants" in product and "edges" in product["variants"]:
                for var_edge in product["variants"]["edges"]:
                    variant_node = var_edge["node"]
                    variants.append({
                        "id": variant_node["id"],
                        "title": variant_node["title"],
                        "price": variant_node["price"]
                    })
            
            product_data = {
                "id": product["id"],
                "title": product["title"],
                "description": product["description"] or "",
                "vendor": product["vendor"],
                "type": product["productType"],
                "tags": product["tags"],
                "variants": variants,
                "images": images
            }
            
            products.append(product_data)
    
    return products

def update_image_alt_text(product_id: str, image_id: str, alt_text: str) -> bool:
    """Update alt text for a specific product image"""
    # Extract the numeric ID from the GraphQL ID string
    image_gid = image_id.split("/")[-1]
    product_gid = product_id.split("/")[-1]
    
    endpoint = f"/products/{product_gid}/images/{image_gid}.json"
    data = {
        "image": {
            "id": image_gid,
            "alt": alt_text
        }
    }
    
    result = make_shopify_request(endpoint, "PUT", data)
    return "image" in result

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
        print(f"Using headers: {headers}")
    
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
