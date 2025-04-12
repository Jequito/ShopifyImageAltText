"""
This module contains all the guide text and documentation content for the Shopify Alt Text Manager.
Keeping the guides separate from the main code makes it easier to update content.
"""

def load_guides():
    """Load all the guide texts and return them as a dictionary"""
    guides = {
        # Connection Guide
        "connection_guide": """
## Shopify API Connection Guide

### URL Structure for Shopify API
When connecting to the Shopify Admin API, you need to use the correct URL format:

#### Correct URL Formats
- `your-store.myshopify.com`
- `your-store`

#### Incorrect URL Formats
- `https://your-store.myshopify.com`
- `http://your-store.myshopify.com`
- `www.your-store.myshopify.com`
- `your-store.com`

### Authentication
- Private app tokens start with `shpat_`
- Custom app tokens start with `shpca_`
- Tokens need `read_products` and `write_products` scopes
""",

        # Troubleshooting Guide
        "troubleshooting": """
## Troubleshooting Connection Issues

### Common Errors and Solutions

#### "Invalid Request" Error
- **Cause**: Malformed API request
- **Solution**: Verify store URL format, ensure no typos

#### "API Key is Invalid" Error
- **Cause**: Invalid or expired access token
- **Solution**: Generate a new access token in Shopify admin

#### "Not Found" Error
- **Cause**: Store URL is incorrect
- **Solution**: Double-check your store URL, ensure it's a valid Shopify store

#### "Exceeded Rate Limit" Error
- **Cause**: Too many API requests in a short time
- **Solution**: Wait a few minutes before trying again

#### "Insufficient Permission" Error
- **Cause**: Token doesn't have the required API scopes
- **Solution**: Create a new token with the required permissions

### Generating a New API Token

1. Go to your Shopify admin panel
2. Navigate to Apps > App and sales channel settings
3. Scroll down to "Private apps" and click "Manage private apps"
4. Click "Create new private app"
5. Name your app (e.g., "Alt Text Manager")
6. Under "Admin API", ensure you enable:
   - "Read products" 
   - "Write products"
7. Click "Save" and copy the new API token
""",

        # Template Guide
        "template_guide": """
## Template Variables Guide

Templates allow you to create reusable alt text patterns for your product images.

### Available Variables

- `{title}` - The product title
- `{vendor}` - The product vendor/brand
- `{type}` - The product type
- `{tags}` - The product tags (comma separated)

### Template Examples

**Basic product description:**
```
{title} - {vendor} product
```

**Detailed product description:**
```
{title} by {vendor}, {type} product
```

**SEO-optimized template:**
```
Buy {title} from {vendor} - Premium {type}
```

### Best Practices

1. **Keep it concise** - Aim for 8-10 words
2. **Be descriptive** - Include key product details
3. **Use natural language** - Write for humans, not just search engines
4. **Avoid keyword stuffing** - It can hurt your SEO
5. **Include brand/vendor** - This improves searchability
""",

        # App User Guide
        "app_user_guide": """
# Shopify Alt Text Manager - User Guide

This app helps you efficiently manage alt text for your Shopify product images using customizable templates.

## Main Features

1. **Template-Based Alt Text Generation**
   - Create reusable templates with variables like {title}, {vendor}, etc.
   - Apply templates to individual images or in bulk

2. **Product Management**
   - Import products directly from your Shopify store
   - Filter and search products easily

3. **Image Alt Text Management**
   - View all product images in an organized grid
   - See real-time previews of generated alt text
   - Track alt text coverage with detailed metrics

## Workflow

1. **Connect your Shopify store** (Configuration tab in sidebar)
2. **Create templates** (Templates tab in sidebar)
3. **Import products** (Products tab)
4. **Apply templates** to product images (Product Detail tab)
5. **Sync changes** back to your Shopify store

## Why Alt Text Matters

- **Accessibility**: Helps visually impaired users understand your images
- **SEO**: Improves image search visibility and ranking
- **User Experience**: Provides context when images fail to load
""",

        # Getting Started Guide
        "getting_started": """
### How to Get Started

1. **Connect Your Shopify Store**
   * Get your Shopify Admin API credentials from your Shopify admin
   * Enter your Shop URL and Access Token in the sidebar

2. **Create Alt Text Templates**
   * Switch to the Templates tab in the sidebar
   * Create templates using variables like {title}, {vendor}, etc.

3. **Manage Product Images**
   * Import products from your store
   * Apply templates to product images
   * Review and sync changes back to Shopify
""",

        # Product Management Guide
        "product_management": """
## Product Management

This tab allows you to manage your Shopify products and their images.

### Key Features

1. **Fetch Products** - Import products from your Shopify store
2. **Search** - Find specific products by name
3. **Coverage Tracking** - See alt text coverage for each product
4. **Product Details** - View and edit individual product images

### Tips for Efficient Management

- **Import Products First** - Click "Fetch Products" to import your products from Shopify
- **Use Search** - For stores with many products, use the search function to find specific items
- **Monitor Coverage** - The "Coverage" column shows what percentage of images have alt text
- **Batch Process** - Work through products with the lowest coverage first

### Troubleshooting

- **Products Not Loading?** Check your Shopify connection
- **Changes Not Saving?** Ensure your API token has write permissions
- **Missing Images?** Verify image URLs are accessible
""",

        # Alt Text Guide
        "alt_text_guide": """
## Image Alt Text Best Practices

Alt text (alternative text) provides a textual alternative to non-text content like images.

### Why Alt Text Is Important

1. **Accessibility** - Helps visually impaired users who use screen readers
2. **SEO** - Improves image search ranking and overall page SEO
3. **Context** - Provides information when images can't be displayed

### Writing Effective Alt Text

- **Be Specific** - Describe what's in the image clearly
- **Keep It Concise** - Aim for 8-10 words (125 characters or less)
- **Include Keywords** - Naturally incorporate relevant keywords
- **Avoid "Image of..."** - Don't start with "picture of" or "image of"
- **Consider Context** - How does the image relate to the surrounding content?

### Examples

#### Poor Alt Text:
- "Product image"
- "DSC10234.jpg"
- "Click here to buy"

#### Good Alt Text:
- "Women's blue denim jacket with button closure by BrandName"
- "Red ceramic coffee mug with floral pattern"
- "Stainless steel kitchen knife set with wooden handles"
""",

        # FAQ Content
        "faq": """
## Frequently Asked Questions

### Connection Issues

#### Q: Why am I getting a "Not Found" error when connecting?
**A:** This usually means your shop URL is incorrect. Make sure you're using just the subdomain part (e.g., `your-store.myshopify.com` or just `your-store`).

#### Q: Why am I getting an "Invalid API Key" error?
**A:** Your access token might be invalid or expired. Generate a new access token from your Shopify admin panel.

#### Q: Do I need to configure a proxy server?
**A:** No, this Streamlit app connects directly to the Shopify API without requiring a proxy server.

### Template Usage

#### Q: What variables can I use in templates?
**A:** You can use `{title}`, `{vendor}`, `{type}`, and `{tags}` in your templates.

#### Q: Can I use HTML in my alt text?
**A:** No, alt text should be plain text only. HTML tags will be displayed as text.

#### Q: Is there a character limit for alt text?
**A:** While there's no strict limit, it's recommended to keep alt text under 125 characters for optimal accessibility.

### Product Management

#### Q: How many products can I fetch at once?
**A:** The current implementation fetches up to 50 products at a time.

#### Q: Are my changes saved automatically?
**A:** Yes, changes are sent to Shopify in real-time when you apply a template or clear alt text.

#### Q: Can I export my alt text data?
**A:** This feature is not currently available but may be added in future updates.

### Security

#### Q: Is my access token secure?
**A:** Your access token is stored only in your browser's session state and is not shared with any third parties. However, it's always best practice to create a token with only the permissions needed and to refresh tokens regularly.
"""
    }
    
    return guides
