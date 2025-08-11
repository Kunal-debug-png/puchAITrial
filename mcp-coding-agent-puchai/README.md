# Invoice PDF Generator for Puch AI

A professional AI-powered invoice PDF generator designed specifically for Puch AI. Generate beautiful, professional invoices with company branding, automatic numbering, tax calculations, and secure download links.

## Features

- Professional PDF invoice generation
- Company branding and customization
- Automatic invoice numbering
- Tax calculations (configurable)
- Terms and conditions
- Secure 24-hour download links
- Puch AI authentication integration
- Fast PDF processing with ReportLab

## How It Works

1. Provide invoice details (amount, buyer, company, date)
2. AI generates professional PDF with branding
3. PDF is saved to secure storage
4. Download link provided (expires in 24 hours)
5. Professional invoice ready for business use

## Generated Project Structure

Each generated MCP includes:

```text
generated-mcp/
├── mcp_server.py          # Main MCP implementation
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project configuration
├── render.yaml            # Render deployment config
├── render_start.py        # Render startup script
├── .env.example           # Environment variables template
├── README.md              # Usage instructions
├── DEPLOYMENT.md          # Deployment guide
└── GENERATION_INFO.json   # Generation metadata
```

## Prerequisites

- Python 3.11+
- Blaxel account and API key
- MorphLLM API key
- Phone number for Puch AI validation

## Quick Start

### 1. Configure environment

Create a `.env` file:

```env
# Puch AI Configuration
MY_NUMBER=919876543210
AUTH_TOKEN=your_bearer_token

# Blaxel Configuration
BL_WORKSPACE=your_workspace_name
BL_API_KEY=your_blaxel_api_key

# MorphLLM (Required for fast code generation)
MORPH_API_KEY=your_morph_api_key
MORPH_MODEL=morph-v2

# Application Configuration
DOWNLOAD_BASE_URL=https://your-app.onrender.com
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run locally

```bash
python mcp_generator.py
```

### 4. Connect to Puch AI

```bash
/mcp connect wss://run.blaxel.ai/your-workspace/functions/mcp-code-generator your_token
```

## Usage

### Generate MCPs with natural language

Examples:

```text
# Weather tracking
"Weather forecasting MCP with SMS alerts for severe weather"

# Flight search
"Flight search with price comparison across multiple airlines"

# Crypto tracking
"Cryptocurrency portfolio tracker with price alerts"

# AI content
"Document summarizer using OpenAI with batch processing"

# Automation
"Email automation assistant with template management"
```

### Available tools

#### Generate MCP

```python
generate_mcp("flight search with price alerts")
```

#### Get examples

```python
get_mcp_examples()
```

#### Check system status

```python
system_status()
```

## Deployment

### Blaxel deployment

This MCP Code Generator is designed to run on the Blaxel platform:

1. Install Blaxel CLI: `npm install -g @blaxel/cli`
2. Login: `bl login your-workspace`
3. Set environment variables in your Blaxel workspace
4. Deploy: `bl deploy`
5. Connect: Use the Blaxel WebSocket URL with Puch AI

### Environment variables for Blaxel

Set these in your Blaxel workspace:

- `MY_NUMBER`: Your phone number (digits only)
- `BL_WORKSPACE`: Your Blaxel workspace name
- `BL_API_KEY`: Your Blaxel API key
- `MORPH_API_KEY`: Your MorphLLM API key
- `MORPH_MODEL`: morph-v2 (default)

## API Reference

### Core tools

#### `validate()`

Required by Puch AI. Returns your phone number for authentication.

#### `generate_mcp(prompt, include_database=False, deployment_target="render")`

Generates a complete MCP from a natural-language description.

Parameters:

- `prompt` (str): Description of the desired MCP functionality
- `include_database` (bool): Whether to include database functionality
- `deployment_target` (str): `render`, `vercel`, or `custom`

Returns: Generation summary with a download link

#### `get_mcp_examples()`

Returns examples and inspiration for MCP generation.

#### `system_status()`

Reports system configuration and status.

## Supported MCP Types

### API integrations

- Weather services (OpenWeatherMap, WeatherAPI)
- Flight search (Skyscanner, Amadeus)
- Financial data (Alpha Vantage, Yahoo Finance)
- Social media (Twitter, Facebook, LinkedIn)
- AI services (OpenAI, Anthropic, Google)

### Utilities

- QR code generation
- URL shortening
- File conversion
- Email automation
- SMS notifications

### Data and analytics

- Web scraping
- Report generation
- Data analysis
- Monitoring systems

### Custom functionality

- Describe any functionality and the system will attempt to implement it

## Troubleshooting

### Common issues

Generation fails:

- Confirm Blaxel API key and workspace
- Verify MorphLLM API key
- Check internet connectivity

Download link not working:

- Links expire after 24 hours
- Regenerate the MCP if needed

Syntax errors in generated code:

- Basic validation is included
- Review the generated code before deployment
- Report persistent issues

Deployment issues:

- Check environment variables
- Review deployment logs
- Ensure all dependencies are included

### Getting help

1. Review the generated `README.md` in your MCP package
2. Read `DEPLOYMENT.md` for deployment-specific guidance
3. Verify all environment variables are correctly set
4. Check the system status using the `system_status()` tool

## Security and Privacy

- API keys are never logged or stored
- Generated code is cleaned up after download expiration
- All communication uses HTTPS
- User prompts are stored only temporarily for generation


