import streamlit as st
import requests
import json
import pandas as pd
import time
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv
import re

# Import guides and helper modules
from guides import load_guides
from shopify_api import make_shopify_request, fetch_products, update_image_alt_text

# Load environment variables if .env file exists
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Shopify Alt Text Manager",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load CSS styling
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'shopify_connected' not in st.session_state:
    st.session_state.shopify_connected = False
if 'products' not in st.session_state:
    st.session_state.products = []
if 'templates' not in st.session_state:
    st.session_state.templates = []
if 'current_product' not in st.session_state:
    st.session_state.current_product = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'recent_products' not in st.session_state:
    st.session_state.recent_products = []
if 'alt_text_coverage' not in st.session_state:
    st.session_state.alt_text_coverage = 0
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "dashboard"
if 'config_open' not in st.session_state:
    st.session_state.config_open = True

# Load guides from the guides module
guides = load_guides()

# Helper functions for template management
def preview_template(template: str, product: Dict) -> str:
    """Generate a preview of a template with a product's data"""
    preview = template
    
    # Replace variables with product data
    variables = {
        "{title}": product.get("title", ""),
        "{vendor}": product.get("vendor", ""),
        "{type}": product.get("type", ""),
        "{tags}": ", ".join(product.get("tags", [])),
    }
    
    for var, value in variables.items():
        preview = preview.replace(var, str(value))
    
    return preview

def apply_template_to_image(product: Dict, image_id: str, template_id: str) -> str:
    """Apply a template to generate alt text for an image"""
    template = next((t for t in st.session_state.templates if t["id"] == template_id), None)
    if not template:
        return ""
    
    alt_text = template["template"]
    
    # Replace variables with product data
    variables = {
        "{title}": product.get("title", ""),
        "{vendor}": product.get("vendor", ""),
        "{type}": product.get("type", ""),
        "{tags}": ", ".join(product.get("tags", [])),
    }
    
    for var, value in variables.items():
        alt_text = alt_text.replace(var, str(value))
    
    # Find image and update its applied_template
    for image in product["images"]:
        if image["id"] == image_id:
            image["alt"] = alt_text
            image["applied_template"] = template_id
            
            # Update in Shopify
            update_image_alt_text(product["id"], image_id, alt_text)
            break
    
    return alt_text

def calculate_coverage_metrics() -> Tuple[int, int, float]:
    """Calculate alt text coverage metrics"""
    total_images = 0
    images_with_alt = 0
    
    for product in st.session_state.products:
        for image in product["images"]:
            total_images += 1
            if image["alt"]:
                images_with_alt += 1
    
    coverage = (images_with_alt / total_images * 100) if total_images > 0 else 0
    return images_with_alt, total_images, coverage

# App header
st.title("🏪 Shopify Alt Text Manager")

# Display connection status
if st.session_state.shopify_connected:
    st.markdown(f"<span class='status-connected'>✅ Connected to Shopify</span>", unsafe_allow_html=True)
else:
    st.markdown(f"<span class='status-disconnected'>❌ Not connected to Shopify</span>", unsafe_allow_html=True)

# Main navigation
st.markdown("<div class='main-nav'>", unsafe_allow_html=True)
tabs = {
    "dashboard": "🏠 Dashboard",
    "connect": "🔌 Connect",
    "templates": "📝 Templates",
    "products": "📋 Products",
    "help": "❓ Help"
}

