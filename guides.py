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

Templates allow you to create reusable patterns for your product images.

### Available Variables

- `{title}` - The product title
- `{vendor}` or `{brand}` - The product vendor/brand
- `{type}` or `{category}` - The product type/category
- `{tags}` - The product tags (comma separated)
- `{store}` - Your store name
- `{sku}` - Product SKU codes (if available)
- `{color}` - Detected color from product title
- `{index}` - Image index number (useful for filenames)
- `{id}` - A unique ID to prevent duplicate filenames

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

**Template with store and color:**
```
{color} {title} from {store} - {sku}
```

**Filename template examples:**
```
{vendor}-{title}-{index}
{store}-{type}-{color}-{id}
{sku}-product-image-{index}
```

### Best Practices

1. **Keep it concise** - Aim for 8-10 words for alt text
2. **Be descriptive** - Include key product details
3. **Use natural language** - Write for humans, not just search engines
4. **Avoid keyword stuffing** - It can hurt your SEO
5. **Include brand/vendor** - This improves searchability
6. **For filenames** - Use hyphens instead of spaces, keep it lowercase
7. **Prevent duplicates** - Use `{index}` or `{id}` in filename templates
""",

        # App User Guide
        "app_user_guide": """
# Shopify Alt Text Manager - User Guide

This app helps you efficiently manage alt text and filenames for your Shopify product images using customizable templates.

## Main Features

1. **Template-Based Generation**
   - Create reusable templates with variables like {title}, {vendor}, etc.
   - Apply templates to individual images or in bulk
   - Templates work for both alt text and filenames

2. **Product Management**
   - Import products directly from your Shopify store
   - Filter and search products easily
   - Select specific products to work with

3. **Image Management**
   - View all product images in an organized grid
   - See real-time previews of generated text
   - Track alt text coverage with detailed metrics
   - Rename image files using templates

## Workflow

1. **Connect your Shopify store** (Configuration tab in sidebar)
2. **Create templates** (Templates tab in sidebar)
3. **Import products** (Products tab)
4. **Apply templates** to product images (Product Detail tab)
5. **Sync changes** back to your Shopify store

## Why Alt Text and Proper Filenames Matter

- **Accessibility**: Helps visually impaired users understand your images
- **SEO**: Improves image search visibility and ranking
- **Organization**: Well-named files make inventory management easier
- **User Experience**: Provides context when images fail to load
""",

        # Getting Started Guide
        "getting_started": """
### How to Get Started

1. **Connect Your Shopify Store**
   * Get your Shopify Admin API credentials from your Shopify admin
   * Enter your Shop URL and Access Token in the sidebar

2. **Create Templates**
   * Switch to the Templates tab
   * Create templates for both alt text and filenames
   * Use variables like {title}, {vendor}, {index}, etc.

3. **Manage Product Images**
   * Import products from your store
   * Apply templates to product images individually or in bulk
   * Update both alt text and filenames with your templates
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
5. **Selective Fetching** - Choose specific products to work with

### Tips for Efficient Management

- **Import Products First** - Click "Fetch Products" to import your products from Shopify
- **Use Search** - For stores with many products, use the search function to find specific items
- **Monitor Coverage** - The "Coverage" column shows what percentage of images have alt text
- **Batch Process** - Work through products with the lowest coverage first
- **Use Selective Fetching** - For stores with many products, select only the ones you want to work with

### Troubleshooting

- **Products Not Loading?** Check your Shopify connection
- **Changes Not Saving?** Ensure your API token has write permissions
- **Missing Images?** Verify image URLs are accessible
""",

        # Alt Text Guide
        "alt_text_guide": """
## Image Alt Text & Filename Best Practices

Alt text provides a textual alternative to non-text content like images. Proper filenames improve organization and SEO.

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

### Filename Best Practices

- **Use hyphens** instead of spaces or underscores
- **Keep filenames lowercase** to avoid case-sensitivity issues
- **Include relevant keywords** for SEO benefits
- **Be consistent** across your product catalog
- **Add unique identifiers** like product SKUs or sequence numbers
- **Keep filenames meaningful** but reasonably short

### Examples

#### Poor Alt Text & Filenames:
- Alt: "Product image" / Filename: "DSC10234.jpg"
- Alt: "Click here to buy" / Filename: "final_image_v2.jpg"
- Alt: "" (empty) / Filename: "img_45.png"

#### Good Alt Text & Filenames:
- Alt: "Women's blue denim jacket with button closure by BrandName"
  Filename: "brandname-womens-denim-jacket-blue-001.jpg"
- Alt: "Red ceramic coffee mug with floral pattern"
  Filename: "red-ceramic-mug-floral-sk1234.jpg"
- Alt: "Stainless steel kitchen knife set with wooden handles"
  Filename: "premium-knife-set-wooden-handle-5pc-001.jpg"
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
**A:** You can use `{title}`, `{vendor}`, `{type}`, `{tags}`, `{store}`, `{sku}`, `{color}`, `{index}`, and `{id}` in your templates.

#### Q: Can I use HTML in my alt text?
**A:** No, alt text should be plain text only. HTML tags will be displayed as text.

#### Q: Is there a character limit for alt text?
**A:** While there's no strict limit, it's recommended to keep alt text under 125 characters for optimal accessibility.

#### Q: Why do I need {index} or {id} in filename templates?
**A:** These ensure unique filenames, preventing conflicts if you apply the same template to multiple images.

### Product Management

#### Q: How many products can I fetch at once?
**A:** The current implementation fetches up to 50 products at a time.

#### Q: Are my changes saved automatically?
**A:** Yes, changes are sent to Shopify in real-time when you apply a template or clear alt text/filenames.

#### Q: Can I export my alt text data?
**A:** This feature is not currently available but may be added in future updates.

#### Q: Will renaming image files affect my storefront?
**A:** No, Shopify maintains the correct URLs even when you rename the file. The visible filename is updated in your admin and for SEO purposes.

### Security

#### Q: Is my access token secure?
**A:** Your access token is stored only in your browser's session state and is not shared with any third parties. However, it's always best practice to create a token with only the permissions needed and to refresh tokens regularly.
"""
    }
    
    return guides
