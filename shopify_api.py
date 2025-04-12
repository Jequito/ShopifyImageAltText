import streamlit as st
import requests
import json
from typing import Dict, List, Any

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
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=15)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=15)
        
        # Log the response status code
        st.info(f"Response status code: {response.status_code}")
        
        # Try to get detailed error info if available
        if response.status_code >= 400:
            error_detail = "No detailed error information available"
            try:
                error_json = response.json()
                error_detail = json.dumps(error_json, indent=2)
            except:
                if response.text:
                    error_detail = response.text[:500]  # Limit text length
            
            st.error(f"API Error ({response.status_code}):\n{error_detail}")
            return {}
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
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
                  sku
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
            skus = []
            if "variants" in product and "edges" in product["variants"]:
                for var_edge in product["variants"]["edges"]:
                    variant_node = var_edge["node"]
                    variants.append({
                        "id": variant_node["id"],
                        "title": variant_node["title"],
                        "price": variant_node["price"],
                        "sku": variant_node.get("sku", "")
                    })
                    if variant_node.get("sku"):
                        skus.append(variant_node["sku"])
            
            product_data = {
                "id": product["id"],
                "title": product["title"],
                "description": product["description"] or "",
                "vendor": product["vendor"],
                "type": product["productType"],
                "tags": product["tags"],
                "variants": variants,
                "images": images,
                "skus": skus,
                "store": st.session_state.get("shop_name", "")
            }
            
            products.append(product_data)
    
    return products

def fetch_selected_products(selected_ids=None) -> List[Dict]:
    """Fetch specific products from Shopify using GraphQL API
    
    Args:
        selected_ids: Optional list of product IDs to fetch. If None, fetches all products.
    """
    if selected_ids:
        # Build a GraphQL query with product ID filter
        id_list = ", ".join([f'"{id}"' for id in selected_ids])
        query = f"""
        {{
          products(first: 50, query: "id:({id_list})") {{
            edges {{
              node {{
                id
                title
                description
                vendor
                productType
                tags
                images(first: 20) {{
                  edges {{
                    node {{
                      id
                      url
                      altText
                    }}
                  }}
                }}
                variants(first: 10) {{
                  edges {{
                    node {{
                      id
                      title
                      price
                      sku
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """
    else:
        # Fetch all products (original query)
        return fetch_products()
    
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
            skus = []
            if "variants" in product and "edges" in product["variants"]:
                for var_edge in product["variants"]["edges"]:
                    variant_node = var_edge["node"]
                    variants.append({
                        "id": variant_node["id"],
                        "title": variant_node["title"],
                        "price": variant_node["price"],
                        "sku": variant_node.get("sku", "")
                    })
                    if variant_node.get("sku"):
                        skus.append(variant_node["sku"])
            
            product_data = {
                "id": product["id"],
                "title": product["title"],
                "description": product["description"] or "",
                "vendor": product["vendor"],
                "type": product["productType"],
                "tags": product["tags"],
                "variants": variants,
                "images": images,
                "skus": skus,
                "store": st.session_state.get("shop_name", "")
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