# Create horizontal tabs
cols = st.columns(len(tabs))
for i, (tab_id, tab_name) in enumerate(tabs.items()):
    with cols[i]:
        if st.button(tab_name, key=f"tab_{tab_id}", 
                     use_container_width=True,
                     type="primary" if st.session_state.active_tab == tab_id else "secondary"):
            st.session_state.active_tab = tab_id
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# Dashboard tab
if st.session_state.active_tab == "dashboard":
    # Help guide in the dashboard
    with st.expander("📖 App User Guide", expanded=not st.session_state.shopify_connected):
        st.markdown(guides["app_user_guide"])
    
    # Metrics overview
    if st.session_state.shopify_connected:
        st.header("Dashboard")
        
        with st.container():
            col1, col2, col3 = st.columns(3)
            
            # Calculate metrics
            if st.session_state.products:
                images_with_alt, total_images, coverage = calculate_coverage_metrics()
                
                with col1:
                    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                    st.markdown("##### Total Products")
                    st.markdown(f"<div class='metric-value'>{len(st.session_state.products)}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                    st.markdown("##### Total Images")
                    st.markdown(f"<div class='metric-value'>{total_images}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col3:
                    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                    st.markdown("##### Alt Text Coverage")
                    st.markdown(f"<div class='metric-value'>{coverage:.1f}%</div>", unsafe_allow_html=True)
                    st.markdown("<div class='coverage-bar'>", unsafe_allow_html=True)
                    st.markdown(f"<div class='coverage-progress' style='width: {coverage}%'></div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                with st.container():
                    st.info("No products loaded yet. Click 'Fetch Products' in the Products tab to import products from your Shopify store.")
                    if st.button("Go to Products Tab"):
                        st.session_state.active_tab = "products"
                        st.rerun()
        
        # Recent products
        st.subheader("Recent Products")
        if st.session_state.recent_products:
            recent_cols = st.columns(3)
            for i, product_id in enumerate(st.session_state.recent_products[-6:]):
                product = next((p for p in st.session_state.products if p["id"] == product_id), None)
                if product:
                    col_idx = i % 3
                    with recent_cols[col_idx]:
                        st.markdown(f"<div class='product-card'>", unsafe_allow_html=True)
                        st.markdown(f"**{product['title']}**")
                        
                        # Show product image if available
                        if product["images"]:
                            try:
                                response = requests.get(product["images"][0]["src"])
                                img = Image.open(BytesIO(response.content))
                                st.image(img, width=150)
                            except:
                                st.image("https://via.placeholder.com/150x150?text=No+Image")
                        else:
                            st.image("https://via.placeholder.com/150x150?text=No+Image")
                        
                        # Alt text stats
                        image_count = len(product["images"])
                        alt_count = sum(1 for img in product["images"] if img["alt"])
                        coverage = (alt_count / image_count * 100) if image_count > 0 else 0
                        
                        st.write(f"Images: {alt_count}/{image_count}")
                        st.progress(coverage/100)
                        
                        if st.button("View Details", key=f"view_recent_{product['id']}"):
                            st.session_state.current_product = product
                            st.session_state.active_tab = "products"
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No recent products viewed")
    
    else:
        st.warning("Please connect to your Shopify store to get started.")
        
        # Getting started guide
        with st.expander("Getting Started Guide", expanded=True):
            st.markdown(guides["getting_started"])
            if st.button("Go to Connect Tab"):
                st.session_state.active_tab = "connect"
                st.rerun()

# Connect tab
elif st.session_state.active_tab == "connect":
    st.header("Connect to Shopify")
    
    # Connection form
    with st.form("connection_form"):
        # Help text with URL format instructions
        st.markdown("""
        **Shopify URL Format:**
        - Enter your Shopify store subdomain
        - Example: `your-store.myshopify.com` or just `your-store`
        - Do not include `https://` or `http://`
        """)
        
        shop_url = st.text_input(
            "Shop URL",
            value=st.session_state.get("shop_url", ""),
            placeholder="your-store.myshopify.com"
        )
        
        # Help text for access token
        st.markdown("""
        **Access Token Format:**
        - Private app tokens start with `shpat_`
        - Custom app tokens start with `shpca_`
        - Ensure the token has `read_products` and `write_products` scopes
        """)
        
        access_token = st.text_input(
            "Access Token",
            value=st.session_state.get("access_token", ""),
            placeholder="shpat_xxxxxxxxxxxxxxxxxxxxx",
            type="password"
        )
        
        show_debug = st.checkbox("Show debug logs", value=False)
        
        # Submit button
        submitted = st.form_submit_button("Connect to Shopify", type="primary", use_container_width=True)
        
        if submitted:
            if shop_url and access_token:
                # Store credentials in session state
                st.session_state.shop_url = shop_url
                st.session_state.access_token = access_token
                
                # Format shop URL
                formatted_shop_url = shop_url.strip()
                if formatted_shop_url.startswith("https://"):
                    formatted_shop_url = formatted_shop_url.replace("https://", "")
                if not ".myshopify.com" in formatted_shop_url:
                    formatted_shop_url = f"{formatted_shop_url}.myshopify.com"
                
                st.session_state.shop_url = formatted_shop_url
                
                # Test connection
                with st.spinner("Connecting to Shopify..."):
                    try:
                        # Make a direct request to test connection
                        raw_response = requests.get(
                            f"https://{formatted_shop_url}/admin/api/2023-10/shop.json",
                            headers={
                                "X-Shopify-Access-Token": access_token,
                                "Content-Type": "application/json"
                            }
                        )
                        
                        # Display debug info if requested
                        if show_debug:
                            st.write("### Response Status")
                            st.code(f"Status Code: {raw_response.status_code}")
                            
                            st.write("### Response Headers")
                            st.json(dict(raw_response.headers))
                            
                            # Display response content
                            st.write("### Response Body")
                            try:
                                response_json = raw_response.json()
                                st.json(response_json)
                            except:
                                st.code(f"Raw Response: {raw_response.text[:1000]}")
                        
                        # Handle the connection result
                        if 200 <= raw_response.status_code < 300:
                            st.session_state.shopify_connected = True
                            try:
                                response_json = raw_response.json()
                                if "shop" in response_json:
                                    st.success(f"✅ Connected to {response_json['shop'].get('name', 'Shopify store')} successfully!")
                                else:
                                    st.success("✅ Connected to Shopify successfully!")
                            except:
                                st.success("✅ Connected to Shopify successfully!")
                                
                            # Redirect to dashboard
                            st.session_state.active_tab = "dashboard"
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to connect. Status code: {raw_response.status_code}")
                            
                            # Status-based troubleshooting hints
                            if raw_response.status_code == 401:
                                st.error("⚠️ Authentication failed (401). Your access token is invalid or expired.")
                                st.info("Generate a new access token in your Shopify admin.")
                            elif raw_response.status_code == 403:
                                st.error("⚠️ Permission denied (403). Your access token doesn't have the required permissions.")
                                st.info("Ensure your token has 'read_products' and 'write_products' scopes.")
                            elif raw_response.status_code == 404:
                                st.error("⚠️ Not found (404). The shop URL may be incorrect.")
                                st.info("Double-check your store URL format.")
                            elif raw_response.status_code == 429:
                                st.error("⚠️ Rate limited (429). Too many requests in a short time.")
                                st.info("Wait a few minutes before trying again.")
                                
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
            else:
                st.error("Please provide both shop URL and access token")
    
    # Help guides
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("📘 Connection Guide"):
            st.markdown(guides["connection_guide"])
    
    with col2:
        with st.expander("🔍 Troubleshooting"):
            st.markdown(guides["troubleshooting"])

# Templates tab
elif st.session_state.active_tab == "templates":
    st.header("Template Management")
    
    # Add template guide
    with st.expander("📝 Template Guide", expanded=len(st.session_state.templates) == 0):
        st.markdown(guides["template_guide"])
    
    # Template creation form
    with st.form("template_form"):
        st.subheader("Create New Template")
        
        template_name = st.text_input(
            "Template Name", 
            key="new_template_name",
            placeholder="e.g., Basic Product Template"
        )
        
        template_string = st.text_area(
            "Template String",
            placeholder="e.g., {title} - {vendor} product",
            key="new_template_string"
        )
        
        st.caption("Available Variables: {title}, {vendor}, {type}, {tags}")
        
        submitted = st.form_submit_button("Add Template", type="primary")
        if submitted:
            if template_name and template_string:
                new_template = {
                    "id": f"template_{len(st.session_state.templates) + 1}",
                    "name": template_name,
                    "template": template_string
                }
                st.session_state.templates.append(new_template)
                st.session_state.new_template_name = ""
                st.session_state.new_template_string = ""
                st.success(f"Template '{template_name}' added successfully!")
                st.rerun()
            else:
                st.error("Please provide both template name and string")
    
    # Display existing templates
    st.subheader("Your Templates")
    
    if st.session_state.templates:
        # Display templates in a grid
        template_cols = st.columns(2)
        for i, template in enumerate(st.session_state.templates):
            col_idx = i % 2
            with template_cols[col_idx]:
                st.markdown(f"<div class='template-card'>", unsafe_allow_html=True)
                st.subheader(template['name'])
                st.code(template['template'])
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("Delete", key=f"delete_{template['id']}"):
                        st.session_state.templates.pop(i)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No templates added yet. Create your first template using the form above.")
        
    # Template usage instructions
    if st.session_state.templates:
        st.subheader("How to Use Templates")
        st.markdown("""
        1. Go to the **Products** tab
        2. Find a product and view its details
        3. Select a template from the dropdown for each image
        4. Click "Apply" to apply the template to the image
        5. You can also apply a template to all images at once
        """)

# Products tab
elif st.session_state.active_tab == "products":
    if not st.session_state.shopify_connected:
        st.warning("Please connect to Shopify first")
        if st.button("Go to Connect Tab"):
            st.session_state.active_tab = "connect"
            st.rerun()
    else:
        # Products overview tab or product detail view toggle
        if st.session_state.current_product is None:
            st.header("Products")
            
            # Fetch and search toolbar
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                search = st.text_input("Search Products", value=st.session_state.search_query)
            with col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("Reset", key="reset_search"):
                    st.session_state.search_query = ""
                    st.rerun()
            with col3:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("Fetch Products", type="primary"):
                    with st.spinner("Fetching products from Shopify..."):
                        st.session_state.products = fetch_products()
                        st.success(f"Fetched {len(st.session_state.products)} products")
                        st.rerun()
            
            # Update search query in session state
            st.session_state.search_query = search
            
            # Filter products based on search query
            filtered_products = st.session_state.products
            if search:
                filtered_products = [p for p in st.session_state.products if search.lower() in p["title"].lower()]
            
            # Display products in a grid layout
            if filtered_products:
                st.write(f"Showing {len(filtered_products)} products")
                
                # Create a grid of product cards
                product_cols = st.columns(3)
                for i, product in enumerate(filtered_products):
                    col_idx = i % 3
                    with product_cols[col_idx]:
                        st.markdown(f"<div class='product-card'>", unsafe_allow_html=True)
                        st.markdown(f"**{product['title']}**")
                        st.caption(f"Vendor: {product['vendor']}")
                        
                        # Show product image if available
                        if product["images"]:
                            try:
                                response = requests.get(product["images"][0]["src"])
                                img = Image.open(BytesIO(response.content))
                                st.image(img, width=150)
                            except:
                                st.image("https://via.placeholder.com/150x150?text=No+Image")
                        else:
                            st.image("https://via.placeholder.com/150x150?text=No+Image")
                        
                        # Alt text stats
                        total_images = len(product["images"])
                        images_with_alt = sum(1 for img in product["images"] if img["alt"])
                        coverage = (images_with_alt / total_images * 100) if total_images > 0 else 0
                        
                        st.write(f"Images: {images_with_alt}/{total_images}")
                        st.progress(coverage/100)
                        
                        if st.button("View Details", key=f"view_{product['id']}"):
                            st.session_state.current_product = product
                            if product["id"] not in st.session_state.recent_products:
                                st.session_state.recent_products.append(product["id"])
                            # Limit recent products list to last 10
                            if len(st.session_state.recent_products) > 10:
                                st.session_state.recent_products = st.session_state.recent_products[-10:]
                            st.rerun()
                            
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                if st.session_state.products:
                    st.info("No products match your search criteria")
                else:
                    st.info("No products fetched yet. Click 'Fetch Products' to import products from your Shopify store.")
# 1. Fix for blank Products tab when viewing details

# Find this code section in your Products tab:
if st.session_state.current_product is None:
    # Products list view code here...
else:
    # ADD THIS SECTION to handle the product details view
    product = st.session_state.current_product
    
    st.header(f"Product: {product['title']}")
    
    # Back button
    if st.button("Back to Products List", key="back_to_products"):
        st.session_state.current_product = None
        st.rerun()
    
    # Product information section
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Product Details")
        st.caption(f"Vendor: {product['vendor']} | Type: {product['type']}")
        
        if product["description"]:
            with st.expander("Description"):
                st.write(product["description"])
    
    with col2:
        # Alt text coverage for this product
        total_images = len(product["images"])
        images_with_alt = sum(1 for img in product["images"] if img["alt"])
        coverage = (images_with_alt / total_images * 100) if total_images > 0 else 0
        
        st.metric("Alt Text Coverage", f"{coverage:.1f}%", f"{images_with_alt}/{total_images} images")
    
    st.divider()
    
    # Images section
    st.subheader("Images")
    
    if product["images"]:
        # Template selection for bulk application
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            bulk_template = st.selectbox(
                "Select Template",
                options=[t["id"] for t in st.session_state.templates],
                format_func=lambda x: next((t["name"] for t in st.session_state.templates if t["id"] == x), x),
                key="bulk_template"
            )
        
        with col2:
            if st.button("Apply to All Images"):
                if bulk_template:
                    for image in product["images"]:
                        apply_template_to_image(product, image["id"], bulk_template)
                    st.success("Template applied to all images")
                else:
                    st.error("Please select a template")
        
        with col3:
            if st.button("Clear All Alt Text"):
                for image in product["images"]:
                    image["alt"] = ""
                    image["applied_template"] = None
                    update_image_alt_text(product["id"], image["id"], "")
                st.success("All alt text cleared")
        
        # Display images in a grid
        num_cols = 3
        cols = st.columns(num_cols)
        
        for i, image in enumerate(product["images"]):
            col_idx = i % num_cols
            
            with cols[col_idx]:
                st.markdown(f'<div class="image-card">', unsafe_allow_html=True)
                
                # Display image
                try:
                    response = requests.get(image["src"])
                    img = Image.open(BytesIO(response.content))
                    st.image(img, width=200)
                except:
                    st.image("https://via.placeholder.com/200x200?text=Image+Not+Available")
                
                # Image position
                st.caption(f"Position: {i+1}")
                
                # Template selector for this image
                template_options = [("", "None")] + [(t["id"], t["name"]) for t in st.session_state.templates]
                selected_template = st.selectbox(
                    "Template",
                    options=[t[0] for t in template_options],
                    format_func=lambda x: next((t[1] for t in template_options if t[0] == x), x),
                    key=f"template_{image['id']}",
                    index=0 if not image["applied_template"] else next((i for i, t in enumerate(template_options) if t[0] == image["applied_template"]), 0)
                )
                
                # Preview current alt text
                st.markdown('<div class="alt-preview">', unsafe_allow_html=True)
                st.write("Alt Text Preview:")
                if selected_template:
                    preview = preview_template(
                        next((t["template"] for t in st.session_state.templates if t["id"] == selected_template), ""),
                        product
                    )
                    st.text(preview[:100] + ("..." if len(preview) > 100 else ""))
                else:
                    st.text(image["alt"][:100] + ("..." if len(image["alt"]) > 100 else ""))
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Apply template button
                if st.button("Apply", key=f"apply_{image['id']}"):
                    if selected_template:
                        new_alt = apply_template_to_image(product, image["id"], selected_template)
                        st.success(f"Applied template: {new_alt[:50]}...")
                    else:
                        # Clear alt text
                        image["alt"] = ""
                        image["applied_template"] = None
                        update_image_alt_text(product["id"], image["id"], "")
                        st.success("Alt text cleared")
                
                st.markdown('</div>', unsafe_allow_html=True)
        
    else:
        st.info("This product has no images")
    
    # Variants section
    if product["variants"]:
        with st.expander("Variants"):
            variant_data = []
            for variant in product["variants"]:
                variant_data.append({
                    "ID": variant["id"],
                    "Title": variant["title"],
                    "Price": f"${variant['price']}"
                })
            
            st.dataframe(pd.DataFrame(variant_data).set_index("ID"), use_container_width=True)

# 2. Fix for Connect tab redirect - find the Connect tab section and modify the success handler:

# Replace this:
if 200 <= raw_response.status_code < 300:
    st.session_state.shopify_connected = True
    try:
        response_json = raw_response.json()
        if "shop" in response_json:
            st.success(f"✅ Connected to {response_json['shop'].get('name', 'Shopify store')} successfully!")
        else:
            st.success("✅ Connected to Shopify successfully!")
    except:
        st.success("✅ Connected to Shopify successfully!")
        
    # Redirect to dashboard - REMOVE THIS LINE
    st.session_state.active_tab = "dashboard"
    st.rerun()

# With this (keeps user on connect tab):
if 200 <= raw_response.status_code < 300:
    st.session_state.shopify_connected = True
    try:
        response_json = raw_response.json()
        if "shop" in response_json:
            st.success(f"✅ Connected to {response_json['shop'].get('name', 'Shopify store')} successfully!")
        else:
            st.success("✅ Connected to Shopify successfully!")
    except:
        st.success("✅ Connected to Shopify successfully!")
    
    # Don't redirect, just rerun to refresh the UI
    st.rerun()

# 3. Add product selection functionality - enhance the product fetching in the shopify_api.py file:

# Add this function to shopify_api.py:
def fetch_selected_products(selected_ids=None) -> List[Dict]:
    """Fetch specific products from Shopify using GraphQL API
    
    Args:
        selected_ids: Optional list of product IDs to fetch. If None, fetches all products.
    """
    if selected_ids:
        # Build a GraphQL query with product ID filter
        id_filter = ", ".join([f'"{id}"' for id in selected_ids])
        query = f"""
        {{
          products(first: 50, query: "id:{id_filter}") {{
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
        # Fetch all products (original query with added SKU field)
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

# 4. Update template variables - modify the preview_template and apply_template_to_image functions:

def preview_template(template: str, product: Dict) -> str:
    """Generate a preview of a template with a product's data"""
    preview = template
    
    # Replace variables with product data
    variables = {
        "{title}": product.get("title", ""),
        "{vendor}": product.get("vendor", ""),
        "{type}": product.get("type", ""),
        "{tags}": ", ".join(product.get("tags", [])),
        "{store}": product.get("store", ""),
        "{sku}": ", ".join(product.get("skus", [])),
        "{color}": extract_color_from_title(product.get("title", "")),
        "{brand}": product.get("vendor", ""),  # Alias for vendor
        "{category}": product.get("type", ""), # Alias for type
    }
    
    for var, value in variables.items():
        preview = preview.replace(var, str(value))
    
    return preview

def apply_template_to_image(product: Dict, image_id: str, template_id: str) -> str:
    """Apply a template to generate alt text for an image"""
    template = next((t for t in st.session_state.templates if t["id"] == template_id), None)
    if not template:
        return ""
    
    alt_text = template["template"]
    
    # Replace variables with product data
    variables = {
        "{title}": product.get("title", ""),
        "{vendor}": product.get("vendor", ""),
        "{type}": product.get("type", ""),
        "{tags}": ", ".join(product.get("tags", [])),
        "{store}": product.get("store", ""),
        "{sku}": ", ".join(product.get("skus", [])),
        "{color}": extract_color_from_title(product.get("title", "")),
        "{brand}": product.get("vendor", ""),  # Alias for vendor
        "{category}": product.get("type", ""), # Alias for type
    }
    
    for var, value in variables.items():
        alt_text = alt_text.replace(var, str(value))
    
    # Find image and update its applied_template
    for image in product["images"]:
        if image["id"] == image_id:
            image["alt"] = alt_text
            image["applied_template"] = template_id
            
            # Update in Shopify
            update_image_alt_text(product["id"], image_id, alt_text)
            break
    
    return alt_text

# Helper function to extract color from title
def extract_color_from_title(title):
    # Common colors that might appear in product titles
    common_colors = [
        "black", "white", "red", "blue", "green", "yellow", "purple", "pink", 
        "orange", "brown", "grey", "gray", "silver", "gold", "beige", "navy", 
        "teal", "cream", "ivory", "turquoise", "violet", "magenta", "indigo"
    ]
    
    words = title.lower().split()
    for word in words:
        if word in common_colors:
            return word
    
    return ""

# 5. Add the product selection UI to the Products tab:

# Replace the fetch button area:
if st.button("Fetch Products", type="primary"):
    with st.spinner("Fetching products from Shopify..."):
        st.session_state.products = fetch_products()
        st.success(f"Fetched {len(st.session_state.products)} products")
        st.rerun()

# With this:
# Fetch products button with selection options
fetch_col1, fetch_col2 = st.columns([3, 1])
with fetch_col1:
    fetch_option = st.radio(
        "Fetch options:", 
        ["All Products", "Selected Products"], 
        horizontal=True
    )

with fetch_col2:
    if st.button("Fetch Products", type="primary"):
        with st.spinner("Fetching products from Shopify..."):
            if fetch_option == "All Products":
                st.session_state.products = fetch_products()
                st.success(f"Fetched {len(st.session_state.products)} products")
            else:
                # If we already have products, show a selection UI
                if st.session_state.products:
                    product_ids = [p["id"] for p in st.session_state.products]
                    product_titles = [p["title"] for p in st.session_state.products]
                    selected_indices = st.multiselect(
                        "Select products to fetch",
                        options=range(len(product_ids)),
                        format_func=lambda i: product_titles[i]
                    )
                    
                    if selected_indices:
                        selected_ids = [product_ids[i] for i in selected_indices]
                        st.session_state.products = fetch_selected_products(selected_ids)
                        st.success(f"Fetched {len(st.session_state.products)} selected products")
                    else:
                        st.warning("Please select at least one product")
                else:
                    # If no products loaded yet, fetch all first
                    st.session_state.products = fetch_products()
                    st.success(f"Fetched {len(st.session_state.products)} products")
            st.rerun()

# 6. Update the template guide to show the new variables:
# Add this to the guides.py file in the "template_guide" section:

### Available Variables

- `{title}` - The product title
- `{vendor}` or `{brand}` - The product vendor/brand
- `{type}` or `{category}` - The product type/category
- `{tags}` - The product tags (comma separated)
- `{store}` - Your store name
- `{sku}` - Product SKU codes (if available)
- `{color}` - Detected color from product title
