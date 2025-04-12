# Shopify Alt Text Manager

A Streamlit application for managing alt text on Shopify product images using customizable templates.

## Features

- **Shopify Integration**: Direct connection to your Shopify store using the Admin API
- **Product Management**: Import and manage your Shopify products
- **Template System**: Create reusable alt text templates with variables
- **Image Management**: Apply templates to individual or all product images
- **Dashboard**: Track alt text coverage and recent products

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   streamlit run app.py
   ```

## Usage

1. **Connect Your Shopify Store**
   - Enter your Shopify store URL
   - Provide your Admin API access token

2. **Create Templates**
   - Create reusable alt text templates using variables like {title}, {vendor}, etc.
   
3. **Manage Products and Images**
   - Fetch products from your store
   - Apply templates to product images
   - Sync changes back to Shopify
