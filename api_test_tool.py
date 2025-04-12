"""
Shopify API Testing Tool - A standalone diagnostic utility

This tool provides a simple way to test different Shopify API endpoints
and see the full request/response cycle for debugging purposes.
"""

import streamlit as st
import requests
import json
import time
import traceback
from typing import Dict, Any

# Set page config
st.set_page_config(
    page_title="Shopify API Test Tool",
    page_icon="🔍",
    layout="wide"
)

# CSS for styling
st.markdown("""
<style>
.success { color: green; font-weight: bold; }
.error { color: red; font-weight: bold; }
.api-box {
    background-color: #f0f2f6;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
}
.response-time {
    font-size: 14px;
    color: #555;
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)

# Helper functions
def make_api_request(url: str, headers: Dict[str, str], method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Make an API request and return detailed results"""
    result = {
        "success": False,
        "status_code": None,
        "headers": {},
        "body": None,
        "error": None,
        "time_taken": 0
    }
    
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=15)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=15)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=15)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        end_time = time.time()
        result["time_taken"] = end_time - start_time
        result["status_code"] = response.status_code
        result["headers"] = dict(response.headers)
        
        # Try to parse JSON response
        try:
            result["body"] = response.json()
        except:
            result["body"] = response.text
        
        result["success"] = 200 <= response.status_code < 300
        
    except Exception as e:
        result["error"] = {
            "message": str(e),
            "traceback": traceback.format_exc()
        }
    
    return result

# App title
st.title("🔍 Shopify API Testing Tool")
st.write("A diagnostic utility for testing and debugging Shopify API connections")

# Sidebar for configuration
with st.sidebar:
    st.header("API Configuration")
    
    shop_url = st.text_input(
        "Shop URL",
        placeholder="your-store.myshopify.com"
    )
    
    # Help text for shop URL format
    st.caption("""
    **Format**: `your-store.myshopify.com` or just `your-store`
    Do not include `https://`
    """)
    
    access_token = st.text_input(
        "Access Token",
        placeholder="shpat_xxxxxxxxxxxxxxxxxxxxx", 
        type="password"
    )
    
    # Help text for access token
    st.caption("""
    **Format**: Should start with `shpat_` (private app) or `shpca_` (custom app)
    """)
    
    # API Version selection
    api_version = st.selectbox(
        "API Version",
        options=["2023-10", "2023-07", "2023-04", "2023-01", "2022-10"],
        index=0
    )
    
    # Method selection
    method = st.selectbox(
        "HTTP Method",
        options=["GET", "POST", "PUT", "DELETE"],
        index=0
    )
    
    # Common endpoints
    st.header("Common Endpoints")
    
    if st.button("Shop Information"):
        st.session_state.endpoint = "/shop.json"
        st.session_state.method = "GET"
        st.session_state.request_body = "{}"
    
    if st.button("List Products"):
        st.session_state.endpoint = "/products.json"
        st.session_state.method = "GET"
        st.session_state.request_body = "{}"
    
    if st.button("List Orders"):
        st.session_state.endpoint = "/orders.json?status=any"
        st.session_state.method = "GET"
        st.session_state.request_body = "{}"
    
    if st.button("GraphQL API"):
        st.session_state.endpoint = "/graphql.json"
        st.session_state.method = "POST"
        st.session_state.request_body = """
{
  "query": "{
    shop {
      name
      email
      myshopifyDomain
      plan {
        displayName
        partnerDevelopment
        shopifyPlus
      }
    }
  }"
}
"""

# Main content
col1, col2 = st.columns(2)

with col1:
    st.header("Request")
    
    # Request configuration
    with st.container():
        st.markdown('<div class="api-box">', unsafe_allow_html=True)
        
        # Initialize session state for endpoint and request body if not exists
        if "endpoint" not in st.session_state:
            st.session_state.endpoint = "/shop.json"
        if "method" not in st.session_state:
            st.session_state.method = "GET"
        if "request_body" not in st.session_state:
            st.session_state.request_body = "{}"
        
        # Request endpoint
        endpoint = st.text_input(
            "API Endpoint",
            value=st.session_state.endpoint,
            key="current_endpoint"
        )
        st.caption("Example: `/shop.json` or `/products.json`")
        
        # Method selector
        request_method = st.selectbox(
            "Method",
            options=["GET", "POST", "PUT", "DELETE"],
            index=["GET", "POST", "PUT", "DELETE"].index(st.session_state.method),
