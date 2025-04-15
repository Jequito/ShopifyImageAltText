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
import random
import string

# Load environment variables if .env file exists
load_dotenv()

# Import guides and helper modules
from guides import load_guides
from shopify_api import (
    make_shopify_request, fetch_products, fetch_selected_products, 
    update_image_alt_text, update_image_filename, generate_unique_filename
)
from enhanced_debug_tools import display_debug_info

# Set page configuration
st.set_page_config(
    page_title="Shopify Alt Text Manager",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load CSS styling
try:
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    # Default styles if file not found
    st.markdown("""
    <style>
    .status-connected { color: green; font-weight: bold; }
    .status-disconnected { color: red; font-weight: bold; }
    .product-card, .template-card, .metric-card { 
        background-color: #f8f9fa; 
        border-radius: 10px; 
        padding: 15px; 
        margin-bottom: 10px; 
    }
    .image-card {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        max-width: 100%;
    }
    .alt-preview {
        background-color: #f0f0f0;
        padding: 8px;
        border-radius: 4px;
        margin-top: 8px;
        font-size: 12px;
        min-height: 40px;
    }
    .metric-value { font-size: 24px; font-weight: bold; }
    .coverage-bar {
        height: 10px;
        background-color: #e9ecef;
        border-radius: 5px;
        margin-top: 5px;
    }
    .coverage-progress {
        height: 10px;
        background-color: #4CAF50;
        border-radius: 5px;
    }
    .compact-tabs {
        margin-bottom: 0.5rem;
    }
    .compact-form {
        padding: 0.5rem 0;
    }
    .tabs-container {
        margin-bottom: 1rem;
    }
    .main-nav {
        margin-bottom: 1rem;
    }
    .image-action-buttons {
        display: flex;
        gap: 5px;
    }
    .filename-field {
        font-size: 12px;
        color: #666;
        margin-top: 5px;
        overflow-wrap: break-word;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'shopify_connected' not in st.session_state:
    st.session_state.shopify_connected = False
if 'products' not in st.session_state:
    st.session_state.products = []
if 'templates' not in st.session_state:
    st.session_state.templates = []
if 'filename_templates' not in st.session_state:
    st.session_state.filename_templates = []
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
    st.session_state.config_open = False
if 'shop_name' not in st.session_state:
    st.session_state.shop_name = ""
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False
if 'fetch_limit' not in st.session_state:
    st.session_state.fetch_limit = 50
if 'compact_mode' not in st.session_state:
    st.session_state.compact_mode = True

# Load guides from the guides module
guides = load_guides()

# Helper function to extract color from title
def extract_color_from_title(title):
    """Extract a color name from the product title if present"""
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

# Helper functions for template management
def preview_template(template: str, product: Dict, image_index: int = 0) -> str:
    """Generate a preview of a template with a product's data"""
    preview = template
    
    # Generate a random ID for unique filename purposes
    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    # Replace variables with product data
    variables = {
        "{title}": product.get("title", ""),
        "{vendor}": product.get("vendor", ""),
        "{type}": product.get("type", ""),
        "{tags}": ", ".join(product.get("tags", [])),
        "{store}": product.get("store", ""),
        "{sku}": ", ".join(product.get("skus", [])) if "skus" in product else "",
        "{color}": extract_color_from_title(product.get("title", "")),
        "{brand}": product.get("vendor", ""),  # Alias for vendor
        "{category}": product.get("type", ""), # Alias for type
        "{index}": str(image_index + 1),
        "{id}": random_id
    }
    
    for var, value in variables.items():
        preview = preview.replace(var, str(value))
    
    return preview

def apply_template_to_image(product: Dict, image_id: str, template_id: str) -> str:
    """Apply a template to generate alt text for an image"""
    template = next((t for t in st.session_state.templates if t["id"] == template_id), None)
    if not template:
        return ""
    
    # Find the image and its index
    image_index = 0
    for idx, image in enumerate(product["images"]):
        if image["id"] == image_id:
            image_index = idx
            break
    
    # Generate a random ID for unique filename purposes
    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    alt_text = template["template"]
    
    # Replace variables with product data
    variables = {
        "{title}": product.get("title", ""),
        "{vendor}": product.get("vendor", ""),
        "{type}": product.get("type", ""),
        "{tags}": ", ".join(product.get("tags", [])),
        "{store}": product.get("store", ""),
        "{sku}": ", ".join(product.get("skus", [])) if "skus" in product else "",
        "{color}": extract_color_from_title(product.get("title", "")),
        "{brand}": product.get("vendor", ""),  # Alias for vendor
        "{category}": product.get("type", ""), # Alias for type
        "{index}": str(image_index + 1),
        "{id}": random_id
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

def apply_filename_template_to_image(product: Dict, image_id: str, template_id: str) -> str:
    """Apply a template to generate filename for an image"""
    template = next((t for t in st.session_state.filename_templates if t["id"] == template_id), None)
    if not template:
        return ""
    
    # Find the image and its index
    image_index = 0
    for idx, image in enumerate(product["images"]):
        if image["id"] == image_id:
            image_index = idx
            break
    
    # Generate a random ID for unique filename purposes
    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    filename_template = template["template"]
    
    # Replace variables with product data
    variables = {
        "{title}": product.get("title", "").replace(" ", "-").lower(),
        "{vendor}": product.get("vendor", "").replace(" ", "-").lower(),
        "{type}": product.get("type", "").replace(" ", "-").lower(),
        "{tags}": "-".join(product.get("tags", [])).lower(),
        "{store}": product.get("store", "").replace(" ", "-").lower(),
        "{sku}": "-".join(product.get("skus", [])) if "skus" in product else "",
        "{color}": extract_color_from_title(product.get("title", "")),
        "{brand}": product.get("vendor", "").replace(" ", "-").lower(),  # Alias for vendor
        "{category}": product.get("type", "").replace(" ", "-").lower(), # Alias for type
        "{index}": str(image_index + 1),
        "{id}": random_id
    }
    
    for var, value in variables.items():
        filename_template = filename_template.replace(var, str(value))
    
    # Ensure filename has extension
    if "." not in filename_template:
        filename_template += ".jpg"
    
    # Generate a unique filename to avoid conflicts
    filename = generate_unique_filename(filename_template, product["id"], image_id)
    
    # Find image and update its applied_filename_template
    for image in product["images"]:
        if image["id"] == image_id:
            image["filename"] = filename
            image["applied_filename_template"] = template_id
            
            # Update in Shopify
            update_image_filename(product["id"], image_id, filename)
            break
    
    return filename

def calculate_coverage_metrics() -> Tuple[int, int, float, float]:
    """Calculate alt text and filename coverage metrics"""
    total_images = 0
    images_with_alt = 0
    images_with_filename = 0
    
    for product in st.session_state.products:
        for image in product["images"]:
            total_images += 1
            if image.get("alt"):
                images_with_alt += 1
            if image.get("applied_filename_template"):
                images_with_filename += 1
    
    alt_coverage = (images_with_alt / total_images * 100) if total_images > 0 else 0
    filename_coverage = (images_with_filename / total_images * 100) if total_images > 0 else 0
    
    return images_with_alt, total_images, alt_coverage, filename_coverage

# App header with more compact layout
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏪 Shopify Alt Text Manager")
with col2:
    # Display compact connection status and UI mode toggle
    if st.session_state.shopify_connected:
        st.markdown(f"<span class='status-connected'>✅ Connected to Shopify</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span class='status-disconnected'>❌ Not connected to Shopify</span>", unsafe_allow_html=True)
    
    # Toggle for compact mode
    compact_mode = st.toggle("Compact UI", value=st.session_state.compact_mode)
    if compact_mode != st.session_state.compact_mode:
        st.session_state.compact_mode = compact_mode
        st.rerun()

# Main navigation
st.markdown("<div class='main-nav'>", unsafe_allow_html=True)
tabs = {
    "dashboard": "🏠 Dashboard",
    "connect": "🔌 Connect",
    "templates": "📝 Templates",
    "products": "📋 Products",
    "debug": "🔍 Debug",
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
    with st.expander("📖 App User Guide", expanded=not st.session_state.shopify_connected and not st.session_state.compact_mode):
        st.markdown(guides["app_user_guide"])
    
    # Metrics overview
    if st.session_state.shopify_connected:
        st.header("Dashboard")
        
        with st.container():
            col1, col2 = st.columns(2)
            
            # Calculate metrics
            if st.session_state.products:
                images_with_alt, total_images, alt_coverage, filename_coverage = calculate_coverage_metrics()
                
                with col1:
                    # Products and Images
                    metric_cols = st.columns(2)
                    with metric_cols[0]:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        st.markdown("##### Total Products")
                        st.markdown(f"<div class='metric-value'>{len(st.session_state.products)}</div>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with metric_cols[1]:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        st.markdown("##### Total Images")
                        st.markdown(f"<div class='metric-value'>{total_images}</div>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                
                with col2:
                    # Coverage metrics
                    coverage_cols = st.columns(2)
                    
                    with coverage_cols[0]:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        st.markdown("##### Alt Text Coverage")
                        st.markdown(f"<div class='metric-value'>{alt_coverage:.1f}%</div>", unsafe_allow_html=True)
                        st.markdown("<div class='coverage-bar'>", unsafe_allow_html=True)
                        st.markdown(f"<div class='coverage-progress' style='width: {alt_coverage}%'></div>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                        st.markdown(f"<small>{images_with_alt} of {total_images} images</small>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with coverage_cols[1]:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        st.markdown("##### Filename Coverage")
                        st.markdown(f"<div class='metric-value'>{filename_coverage:.1f}%</div>", unsafe_allow_html=True)
                        st.markdown("<div class='coverage-bar'>", unsafe_allow_html=True)
                        st.markdown(f"<div class='coverage-progress' style='width: {filename_coverage}%'></div>", unsafe_allow_html=True)
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
                        filename_count = sum(1 for img in product["images"] if img.get("applied_filename_template"))
                        alt_coverage = (alt_count / image_count * 100) if image_count > 0 else 0
                        
                        st.write(f"Alt Text: {alt_count}/{image_count} ({alt_coverage:.1f}%)")
                        st.progress(alt_coverage / 100)
                        st.write(f"Filenames: {filename_count}/{image_count}")
                        
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

# Products tab
elif st.session_state.active_tab == "products":
    st.header("Products Management")
    
    # Products guide
    with st.expander("📋 Product Management Guide", expanded=len(st.session_state.products) == 0 and not st.session_state.compact_mode):
        st.markdown(guides["product_management"])
    
    # Product fetch options
    st.subheader("Fetch Products")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("Fetch All Products", key="fetch_all", type="primary", use_container_width=True):
            with st.spinner("Fetching products from Shopify..."):
                try:
                    products = fetch_products()
                    if products:
                        st.session_state.products = products
                        st.success(f"✅ Successfully imported {len(products)} products")
                        st.rerun()
                    else:
                        st.error("❌ No products retrieved. Check connection and permissions.")
                except Exception as e:
                    st.error(f"Error fetching products: {str(e)}")
    
    with col2:
        limit = st.number_input("Max Products", value=st.session_state.fetch_limit, min_value=1, max_value=250, step=10)
        if limit != st.session_state.fetch_limit:
            st.session_state.fetch_limit = limit
    
    # Display products if available
    if st.session_state.products:
        st.subheader(f"Products ({len(st.session_state.products)})")
        
        # Search box
        search_query = st.text_input("Search Products", value=st.session_state.search_query)
        st.session_state.search_query = search_query
        
        # Filter products by search query
        filtered_products = st.session_state.products
        if search_query:
            filtered_products = [p for p in st.session_state.products if search_query.lower() in p["title"].lower()]
        
        # Create a dataframe for display
        product_data = []
        for product in filtered_products:
            # Calculate alt text coverage
            total_images = len(product["images"])
            images_with_alt = sum(1 for img in product["images"] if img.get("alt"))
            images_with_filename = sum(1 for img in product["images"] if img.get("applied_filename_template"))
            alt_coverage = (images_with_alt / total_images * 100) if total_images > 0 else 0
            filename_coverage = (images_with_filename / total_images * 100) if total_images > 0 else 0
            
            product_data.append({
                "ID": product["id"],
                "Product": product["title"],
                "Images": f"{total_images}",
                "Alt Coverage": f"{alt_coverage:.1f}%",
                "Filename Coverage": f"{filename_coverage:.1f}%",
                "Vendor": product["vendor"]
            })
        
        if product_data:
            # Convert to dataframe
            df = pd.DataFrame(product_data)
            
            # Show product table with a view details button - compact layout
            # Add table header
            header_cols = st.columns([4, 1, 1.5, 1.5, 1.5, 1.5])
            with header_cols[0]:
                st.markdown("**Product**")
            with header_cols[1]:
                st.markdown("**Images**")
            with header_cols[2]:
                st.markdown("**Alt Text**")
            with header_cols[3]:
                st.markdown("**Filename**")
            with header_cols[4]:
                st.markdown("**Vendor**")
            with header_cols[5]:
                st.markdown("**Actions**")
            
            st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)
            
            # Show product rows
            for i, row in df.iterrows():
                cols = st.columns([4, 1, 1.5, 1.5, 1.5, 1.5])
                
                with cols[0]:
                    st.write(row["Product"])
                with cols[1]:
                    st.write(row["Images"])
                with cols[2]:
                    st.write(row["Alt Coverage"])
                with cols[3]:
                    st.write(row["Filename Coverage"])
                with cols[4]:
                    st.write(row["Vendor"])
                with cols[5]:
                    if st.button("View", key=f"view_{row['ID']}", use_container_width=True):
                        product = next((p for p in st.session_state.products if p["id"] == row["ID"]), None)
                        if product:
                            st.session_state.current_product = product
                            
                            # Add to recent products list
                            if row["ID"] in st.session_state.recent_products:
                                st.session_state.recent_products.remove(row["ID"])
                            st.session_state.recent_products.append(row["ID"])
                            
                            # Show product details
                            st.rerun()
                
                st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)
        else:
            st.info("No products match your search criteria")
    else:
        st.info("No products loaded. Click 'Fetch Products' to import products from your Shopify store.")
    
    # Product detail view
    if st.session_state.current_product:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader(f"Product Details: {st.session_state.current_product['title']}")
        
        # Product info
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"**Vendor:** {st.session_state.current_product['vendor']}")
            st.write(f"**Type:** {st.session_state.current_product['type']}")
            if st.session_state.current_product.get('tags'):
                st.write(f"**Tags:** {', '.join(st.session_state.current_product['tags'])}")
        
        with col2:
            if st.button("Back to Products", use_container_width=True):
                st.session_state.current_product = None
                st.rerun()
        
        # Bulk templates in tabs
        st.subheader("Bulk Apply Templates")
        template_bulk_tabs = st.tabs(["Alt Text Templates", "Filename Templates"])
        
        # Alt Text Template Bulk Tab
        with template_bulk_tabs[0]:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if st.session_state.templates:
                    template_options = {t["id"]: t["name"] for t in st.session_state.templates}
                    selected_template = st.selectbox(
                        "Select Alt Text Template",
                        options=list(template_options.keys()),
                        format_func=lambda x: template_options[x],
                        key="bulk_alt_template"
                    )
                    
                    # Preview selected template
                    template = next((t for t in st.session_state.templates if t["id"] == selected_template), None)
                    if template:
                        preview = preview_template(template["template"], st.session_state.current_product)
                        st.markdown("<div class='alt-preview'>", unsafe_allow_html=True)
                        st.write(f"Preview: {preview}")
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("No alt text templates available. Create templates in the Templates tab.")
                    selected_template = None
            
            with col2:
                if selected_template and st.button("Apply to All Images", use_container_width=True, type="primary"):
                    # Apply template to all images
                    product = st.session_state.current_product
                    for image in product["images"]:
                        apply_template_to_image(product, image["id"], selected_template)
                    
                    st.success("✅ Alt text template applied to all images")
                    st.rerun()
        
        # Filename Template Bulk Tab
        with template_bulk_tabs[1]:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if st.session_state.filename_templates:
                    filename_template_options = {t["id"]: t["name"] for t in st.session_state.filename_templates}
                    selected_filename_template = st.selectbox(
                        "Select Filename Template",
                        options=list(filename_template_options.keys()),
                        format_func=lambda x: filename_template_options[x],
                        key="bulk_filename_template"
                    )
                    
                    # Preview selected template
                    template = next((t for t in st.session_state.filename_templates if t["id"] == selected_filename_template), None)
                    if template:
                        preview = preview_template(template["template"], st.session_state.current_product)
                        if "." not in preview:
                            preview += ".jpg"
                        st.markdown("<div class='alt-preview'>", unsafe_allow_html=True)
                        st.write(f"Preview: {preview}")
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("No filename templates available. Create templates in the Templates tab.")
                    selected_filename_template = None
            
            with col2:
                if selected_filename_template and st.button("Apply to All Images", use_container_width=True, type="primary", key="bulk_apply_filename"):
                    # Apply template to all images
                    product = st.session_state.current_product
                    for image in product["images"]:
                        apply_filename_template_to_image(product, image["id"], selected_filename_template)
                    
                    st.success("✅ Filename template applied to all images")
                    st.rerun()
        
        # Display images with alt text and filename editing
        st.subheader("Product Images")
        
        # Create a grid of images
        image_grid = st.container()
        
        with image_grid:
            # Create columns for the grid - make it more compact with 3 columns
            cols = st.columns(3)
            
            for i, image in enumerate(st.session_state.current_product["images"]):
                col_idx = i % 3
                
                with cols[col_idx]:
                    st.markdown(f"<div class='image-card'>", unsafe_allow_html=True)
                    
                    # Display image
                    try:
                        response = requests.get(image["src"])
                        img = Image.open(BytesIO(response.content))
                        st.image(img, width=200)
                    except:
                        st.image("https://via.placeholder.com/200x200?text=No+Image")
                    
                    # Use tabs for Alt Text and Filename settings
                    image_tabs = st.tabs(["Alt Text", "Filename"])
                    
                    # Alt Text Tab
                    with image_tabs[0]:
                        # Current alt text
                        st.text_area(
                            f"Alt Text #{i+1}",
                            value=image.get("alt", ""),
                            key=f"alt_{image['id']}",
                            height=80
                        )
                        
                        # Alt Text Template selector
                        if st.session_state.templates:
                            template_options = {t["id"]: t["name"] for t in st.session_state.templates}
                            template_options[""] = "Select a template..."
                            
                            selected = st.selectbox(
                                "Apply Template",
                                options=list(template_options.keys()),
                                format_func=lambda x: template_options[x],
                                key=f"template_{image['id']}",
                                index=0
                            )
                            
                            # Action buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if selected:
                                    if st.button("Apply", key=f"apply_{image['id']}"):
                                        new_alt_text = apply_template_to_image(
                                            st.session_state.current_product,
                                            image["id"],
                                            selected
                                        )
                                        st.success(f"Template applied")
                                        st.rerun()
                            
                            with col2:
                                if st.button("Clear", key=f"clear_{image['id']}"):
                                    # Clear alt text
                                    for img in st.session_state.current_product["images"]:
                                        if img["id"] == image["id"]:
                                            img["alt"] = ""
                                            img["applied_template"] = None
                                            
                                            # Update in Shopify
                                            update_image_alt_text(st.session_state.current_product["id"], image["id"], "")
                                            break
                                    
                                    st.success("Alt text cleared")
                                    st.rerun()
                    
                    # Filename Tab
                    with image_tabs[1]:
                        # Display current filename
                        st.markdown(f"<div class='filename-field'>Current: {image.get('filename', 'No filename')}</div>", unsafe_allow_html=True)
                        
                        # Filename Template selector
                        if st.session_state.filename_templates:
                            filename_template_options = {t["id"]: t["name"] for t in st.session_state.filename_templates}
                            filename_template_options[""] = "Select a template..."
                            
                            selected_filename = st.selectbox(
                                "Apply Filename Template",
                                options=list(filename_template_options.keys()),
                                format_func=lambda x: filename_template_options[x],
                                key=f"filename_template_{image['id']}",
                                index=0
                            )
                            
                            # Action buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if selected_filename:
                                    if st.button("Apply", key=f"apply_filename_{image['id']}"):
                                        new_filename = apply_filename_template_to_image(
                                            st.session_state.current_product,
                                            image["id"],
                                            selected_filename
                                        )
                                        st.success(f"Filename updated")
                                        st.rerun()
                            
                            with col2:
                                if st.button("Clear", key=f"clear_filename_{image['id']}"):
                                    # We can't really "clear" a filename back to default in Shopify
                                    # But we can mark it as not having an applied template
                                    for img in st.session_state.current_product["images"]:
                                        if img["id"] == image["id"]:
                                            img["applied_filename_template"] = None
                                            break
                                    
                                    st.success("Filename template cleared")
                                    st.rerun()
                        else:
                            st.info("Create filename templates in the Templates tab")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
