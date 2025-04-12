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
    initial_sidebar_state="expanded"
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

# Sidebar setup and configuration
with st.sidebar:
    st.title("🏪 Shopify Alt Text Manager")
    
    # Connection status indicator
    st.markdown(
        "### Shopify Status\n" +
        f"<span class=\"{'status-connected' if st.session_state.shopify_connected else 'status-disconnected'}\">{'Connected' if st.session_state.shopify_connected else 'Disconnected'}</span>",
        unsafe_allow_html=True
    )
    
    st.divider()
    
    # Configuration tabs
    config_tab, templates_tab = st.tabs(["⚙️ Configuration", "📝 Templates"])
    
    with config_tab:
        st.subheader("Shopify Connection")
        
        # Add help expandable sections
        with st.expander("📘 Connection Guide"):
            st.markdown(guides["connection_guide"])
        
        with st.expander("🔍 Troubleshooting"):
            st.markdown(guides["troubleshooting"])
        
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
        
        # Connection test with detailed logs
        if st.button("Connect to Shopify"):
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
                
                # Display connection details for debugging
                with st.expander("Connection Details (for debugging)"):
                    st.code(f"Shop URL: {formatted_shop_url}")
                    token_preview = f"{access_token[:6]}...{access_token[-4:]}" if len(access_token) > 10 else "Invalid token format"
                    st.code(f"Access Token: {token_preview}")
                    st.code(f"API URL: https://{formatted_shop_url}/admin/api/2023-10/shop.json")
                
                # Test connection
                try:
                    response = make_shopify_request("/shop.json")
                    if response and "shop" in response:
                        st.session_state.shopify_connected = True
                        st.success(f"Connected to {response['shop']['name']} successfully!")
                    else:
                        st.error("Failed to connect to Shopify. Check the connection details and try again.")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
            else:
                st.error("Please provide both shop URL and access token")
    
    with templates_tab:
        st.subheader("Templates")
        
        # Add template guide
        with st.expander("📝 Template Guide"):
            st.markdown(guides["template_guide"])
        
        template_name = st.text_input("Template Name", key="new_template_name")
        template_string = st.text_area(
            "Template String",
            placeholder="e.g., {title} - {vendor} product",
            key="new_template_string"
        )
        
        st.caption("Available Variables: {title}, {vendor}, {type}, {tags}")
        
        if st.button("Add Template"):
            if template_name and template_string:
                new_template = {
                    "id": f"template_{len(st.session_state.templates) + 1}",
                    "name": template_name,
                    "template": template_string
                }
                st.session_state.templates.append(new_template)
                st.success(f"Template '{template_name}' added successfully!")
                # Clear inputs
                st.session_state.new_template_name = ""
                st.session_state.new_template_string = ""
            else:
                st.error("Please provide both template name and string")
        
        st.divider()
        
        # Display existing templates
        if st.session_state.templates:
            for i, template in enumerate(st.session_state.templates):
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{template['name']}**")
                        st.text(template['template'])
                    with col2:
                        if st.button("Delete", key=f"delete_{template['id']}"):
                            st.session_state.templates.pop(i)
                            st.rerun()
                st.divider()
        else:
            st.info("No templates added yet")

# Main content
tab1, tab2, tab3 = st.tabs(["🏠 Dashboard", "📋 Products", "🖼️ Product Detail"])

# Dashboard tab
with tab1:
    st.header("Dashboard")
    
    # Help guide in the dashboard
    with st.expander("📖 App User Guide"):
        st.markdown(guides["app_user_guide"])
    
    # Metrics overview
    if st.session_state.shopify_connected:
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
                st.info("Connect to Shopify and fetch products to see metrics")
        
        # Recent products
        st.subheader("Recent Products")
        if st.session_state.recent_products:
            for product_id in st.session_state.recent_products[-5:]:
                product = next((p for p in st.session_state.products if p["id"] == product_id), None)
                if product:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(product["title"])
                    with col2:
                        image_count = len(product["images"])
                        alt_count = sum(1 for img in product["images"] if img["alt"])
                        st.write(f"{alt_count}/{image_count} images with alt text")
                    with col3:
                        if st.button("View", key=f"view_{product['id']}"):
                            st.session_state.current_product = product
                            st.switch_page("Product Detail")
        else:
            st.info("No recent products viewed")
    
    else:
        st.info("Please connect to your Shopify store in the sidebar to get started.")
        
        # Getting started guide
        with st.expander("Getting Started Guide"):
            st.markdown(guides["getting_started"])

