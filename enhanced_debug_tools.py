"""
Enhanced debugging tools for troubleshooting Shopify API connections
"""
import requests
import json
import streamlit as st
import time
from typing import Dict, Any, Tuple
import ssl
import socket
import traceback

def test_network_connectivity(domain: str, port: int = 443) -> Tuple[bool, str]:
    """Test basic network connectivity to a domain and port"""
    try:
        # Create a socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        
        # Try to connect
        result = sock.connect_ex((domain, port))
        
        if result == 0:
            return True, "Connection successful"
        else:
            return False, f"Connection failed with error code: {result}"
    except socket.gaierror:
        return False, "Domain name resolution failed"
    except socket.timeout:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Connection error: {str(e)}"
    finally:
        sock.close()

def test_tls_connection(domain: str) -> Tuple[bool, Dict[str, Any]]:
    """Test TLS/SSL connection and get certificate information"""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
                # Extract key certificate details
                cert_details = {
                    "subject": dict(x[0] for x in cert["subject"]),
                    "issuer": dict(x[0] for x in cert["issuer"]),
                    "version": cert["version"],
                    "notBefore": cert["notBefore"],
                    "notAfter": cert["notAfter"]
                }
                
                return True, cert_details
    except Exception as e:
        return False, {"error": str(e)}

def detailed_connection_test(shop_url: str, access_token: str) -> Dict[str, Any]:
    """Run detailed connectivity tests and diagnostics"""
    results = {}
    
    # Clean up the URL to get just the domain
    domain = shop_url.replace("https://", "").replace("http://", "").strip("/")
    if not ".myshopify.com" in domain:
        domain = f"{domain}.myshopify.com"
    
    # Test basic connectivity
    results["connectivity"] = {}
    connectivity_success, connectivity_msg = test_network_connectivity(domain)
    results["connectivity"]["success"] = connectivity_success
    results["connectivity"]["message"] = connectivity_msg
    
    # Test TLS connection
    results["tls"] = {}
    tls_success, tls_details = test_tls_connection(domain)
    results["tls"]["success"] = tls_success
    results["tls"]["details"] = tls_details
    
    # Test HTTP requests
    results["http"] = {}
    
    # Test with direct HTTP request (no API token, just checking if site is up)
    try:
        start_time = time.time()
        response = requests.get(f"https://{domain}", timeout=10)
        elapsed = time.time() - start_time
        
        results["http"]["direct"] = {
            "success": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "response_time": f"{elapsed:.2f}s"
        }
    except Exception as e:
        results["http"]["direct"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test with API request
    try:
        url = f"https://{domain}/admin/api/2023-10/shop.json"
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10)
        elapsed = time.time() - start_time
        
        results["http"]["api"] = {
            "success": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "response_time": f"{elapsed:.2f}s"
        }
        
        # Additional response info
        try:
            results["http"]["api"]["response"] = response.json()
        except:
            results["http"]["api"]["response_text"] = response.text[:1000]
            
        results["http"]["api"]["headers"] = dict(response.headers)
    except Exception as e:
        results["http"]["api"] = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    return results

def display_debug_info(shop_url: str, access_token: str):
    """Display comprehensive debug information in the Streamlit app"""
    st.subheader("Comprehensive Connection Diagnostics")
    
    with st.spinner("Running connectivity tests..."):
        results = detailed_connection_test(shop_url, access_token)
    
    # Display connectivity test results
    st.write("### Basic Connectivity Test")
    conn_status = results["connectivity"]["success"]
    st.write(f"Status: {'✅ Connected' if conn_status else '❌ Failed'}")
    st.write(f"Details: {results['connectivity']['message']}")
    
    # Display TLS test results
    st.write("### TLS/SSL Connection Test")
    tls_status = results["tls"]["success"]
    st.write(f"Status: {'✅ Secure connection established' if tls_status else '❌ Failed'}")
    if tls_status:
        with st.expander("Certificate Details"):
            st.json(results["tls"]["details"])
    else:
        st.error(f"TLS Error: {results['tls']['details'].get('error', 'Unknown error')}")
    
    # Display HTTP test results
    st.write("### HTTP Connection Tests")
    
    # Direct website connection
    direct_status = results["http"]["direct"].get("success", False)
    st.write(f"Website Availability: {'✅ Available' if direct_status else '❌ Not available'}")
    if direct_status:
        st.write(f"Status Code: {results['http']['direct']['status_code']}")
        st.write(f"Response Time: {results['http']['direct']['response_time']}")
    else:
        st.error(f"Error: {results['http']['direct'].get('error', 'Unknown error')}")
    
    # API connection
    api_status = results["http"]["api"].get("success", False)
    st.write(f"API Availability: {'✅ Available' if api_status else '❌ Failed'}")
    
    with st.expander("API Response Details"):
        if api_status:
            st.write(f"Status Code: {results['http']['api']['status_code']}")
            st.write(f"Response Time: {results['http']['api']['response_time']}")
            
            if "response" in results["http"]["api"]:
                st.json(results["http"]["api"]["response"])
            elif "response_text" in results["http"]["api"]:
                st.code(results["http"]["api"]["response_text"])
                
            st.write("### Response Headers")
            st.json(results["http"]["api"]["headers"])
        else:
            st.error(f"Error: {results['http']['api'].get('error', 'Unknown error')}")
            if "traceback" in results["http"]["api"]:
                st.code(results["http"]["api"]["traceback"])
    
    # Recommendations
    st.write("### Troubleshooting Recommendations")
    
    if not conn_status:
        st.error("❗ Network connectivity issue detected. Ensure you can reach the Shopify domain.")
    
    if not tls_status:
        st.error("❗ TLS/SSL connection issue detected. This may indicate network restrictions or security software interference.")
    
    if not direct_status:
        st.error("❗ Cannot connect to the Shopify store website. Verify the store URL is correct and the store is active.")
    
    if not api_status:
        api_status_code = results["http"]["api"].get("status_code", 0)
        
        if api_status_code == 401:
            st.error("❗ Authentication failed (401). Your access token is invalid or expired. Generate a new token.")
        elif api_status_code == 403:
            st.error("❗ Permission denied (403). Your access token does not have the required permissions.")
        elif api_status_code == 404:
            st.error("❗ Not found (404). The API endpoint doesn't exist or the shop URL is incorrect.")
        elif api_status_code == 429:
            st.error("❗ Rate limited (429). Too many requests in a short time. Wait and try again later.")
        else:
            st.error(f"❗ API connection failed. Check the detailed error message above.")
    
    if conn_status and tls_status and direct_status and not api_status:
        st.warning("⚠️ The store is reachable, but the API connection failed. This likely indicates an authentication issue with your access token.")
