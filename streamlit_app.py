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
# Templates tab
elif st.session_state.active_tab == "templates":
    improved_template_management()
    
# Products tab
elif st.session_state.active_tab == "products":
    improved_product_management()
    
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
# Debug tab
elif st.session_state.active_tab == "debug":
    st.header("Debug Mode")
    
    st.warning("⚠️ This section is for troubleshooting purposes only.")
    
    if not st.session_state.shopify_connected:
        st.error("You need to connect to Shopify first to use the debugging tools.")
    else:
        st.info("Use these tools to diagnose connection issues with your Shopify store.")
        
        # Debug options
        st.subheader("Connection Details")
        st.write(f"**Store URL:** {st.session_state.shop_url}")
        st.write(f"**Connection Status:** {'Connected' if st.session_state.shopify_connected else 'Disconnected'}")
        if hasattr(st.session_state, 'shop_name') and st.session_state.shop_name:
            st.write(f"**Store Name:** {st.session_state.shop_name}")
        
        # Debug tools expander
        with st.expander("Run Comprehensive Diagnostics", expanded=not st.session_state.compact_mode):
            if st.button("Start Diagnostic Test", type="primary", use_container_width=True):
                if st.session_state.shopify_connected and hasattr(st.session_state, 'shop_url') and hasattr(st.session_state, 'access_token'):
                    with st.spinner("Running diagnostics..."):
                        # Use the enhanced_debug_tools module's function
                        display_debug_info(st.session_state.shop_url, st.session_state.access_token)
                else:
                    st.error("Cannot run diagnostics. Please ensure you are connected to Shopify.")
        
        # Test individual API endpoints
        st.subheader("Test API Endpoints")
        
        test_endpoints = {
            "Shop Information": "/shop.json",
            "Product Count": "/products/count.json",
            "First 5 Products": "/products.json?limit=5",
            "First 5 Collections": "/collections.json?limit=5"
        }
        
        selected_endpoint = st.selectbox(
            "Select API endpoint to test", 
            options=list(test_endpoints.keys())
        )
        
        if st.button("Test Endpoint", key="test_endpoint_btn"):
            with st.spinner(f"Testing endpoint {test_endpoints[selected_endpoint]}..."):
                result = make_shopify_request(test_endpoints[selected_endpoint])
                if result:
                    st.success("✅ API call successful")
                    st.json(result)
                else:
                    st.error("❌ API call failed")
        
        # Runtime information
        st.subheader("Runtime Information")
        
        info_cols = st.columns(2)
        
        with info_cols[0]:
            st.write("**Session State Variables:**")
            session_info = {k: v for k, v in st.session_state.items() if k not in ['access_token', 'products', 'current_product']}
            st.write(session_info)
        
        with info_cols[1]:
            st.write("**Version Information:**")
            st.write(f"- Streamlit: {st.__version__}")
            st.write("- Requests: " + requests.__version__)
            st.write("- Pandas: " + pd.__version__)
            
        # Toggle detailed debug mode
        st.session_state.debug_mode = st.checkbox("Enable detailed debug logging", value=st.session_state.debug_mode)
        
        # Clear session state option
        st.subheader("Reset Application")
        clear_cols = st.columns([3, 1])
        
        with clear_cols[0]:
            st.warning("This will reset all session data including your connection, templates, and product cache.")
        
        with clear_cols[1]:
            if st.button("Reset App", type="primary", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("Application has been reset. Refreshing...")
                st.rerun()

# Help tab
elif st.session_state.active_tab == "help":
    st.header("Help & Documentation")
    
    # Create tabs for different help sections
    help_tabs = st.tabs([
        "🔧 App Guide", 
        "🔌 Connection Help", 
        "📝 Template Help", 
        "🖼️ Alt Text Guide", 
        "❓ FAQ"
    ])
    
    # App Guide tab
    with help_tabs[0]:
        st.markdown(guides["app_user_guide"])
        st.markdown(guides["getting_started"])
    
    # Connection Help tab
    with help_tabs[1]:
        st.markdown(guides["connection_guide"])
        st.markdown(guides["troubleshooting"])
    
    # Template Help tab
    with help_tabs[2]:
        st.markdown(guides["template_guide"])
    
    # Alt Text Guide tab
    with help_tabs[3]:
        st.markdown(guides["alt_text_guide"])
    
    # FAQ tab
    with help_tabs[4]:
        st.markdown(guides["faq"])
    
    # Contact information
    st.markdown("---")
    st.subheader("Need More Help?")
    st.markdown("""
    If you're experiencing issues not covered in the documentation, please reach out for support:
    
    - Check the [Shopify API documentation](https://shopify.dev/docs/admin-api) for reference
    - Review the [Streamlit documentation](https://docs.streamlit.io/) for app functionality
    - Refer to the [Alt Text best practices](https://www.w3.org/WAI/tutorials/images/decision-tree/) from W3C
    """)
    
    # Version information
    st.markdown("---")
    st.caption("Shopify Alt Text Manager v1.0")
    st.caption(f"Running on Streamlit {st.__version__}")

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
                                    shop_name = response_json['shop'].get('name', 'Shopify store')
                                    st.session_state.shop_name = shop_name
                                    st.success(f"✅ Connected to {shop_name} successfully!")
                                else:
                                    st.success("✅ Connected to Shopify successfully!")
                            except:
                                st.success("✅ Connected to Shopify successfully!")
                            
                            # Just rerun to refresh the UI, don't redirect
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
        with st.expander("📘 Connection Guide", expanded=not st.session_state.compact_mode):
            st.markdown(guides["connection_guide"])
    
    with col2:
        with st.expander("🔍 Troubleshooting", expanded=not st.session_state.compact_mode):
            st.markdown(guides["troubleshooting"])


def load_sample_templates():
    """Load sample templates for alt text and filenames"""
    sample_alt_text_templates = [
        {
            "id": "template_basic",
            "name": "Basic Product Description",
            "template": "{title} by {vendor}, {type} product"
        },
        {
            "id": "template_seo",
            "name": "SEO Optimized",
            "template": "Buy {title} from {vendor} - Premium {type} product"
        },
        {
            "id": "template_detailed",
            "name": "Detailed with Color",
            "template": "{color} {title} - {vendor} {type}, a quality product from {store}"
        },
        {
            "id": "template_minimal",
            "name": "Minimal",
            "template": "{title} - {vendor}"
        },
        {
            "id": "template_professional",
            "name": "Professional",
            "template": "Professional {type}: {title} by {vendor}"
        }
    ]
    
    sample_filename_templates = [
        {
            "id": "filename_template_basic",
            "name": "Basic Filename",
            "template": "{vendor}-{title}-{index}"
        },
        {
            "id": "filename_template_seo",
            "name": "SEO Filename",
            "template": "{type}-{title}-{vendor}-product-{id}"
        },
        {
            "id": "filename_template_color",
            "name": "Color Focused",
            "template": "{color}-{title}-{vendor}-{id}"
        },
        {
            "id": "filename_template_store",
            "name": "Store Branded",
            "template": "{store}-{type}-{title}-{id}"
        },
        {
            "id": "filename_template_skus",
            "name": "SKU Based",
            "template": "{sku}-product-image-{index}"
        }
    ]
    
    return sample_alt_text_templates, sample_filename_templates

def initialize_templates():
    """Initialize templates if they don't exist"""
    if 'templates' not in st.session_state:
        st.session_state.templates = []
    if 'filename_templates' not in st.session_state:
        st.session_state.filename_templates = []
    
    # Load samples if no templates exist
    if len(st.session_state.templates) == 0 and len(st.session_state.filename_templates) == 0:
        sample_alt_text, sample_filenames = load_sample_templates()
        st.session_state.templates = sample_alt_text
        st.session_state.filename_templates = sample_filenames

def improved_template_management():
    """Improved template management interface"""
    st.header("Template Management")
    
    # Initialize templates with samples if needed
    initialize_templates()
    
    # Add template guide
    with st.expander("📝 Template Guide", expanded=False):
        st.markdown(guides["template_guide"])
    
    # Create tabs for Alt Text Templates and Filename Templates
    template_tabs = st.tabs(["Alt Text Templates", "Filename Templates"])
    
    # Alt Text Templates tab
    with template_tabs[0]:
        # Template creation form in a card-like container
        st.markdown('<div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">', unsafe_allow_html=True)
        st.subheader("Create New Alt Text Template")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            template_name = st.text_input(
                "Template Name", 
                key="new_alt_text_template_name",
                placeholder="e.g., Basic Product Template"
            )
            
            template_string = st.text_area(
                "Template String",
                placeholder="e.g., {title} - {vendor} product",
                key="new_alt_text_template_string",
                height=80
            )
            st.caption("Available Variables: {title}, {vendor}, {type}, {tags}, {store}, {sku}, {color}, {brand}, {category}, {index}, {id}")
        
        with col2:
            st.write("&nbsp;")  # Space for alignment
            st.write("&nbsp;")  # Space for alignment
            if st.button("Add Template", type="primary", use_container_width=True):
                if template_name and template_string:
                    new_template = {
                        "id": f"template_{len(st.session_state.templates) + 1}_{int(time.time())}",
                        "name": template_name,
                        "template": template_string
                    }
                    st.session_state.templates.append(new_template)
                    st.success(f"Template '{template_name}' added successfully!")
                    st.experimental_rerun()
                else:
                    st.error("Please provide both template name and string")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display existing alt text templates
        st.subheader("Your Alt Text Templates")
        
        # Export/Import templates button
        export_col, import_col = st.columns(2)
        with export_col:
            if st.button("Export Templates", use_container_width=True):
                # Convert to JSON and create a download link
                templates_json = json.dumps(st.session_state.templates, indent=2)
                b64 = base64.b64encode(templates_json.encode()).decode()
                href = f'<a href="data:application/json;base64,{b64}" download="alt_text_templates.json">Download Templates JSON</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        with import_col:
            uploaded_file = st.file_uploader("Import Templates", type="json", key="import_alt_text_templates")
            if uploaded_file is not None:
                try:
                    imported_templates = json.load(uploaded_file)
                    if isinstance(imported_templates, list):
                        st.session_state.templates = imported_templates
                        st.success(f"Successfully imported {len(imported_templates)} templates")
                        st.experimental_rerun()
                    else:
                        st.error("Invalid template format")
                except Exception as e:
                    st.error(f"Error importing templates: {str(e)}")
        
        if st.session_state.templates:
            # Preview section
            if st.session_state.products:
                st.subheader("Template Preview")
                preview_product = st.selectbox(
                    "Select a product for preview",
                    options=[p["title"] for p in st.session_state.products],
                    index=0
                )
                
                # Find the selected product
                product = next((p for p in st.session_state.products if p["title"] == preview_product), None)
                
                if product:
                    # Show preview for all templates with this product
                    preview_cols = st.columns(2)
                    for i, template in enumerate(st.session_state.templates):
                        col_idx = i % 2
                        with preview_cols[col_idx]:
                            st.markdown(f"<div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>", unsafe_allow_html=True)
                            st.write(f"**{template['name']}**")
                            preview = preview_template(template["template"], product)
                            st.code(preview)
                            st.markdown("</div>", unsafe_allow_html=True)
            
            # Display templates with edit/delete options
            for i, template in enumerate(st.session_state.templates):
                st.markdown(f"<div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px; display: flex; align-items: center;'>", unsafe_allow_html=True)
                
                # Use columns for layout
                col1, col2, col3 = st.columns([3, 5, 2])
                
                with col1:
                    st.write(f"**{template['name']}**")
                
                with col2:
                    st.code(template['template'], language="markdown")
                
                with col3:
                    button_cols = st.columns(2)
                    with button_cols[0]:
                        if st.button("Edit", key=f"edit_alt_{template['id']}"):
                            st.session_state.edit_template_id = template["id"]
                            st.session_state.edit_template_name = template["name"]
                            st.session_state.edit_template_string = template["template"]
                            st.experimental_rerun()
                    
                    with button_cols[1]:
                        if st.button("Delete", key=f"delete_alt_{template['id']}"):
                            # Confirm deletion
                            st.session_state.templates.pop(i)
                            st.experimental_rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Edit template form (conditionally displayed)
            if "edit_template_id" in st.session_state:
                st.markdown('<div style="background-color: #e7f0fd; padding: 15px; border-radius: 8px; margin: 20px 0;">', unsafe_allow_html=True)
                st.subheader("Edit Template")
                
                edit_col1, edit_col2 = st.columns([3, 1])
                with edit_col1:
                    edited_name = st.text_input(
                        "Template Name", 
                        value=st.session_state.edit_template_name,
                        key="edit_template_name_input"
                    )
                    
                    edited_template = st.text_area(
                        "Template String",
                        value=st.session_state.edit_template_string,
                        key="edit_template_string_input",
                        height=80
                    )
                
                with edit_col2:
                    st.write("&nbsp;")  # Space for alignment
                    st.write("&nbsp;")  # Space for alignment
                    save_col, cancel_col = st.columns(2)
                    
                    with save_col:
                        if st.button("Save", type="primary", use_container_width=True):
                            if edited_name and edited_template:
                                # Find and update the template
                                for idx, tmpl in enumerate(st.session_state.templates):
                                    if tmpl["id"] == st.session_state.edit_template_id:
                                        st.session_state.templates[idx]["name"] = edited_name
                                        st.session_state.templates[idx]["template"] = edited_template
                                        break
                                
                                # Clear edit state
                                del st.session_state.edit_template_id
                                del st.session_state.edit_template_name
                                del st.session_state.edit_template_string
                                st.success("Template updated successfully!")
                                st.experimental_rerun()
                    
                    with cancel_col:
                        if st.button("Cancel", use_container_width=True):
                            # Clear edit state
                            del st.session_state.edit_template_id
                            del st.session_state.edit_template_name
                            del st.session_state.edit_template_string
                            st.experimental_rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No alt text templates created yet. Use the form above to create your first template.")
    
    # Similar structure for Filename Templates tab (abbreviated for brevity)
    with template_tabs[1]:
        # Create similar UI for filename templates
        st.markdown('<div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">', unsafe_allow_html=True)
        st.subheader("Create New Filename Template")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filename_template_name = st.text_input(
                "Template Name", 
                key="new_filename_template_name",
                placeholder="e.g., Basic Filename Template"
            )
            
            filename_template_string = st.text_input(
                "Template String", 
                placeholder="e.g., {vendor}-{title}-{index}",
                key="new_filename_template_string"
            )
            
            st.caption("Available Variables: {title}, {vendor}, {type}, {tags}, {store}, {sku}, {color}, {index}, {id}")
            st.caption("Note: Include {index} or {id} to ensure unique filenames. Extensions will be added automatically if missing.")
        
        with col2:
            st.write("&nbsp;")  # Space for alignment
            st.write("&nbsp;")  # Space for alignment
            if st.button("Add Template", type="primary", use_container_width=True, key="add_filename_template"):
                if filename_template_name and filename_template_string:
                    new_template = {
                        "id": f"filename_template_{len(st.session_state.filename_templates) + 1}_{int(time.time())}",
                        "name": filename_template_name,
                        "template": filename_template_string
                    }
                    st.session_state.filename_templates.append(new_template)
                    st.success(f"Template '{filename_template_name}' added successfully!")
                    st.experimental_rerun()
                else:
                    st.error("Please provide both template name and string")
        
        st.markdown('</div>', unsafe_allow_html=True)

def improved_product_management():
    """Improved product management with bulk operations"""
    st.header("Product Management")
    
    # Product fetch options
    with st.expander("Fetch Products", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
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
        
        with col3:
            st.write("&nbsp;")
            refresh_products = st.checkbox("Auto-refresh", value=False)
    
    # Display products if available
    if st.session_state.products:
        # Add bulk operations section
        with st.expander("Bulk Operations", expanded=True):
            st.subheader("Bulk Update Alt Text and Filenames")
            
            # Product selection method
            selection_method = st.radio(
                "Select products by:",
                options=["All Products", "Filter by Vendor", "Filter by Type", "Select Individually"],
                horizontal=True
            )
            
            # Build the list of selected products based on the method
            selected_products = []
            
            if selection_method == "All Products":
                selected_products = st.session_state.products
                st.write(f"Selected {len(selected_products)} products")
            
            elif selection_method == "Filter by Vendor":
                # Get unique vendors
                vendors = sorted(list(set(p["vendor"] for p in st.session_state.products)))
                selected_vendor = st.selectbox("Select Vendor", options=vendors)
                selected_products = [p for p in st.session_state.products if p["vendor"] == selected_vendor]
                st.write(f"Selected {len(selected_products)} products from vendor '{selected_vendor}'")
            
            elif selection_method == "Filter by Type":
                # Get unique product types
                product_types = sorted(list(set(p["type"] for p in st.session_state.products)))
                selected_type = st.selectbox("Select Product Type", options=product_types)
                selected_products = [p for p in st.session_state.products if p["type"] == selected_type]
                st.write(f"Selected {len(selected_products)} products of type '{selected_type}'")
            
            elif selection_method == "Select Individually":
                # Create a multiselect with product titles
                product_titles = [p["title"] for p in st.session_state.products]
                selected_titles = st.multiselect("Select Products", options=product_titles)
                selected_products = [p for p in st.session_state.products if p["title"] in selected_titles]
                st.write(f"Selected {len(selected_products)} products")
            
            # Only show template application if products are selected
            if selected_products:
                st.write("---")
                
                # Template selection for bulk update
                template_tabs = st.tabs(["Alt Text Templates", "Filename Templates"])
                
                # Alt Text Templates tab
                with template_tabs[0]:
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
                            
                            # Preview selected template on first product
                            if selected_template and selected_products:
                                template = next((t for t in st.session_state.templates if t["id"] == selected_template), None)
                                if template:
                                    preview = preview_template(template["template"], selected_products[0])
                                    st.markdown("<div style='background-color: #f0f0f0; padding: 8px; border-radius: 4px; margin-top: 8px; min-height: 40px;'>", unsafe_allow_html=True)
                                    st.write(f"Preview on '{selected_products[0]['title']}': {preview}")
                                    st.markdown("</div>", unsafe_allow_html=True)
                        else:
                            st.info("No alt text templates available. Create templates in the Templates tab.")
                            selected_template = None
                    
                    with col2:
                        st.write("&nbsp;")  # Space for alignment
                        if selected_template and st.button("Apply to All Selected", use_container_width=True, type="primary"):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            # Count the total images to process
                            total_images = sum(len(p["images"]) for p in selected_products)
                            processed_images = 0
                            
                            for product_idx, product in enumerate(selected_products):
                                status_text.write(f"Processing product {product_idx+1}/{len(selected_products)}: {product['title']}")
                                
                                for image in product["images"]:
                                    # Apply template to this image
                                    apply_template_to_image(product, image["id"], selected_template)
                                    processed_images += 1
                                    # Update progress
                                    progress_bar.progress(processed_images / total_images)
                            
                            status_text.success(f"✅ Alt text template applied to {processed_images} images across {len(selected_products)} products")
                
                # Filename Templates tab
                with template_tabs[1]:
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
                            
                            # Preview selected template on first product
                            if selected_filename_template and selected_products:
                                template = next((t for t in st.session_state.filename_templates if t["id"] == selected_filename_template), None)
                                if template:
                                    preview = preview_template(template["template"], selected_products[0])
                                    if "." not in preview:
                                        preview += ".jpg"
                                    st.markdown("<div style='background-color: #f0f0f0; padding: 8px; border-radius: 4px; margin-top: 8px; min-height: 40px;'>", unsafe_allow_html=True)
                                    st.write(f"Preview on '{selected_products[0]['title']}': {preview}")
                                    st.markdown("</div>", unsafe_allow_html=True)
                        else:
                            st.info("No filename templates available. Create templates in the Templates tab.")
                            selected_filename_template = None
                    
                    with col2:
                        st.write("&nbsp;")  # Space for alignment
                        if selected_filename_template and st.button("Apply to All Selected", use_container_width=True, type="primary", key="bulk_apply_filename"):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            # Count the total images to process
                            total_images = sum(len(p["images"]) for p in selected_products)
                            processed_images = 0
                            
                            for product_idx, product in enumerate(selected_products):
                                status_text.write(f"Processing product {product_idx+1}/{len(selected_products)}: {product['title']}")
                                
                                for image in product["images"]:
                                    # Apply template to this image
                                    apply_filename_template_to_image(product, image["id"], selected_filename_template)
                                    processed_images += 1
                                    # Update progress
                                    progress_bar.progress(processed_images / total_images)
                            
                            status_text.success(f"✅ Filename template applied to {processed_images} images across {len(selected_products)} products")
        
        # Product display with improved search and filtering
        st.subheader("Product List")
        
        # Search and filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_query = st.text_input("Search Products", value=st.session_state.search_query)
            st.session_state.search_query = search_query
        
        with col2:
            # Vendor filter
            vendors = ["All Vendors"] + sorted(list(set(p["vendor"] for p in st.session_state.products)))
            selected_vendor_filter = st.selectbox("Filter by Vendor", options=vendors, index=0)
        
        with col3:
            # Sort options
            sort_options = ["Name (A-Z)", "Name (Z-A)", "Vendor", "Type", "Alt Text Coverage (Low to High)", "Alt Text Coverage (High to Low)"]
            sort_by = st.selectbox("Sort By", options=sort_options, index=0)
        
        # Filter products
        filtered_products = st.session_state.products
        
        # Apply search filter
        if search_query:
            filtered_products = [p for p in filtered_products if search_query.lower() in p["title"].lower()]
        
        # Apply vendor filter
        if selected_vendor_filter != "All Vendors":
            filtered_products = [p for p in filtered_products if p["vendor"] == selected_vendor_filter]
        
        # Sort products
        if sort_by == "Name (A-Z)":
            filtered_products = sorted(filtered_products, key=lambda p: p["title"])
        elif sort_by == "Name (Z-A)":
            filtered_products = sorted(filtered_products, key=lambda p: p["title"], reverse=True)
        elif sort_by == "Vendor":
            filtered_products = sorted(filtered_products, key=lambda p: p["vendor"])
        elif sort_by == "Type":
            filtered_products = sorted(filtered_products, key=lambda p: p["type"])
        elif "Alt Text Coverage" in sort_by:
            # Calculate coverage for sorting
            for product in filtered_products:
                total_images = len(product["images"])
                images_with_alt = sum(1 for img in product["images"] if img.get("alt"))
                product["_alt_coverage"] = (images_with_alt / total_images * 100) if total_images > 0 else 0
            
            if "Low to High" in sort_by:
                filtered_products = sorted(filtered_products, key=lambda p: p["_alt_coverage"])
            else:
                filtered_products = sorted(filtered_products, key=lambda p: p["_alt_coverage"], reverse=True)
        
        # Display product count
        st.write(f"Showing {len(filtered_products)} products")
        
        if filtered_products:
            # Create a more compact and informative product grid
            product_cols = st.columns(3)
            
            for i, product in enumerate(filtered_products):
                col_idx = i % 3
                
                with product_cols[col_idx]:
                    # Calculate coverage
                    total_images = len(product["images"])
                    images_with_alt = sum(1 for img in product["images"] if img.get("alt"))
                    images_with_filename = sum(1 for img in product["images"] if img.get("applied_filename_template"))
                    alt_coverage = (images_with_alt / total_images * 100) if total_images > 0 else 0
                    filename_coverage = (images_with_filename / total_images * 100) if total_images > 0 else 0
                    
                    # Product card
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 15px;">
                        <h4 style="margin-top: 0;">{product['title']}</h4>
                        <p><strong>Vendor:</strong> {product['vendor']}</p>
                        <p><strong>Type:</strong> {product['type']}</p>
                        <p><strong>Images:</strong> {total_images}</p>
                        <div>
                            <strong>Alt Text:</strong> {images_with_alt}/{total_images} ({alt_coverage:.1f}%)
                            <div style="height: 8px; background-color: #e9ecef; border-radius: 4px; margin: 5px 0;">
                                <div style="height: 8px; width: {alt_coverage}%; background-color: #4CAF50; border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div>
                            <strong>Filenames:</strong> {images_with_filename}/{total_images} ({filename_coverage:.1f}%)
                            <div style="height: 8px; background-color: #e9ecef; border-radius: 4px; margin: 5px 0;">
                                <div style="height: 8px; width: {filename_coverage}%; background-color: #2196F3; border-radius: 4px;"></div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("View Details", key=f"view_{product['id']}", use_container_width=True):
                            st.session_state.current_product = product
                            # Add to recent products list
                            if product["id"] in st.session_state.recent_products:
                                st.session_state.recent_products.remove(product["id"])
                            st.session_state.recent_products.append(product["id"])
                            st.rerun()
                    
                    with col2:
                        if st.button("Quick Edit", key=f"quick_{product['id']}", use_container_width=True):
                            st.session_state.quick_edit_product = product
                            st.rerun()
        else:
            st.info("No products match your search criteria")
    else:
        st.info("No products loaded. Click 'Fetch Products' to import products from your Shopify store.")
    
    # Quick Edit Modal (if a product is selected for quick edit)
    if hasattr(st.session_state, 'quick_edit_product') and st.session_state.quick_edit_product:
        product = st.session_state.quick_edit_product
        
        # Create a modal-like UI
        st.markdown("""
        <style>
        .quick-edit-modal {
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="quick-edit-modal">', unsafe_allow_html=True)
        
        # Header with close button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Quick Edit: {product['title']}")
        with col2:
            if st.button("Close", use_container_width=True):
                del st.session_state.quick_edit_product
                st.rerun()
        
        # Display first image
        if product["images"]:
            try:
                response = requests.get(product["images"][0]["src"])
                img = Image.open(BytesIO(response.content))
                st.image(img, width=200)
            except:
                st.image("https://via.placeholder.com/200x200?text=No+Image")
        
        # Template application tabs
        edit_tabs = st.tabs(["Apply Alt Text", "Apply Filenames", "Image Preview"])
        
        with edit_tabs[0]:
            if st.session_state.templates:
                template_options = {t["id"]: t["name"] for t in st.session_state.templates}
                selected_template = st.selectbox(
                    "Select Alt Text Template",
                    options=list(template_options.keys()),
                    format_func=lambda x: template_options[x],
                    key="quick_alt_template"
                )
                
                # Preview selected template
                if selected_template:
                    template = next((t for t in st.session_state.templates if t["id"] == selected_template), None)
                    if template:
                        st.write("**Preview:**")
                        for i, image in enumerate(product["images"][:3]):  # Show first 3 images
                            preview = preview_template(template["template"], product, i)
                            st.code(f"Image {i+1}: {preview}")
                
                # Apply to all button
                if st.button("Apply to All Images", type="primary", use_container_width=True):
                    with st.spinner("Applying template..."):
                        for image in product["images"]:
                            apply_template_to_image(product, image["id"], selected_template)
                        st.success("✅ Template applied to all images")
            else:
                st.info("No templates created yet. Go to the Templates tab to create some.")
        
        with edit_tabs[1]:
            if st.session_state.filename_templates:
                filename_template_options = {t["id"]: t["name"] for t in st.session_state.filename_templates}
                selected_filename_template = st.selectbox(
                    "Select Filename Template",
                    options=list(filename_template_options.keys()),
                    format_func=lambda x: filename_template_options[x],
                    key="quick_filename_template"
                )
                
                # Preview selected template
                if selected_filename_template:
                    template = next((t for t in st.session_state.filename_templates if t["id"] == selected_filename_template), None)
                    if template:
                        st.write("**Preview:**")
                        for i, image in enumerate(product["images"][:3]):  # Show first 3 images
                            preview = preview_template(template["template"], product, i)
                            if "." not in preview:
                                preview += ".jpg"
                            st.code(f"Image {i+1}: {preview}")
                
                # Apply to all button
                if st.button("Apply to All Images", type="primary", use_container_width=True, key="apply_all_filenames"):
                    with st.spinner("Applying template..."):
                        for image in product["images"]:
                            apply_filename_template_to_image(product, image["id"], selected_filename_template)
                        st.success("✅ Template applied to all images")
            else:
                st.info("No filename templates created yet. Go to the Templates tab to create some.")
        
        with edit_tabs[2]:
            # Display all images in a grid with minimal info
            image_cols = st.columns(3)
            for i, image in enumerate(product["images"]):
                col_idx = i % 3
                with image_cols[col_idx]:
                    try:
                        response = requests.get(image["src"])
                        img = Image.open(BytesIO(response.content))
                        st.image(img, width=150)
                    except:
                        st.image("https://via.placeholder.com/150x150?text=No+Image", width=150)
                    
                    # Show current alt text and filename
                    st.caption(f"**Alt:** {image.get('alt', 'None')[:50]}{'...' if len(image.get('alt', '')) > 50 else ''}")
                    st.caption(f"**File:** {image.get('filename', 'Default')}")
        
        st.markdown('</div>', unsafe_allow_html=True)