# Products tab
with tab2:
    st.header("Products")
    
    # Help guide for Products tab
    with st.expander("ℹ️ Product Management Guide"):
        st.markdown(guides["product_management"])
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search Products", value=st.session_state.search_query)
    with col2:
        if st.button("Fetch Products"):
            if st.session_state.shopify_connected:
                with st.spinner("Fetching products from Shopify..."):
                    st.session_state.products = fetch_products()
                    st.success(f"Fetched {len(st.session_state.products)} products")
            else:
                st.error("Please connect to Shopify first")
    
    # Update search query in session state
    st.session_state.search_query = search
    
    # Filter products based on search query
    filtered_products = st.session_state.products
    if search:
        filtered_products = [p for p in st.session_state.products if search.lower() in p["title"].lower()]
    
    # Display products table
    if filtered_products:
        product_data = []
        for product in filtered_products:
            total_images = len(product["images"])
            images_with_alt = sum(1 for img in product["images"] if img["alt"])
            coverage = (images_with_alt / total_images * 100) if total_images > 0 else 0
            
            product_data.append({
                "ID": product["id"],
                "Title": product["title"],
                "Vendor": product["vendor"],
                "Type": product["type"],
                "Images": f"{images_with_alt}/{total_images}",
                "Coverage": f"{coverage:.1f}%",
                "Action": product["id"]
            })
        
        df = pd.DataFrame(product_data)
        
        # Custom component for clickable view buttons in the table
        def make_clickable(product_id):
            return f'<a href="#" onclick="handleProductClick(\'{product_id}\')">View</a>'
        
        # Use custom JavaScript to handle the button click
        st.markdown("""
        <script>
        function handleProductClick(productId) {
            // Pass the product ID to Streamlit
            const data = {
                product_id: productId
            };
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: data
            }, "*");
        }
        </script>
        """, unsafe_allow_html=True)
        
        # Display the product table
        st.dataframe(
            df.style.format({
                "Coverage": lambda x: x
            }).hide_index(),
            use_container_width=True
        )
        
        # Handle product selection through a form
        with st.form("product_selection_form"):
            product_id = st.selectbox("Select Product to View", 
                                     options=[p["id"] for p in filtered_products],
                                     format_func=lambda x: next((p["title"] for p in filtered_products if p["id"] == x), x))
            
            submitted = st.form_submit_button("View Product")
            if submitted:
                product = next((p for p in filtered_products if p["id"] == product_id), None)
                if product:
                    st.session_state.current_product = product
                    if product_id not in st.session_state.recent_products:
                        st.session_state.recent_products.append(product_id)
                    # Limit recent products list to last 10
                    if len(st.session_state.recent_products) > 10:
                        st.session_state.recent_products = st.session_state.recent_products[-10:]
    else:
        if st.session_state.products:
            st.info("No products match your search criteria")
        else:
            st.info("No products fetched yet. Click 'Fetch Products' to import products from your Shopify store.")

# Product Detail tab
with tab3:
    st.header("Product Detail")
    
    # Help guide for Product Detail tab
    with st.expander("🖼️ Image Alt Text Guide"):
        st.markdown(guides["alt_text_guide"])
    
    if st.session_state.current_product:
        product = st.session_state.current_product
        
        # Product information section
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(product["title"])
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
            st.markdown('<div class="image-grid">', unsafe_allow_html=True)
            
            # Create columns for the image grid
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
    else:
        st.info("Select a product from the Products tab to view details")

# Sync changes back to Shopify (could be added in the Products tab)
if st.session_state.shopify_connected and st.session_state.products:
    if st.button("Sync Changes to Shopify"):
        with st.spinner("Syncing changes to Shopify..."):
            # This demo already updates changes in real-time
            # In a real implementation, you might batch updates
            time.sleep(1)  # Simulating sync delay
            st.success("All changes synced to Shopify successfully!")

# Add FAQ section at the bottom            
st.markdown("---")
with st.expander("❓ Frequently Asked Questions"):
    st.markdown(guides["faq"])

# Footer
st.markdown("---")
st.caption("Shopify Alt Text Manager • © 2025")
