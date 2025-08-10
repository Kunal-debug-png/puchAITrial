"""
code generator for mcp code generator

orchestrates generation of complete mcp projects using openai gpt-4.
"""

import asyncio
import logging
from typing import Dict, Callable, Optional

from .blaxel_client import BlaxelClient

logger = logging.getLogger(__name__)


class CodeGenerator:
    """generates complete mcp projects using blaxel ai."""
    
    def __init__(self):
        """init code generator."""
        self.blaxel_client = BlaxelClient()
    
    async def generate_complete_mcp(
        self, 
        prompt: str, 
        intent: Dict, 
        deployment_target: str = "render",
        generation_id: str = "unknown",
        progress_callback: Optional[Callable[[str], None]] = None,
        core_only: bool = False
    ) -> Dict[str, str]:
        """generate a complete mcp project with all necessary files."""
        def progress(msg: str):
            """send progress update."""
            logger.info(f"[{generation_id}] {msg}")
            if progress_callback:
                progress_callback(msg)
        
        if core_only:
            progress("Starting CORE MCP generation with OpenAI (essential files only)")
            # core files only: mcp_server.py, requirements.txt, .env.example, readme.md
            total_files = 4
        else:
            progress("Starting complete MCP generation with OpenAI")
            # all project files
            total_files = 6 + (2 if deployment_target == "render" else 1 if deployment_target == "vercel" else 0) + \
                         (1 if intent.get("requires_database") else 0) + \
                         (1 if intent.get("requires_scheduling") else 0) + \
                         (1 if intent.get("requires_user_data") else 0)
        
        # generate project files
        files = {}
        
        if core_only:
            # parallel generation for core files
            progress("Generating all 4 core files simultaneously...")
            
            # generate core files in parallel using asyncio.gather
            core_tasks = [
                self._generate_main_server(prompt, intent, generation_id),
                self._generate_requirements(intent, generation_id),
                self._generate_env_template(intent, generation_id),
                self._generate_readme(prompt, intent, generation_id)
            ]
            
            progress("Running parallel generation tasks...")
            core_results = await asyncio.gather(*core_tasks)
            
            # map results to filenames
            files["mcp_server.py"] = core_results[0]
            files["requirements.txt"] = core_results[1]
            files[".env.example"] = core_results[2]
            files["README.md"] = core_results[3]
            
            progress(f"Parallel generation complete - all {len(files)} core files generated!")
            
        else:
            # parallel generation for all files (complete mcp)
            progress(f"Generating all {total_files} files simultaneously...")
            
            # build list of files to generate in parallel
            all_tasks = []
            
            # core files (always needed)
            all_tasks.append(("mcp_server.py", self._generate_main_server(prompt, intent, generation_id)))
            all_tasks.append(("requirements.txt", self._generate_requirements(intent, generation_id)))
            all_tasks.append((".env.example", self._generate_env_template(intent, generation_id)))
            all_tasks.append(("README.md", self._generate_readme(prompt, intent, generation_id)))
            
            # deployment config
            if deployment_target == "render":
                all_tasks.append(("render.yaml", self._generate_render_config(intent, generation_id)))
                all_tasks.append(("render_start.py", self._generate_render_startup(generation_id)))
            elif deployment_target == "vercel":
                all_tasks.append(("vercel.json", self._generate_vercel_config(intent, generation_id)))
            
            # extended docs
            all_tasks.append(("DEPLOYMENT.md", self._generate_deployment_guide(deployment_target, intent, generation_id)))
            
            # optional modules based on intent
            if intent.get("requires_database"):
                all_tasks.append(("database.py", self._generate_database_module(intent, generation_id)))
            
            if intent.get("requires_scheduling"):
                all_tasks.append(("scheduler.py", self._generate_scheduler_module(intent, generation_id)))
            
            if intent.get("requires_user_data"):
                all_tasks.append(("USER_DATA_GUIDE.md", self._generate_user_data_guide(intent, generation_id)))
            
            # run parallel generation with asyncio.gather
            progress(f"Running parallel generation for all {len(all_tasks)} files...")
            
            # extract filenames and coroutines
            filenames = [task[0] for task in all_tasks]
            coroutines = [task[1] for task in all_tasks]
            
            # execute all generations in parallel
            results = await asyncio.gather(*coroutines)
            
            # map results to filenames
            for filename, content in zip(filenames, results):
                files[filename] = content
            
            progress(f"Parallel generation complete - all {len(files)} files generated!")
        
        progress(f"Generated {len(files)} files successfully")
        return files
    
    async def _generate_main_server(self, prompt: str, intent: Dict, generation_id: str) -> str:
        """Generate the main MCP server file."""
        instructions = f"""
Create a complete, production-ready MCP server for: {prompt}

CRITICAL PUCH AI REQUIREMENTS:
1. MANDATORY imports and setup:
   ```python
   import asyncio
   import os
   import json
   import uuid
   from typing import Annotated, Optional, Literal
   from datetime import datetime
   from dotenv import dotenv_values
   from fastmcp import FastMCP
   from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
   from mcp import ErrorData, McpError
   from mcp.server.auth.provider import AccessToken
   from mcp.types import TextContent, INVALID_PARAMS, INTERNAL_ERROR
   from pydantic import BaseModel, Field
   ```

2. MANDATORY environment variables and assertions:
   ```python
   from dotenv import dotenv_values
   env_vars = dotenv_values(".env")
   AUTH_TOKEN = env_vars.get("AUTH_TOKEN")
   MY_NUMBER = env_vars.get("MY_NUMBER")
   assert AUTH_TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
   assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"
   ```

3. MANDATORY Puch AI authentication provider:
   ```python
   class SimpleBearerAuthProvider(BearerAuthProvider):
       def __init__(self, token: str):
           k = RSAKeyPair.generate()
           super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
           self.token = token

       async def load_access_token(self, token: str) -> AccessToken | None:
           if token == self.token:
               return AccessToken(
                   token=token,
                   client_id="puch-client", 
                   scopes=["*"],
                   expires_at=None,
               )
           return None
   ```

4. MANDATORY RichToolDescription class:
   ```python
   class RichToolDescription(BaseModel):
       description: str
       use_when: str
       side_effects: str | None = None
   ```

5. MANDATORY FastMCP initialization with auth:
   ```python
   mcp = FastMCP(
       "descriptive server name",
       auth=SimpleBearerAuthProvider(AUTH_TOKEN),
   )
   ```

6. MANDATORY validate() tool (MUST be first tool):
   ```python
   @mcp.tool
   async def validate() -> str:
       return MY_NUMBER
   ```

7. MANDATORY tool description pattern:
   ```python
   ToolNameDescription = RichToolDescription(
       description="Clear description of what this tool does",
       use_when="When to use this tool",
       side_effects="What effects this tool has, if any",
   )

   @mcp.tool(description=ToolNameDescription.model_dump_json())
   async def tool_name(
       puch_user_id: Annotated[str, Field(description="Puch User Unique Identifier")],
       # other parameters...
   ) -> str | list[TextContent]:
   ```

8. MANDATORY error handling pattern:
   ```python
   try:
       # tool logic
   except Exception as e:
       raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))
   ```

9. MANDATORY main function:
   ```python
   async def main():
       print("Starting MCP server on http://0.0.0.0:8086")
       await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

   if __name__ == "__main__":
       asyncio.run(main())
   ```

FUNCTIONALITY REQUIREMENTS:
- Main purpose: {intent['main_functionality']}
- Required APIs: {intent.get('apis', [])}
- Data operations: {intent.get('data_operations', [])}
- Complexity level: {intent.get('complexity', 'intermediate')}
- User data management: {intent.get('requires_user_data', False)}
- Database required: {intent.get('requires_database', False)}

IMPLEMENTATION GUIDELINES:
- Create 3-5 tools that implement: {intent['main_functionality']}
- Each tool MUST use RichToolDescription pattern
- Use Annotated[type, Field(description="...")] for all parameters
- Return either str or list[TextContent] from tools
- Include proper error handling in all tools
- Add comprehensive docstrings
- Use type hints throughout

USER DATA MANAGEMENT (if storing/managing user-specific data):
- Include puch_user_id parameter in ALL tools that handle user data
- Use pattern: puch_user_id: Annotated[str, Field(description="Puch User Unique Identifier")]
- Implement user data separation: USER_DATA: dict[str, dict] = {{}}
- Add helper function: def _get_user_data(puch_user_id: str) -> dict
- Include user validation in all user-specific operations
- Return JSON data using: json.dumps() for structured responses

HELPER FUNCTIONS PATTERN:
```python
import json, uuid
from datetime import datetime

# Global user data storage
USER_DATA: dict[str, dict] = {{}}

def _get_user_data(puch_user_id: str) -> dict:
    if not puch_user_id:
        raise McpError(ErrorData(code=INVALID_PARAMS, message="puch_user_id is required"))
    return USER_DATA.setdefault(puch_user_id, {{}})

def _error(code, msg):
    raise McpError(ErrorData(code=code, message=msg))

def _now() -> str:
    return datetime.utcnow().isoformat()
```

TOOL RESPONSE PATTERNS:
- For structured data: return [TextContent(type="text", text=json.dumps(data))]
- For simple messages: return [TextContent(type="text", text="message")]
- Always use list[TextContent] for consistency

API INTEGRATIONS:
{chr(10).join(f"- {api}: Include httpx for HTTP calls, proper error handling and rate limiting" for api in intent.get('apis', []))}

Make the code production-ready, Puch AI compliant, and immediately deployable.
"""
        
        return await self.blaxel_client.generate_file_content(
            "mcp_server.py", instructions, generation_id
        )
    
    async def _generate_requirements(self, intent: Dict, generation_id: str) -> str:
        """Generate requirements.txt file."""
        instructions = f"""
Create a complete requirements.txt file for a Puch AI compatible MCP server with these capabilities:
- Main functionality: {intent['main_functionality']}
- Required APIs: {intent.get('apis', [])}
- Additional packages: {intent.get('python_packages', [])}

MANDATORY PUCH AI REQUIREMENTS:
- fastmcp>=2.11.2
- python-dotenv>=1.1.1
- httpx>=0.25.0
- uvicorn[standard]>=0.24.0
- pydantic>=2.0.0
- cryptography>=41.0.0  # Required for RSA key generation in auth

ADD BASED ON FUNCTIONALITY:
{chr(10).join(f"- For {api}: include appropriate client library" for api in intent.get('apis', []))}

COMMON ADDITIONAL PACKAGES:
- beautifulsoup4>=4.12.0  # For HTML parsing if needed
- markdownify>=0.11.6     # For HTML to markdown conversion
- Pillow>=10.0.0          # For image processing if needed

Include version constraints and ensure compatibility.
"""
        
        return await self.blaxel_client.generate_file_content(
            "requirements.txt", instructions, generation_id
        )
    
    async def _generate_pyproject(self, intent: Dict, generation_id: str) -> str:
        """Generate pyproject.toml file."""
        instructions = f"""
Create a pyproject.toml file for an MCP server project:
- Name: mcp-{intent['main_functionality'].lower().replace(' ', '-')}
- Description: {intent['main_functionality']}
- Requires Python >=3.11
- Include all dependencies from requirements.txt
- Use setuptools as build backend
"""
        
        return await self.blaxel_client.generate_file_content(
            "pyproject.toml", instructions, generation_id
        )
    
    async def _generate_render_config(self, intent: Dict, generation_id: str) -> str:
        """Generate render.yaml deployment configuration."""
        instructions = f"""
Create a render.yaml configuration for deploying this MCP server:
- Service type: web
- Environment: python
- Build command: pip install -r requirements.txt  
- Start command: python render_start.py
- Include all environment variables from: {intent.get('environment_vars', [])}
- Set sync: false for all API keys
- Include health check path: /health
- Add disk storage if needed for: {intent.get('data_operations', [])}
"""
        
        return await self.blaxel_client.generate_file_content(
            "render.yaml", instructions, generation_id
        )
    
    async def _generate_render_startup(self, generation_id: str) -> str:
        """Generate render_start.py startup script."""
        instructions = """
Create a render_start.py script that:
1. Sets up logging for production
2. Validates required environment variables
3. Creates necessary directories
4. Imports and runs the main MCP server
5. Includes proper error handling and exit codes
6. Adds startup status logging
"""
        
        return await self.blaxel_client.generate_file_content(
            "render_start.py", instructions, generation_id
        )
    
    async def _generate_vercel_config(self, intent: Dict, generation_id: str) -> str:
        """Generate vercel.json configuration."""
        instructions = f"""
Create a vercel.json configuration for deploying this MCP server:
- Configure for Python runtime
- Set up proper routing for MCP endpoints
- Include environment variable references
- Configure build settings
- Set up health check endpoint
"""
        
        return await self.blaxel_client.generate_file_content(
            "vercel.json", instructions, generation_id
        )
    
    async def _generate_env_template(self, intent: Dict, generation_id: str) -> str:
        """Generate .env.example template."""
        instructions = f"""
Create a .env.example file with all required environment variables for Puch AI compatibility:

MANDATORY PUCH AI VARIABLES (ALWAYS REQUIRED):
# Puch AI Authentication (REQUIRED)
AUTH_TOKEN=your_bearer_token_here
MY_NUMBER=919876543210  # Your phone number (digits only, no spaces or +)

ADDITIONAL VARIABLES FOR THIS MCP:
{chr(10).join(f"# {var.replace('_', ' ').title()}\n{var}=your_value_here" for var in intent.get('environment_vars', []) if var not in ['AUTH_TOKEN', 'MY_NUMBER'])}

INSTRUCTIONS:
# 1. Copy this file to .env
# 2. Replace all placeholder values with your actual credentials
# 3. AUTH_TOKEN: Set any secure string (e.g., "my-secret-token-123")
# 4. MY_NUMBER: Your phone number in format: country_code + number (no + or spaces)
#    Examples: 919876543210 (India), 14155552222 (US)

API KEY SOURCES:
{chr(10).join(f"# {api.upper()}: Get from {api} developer portal" for api in intent.get('apis', []))}

SECURITY NOTE:
# Never commit your .env file to version control
# Add .env to your .gitignore file
"""
        
        return await self.blaxel_client.generate_file_content(
            ".env.example", instructions, generation_id
        )
    
    async def _generate_readme(self, prompt: str, intent: Dict, generation_id: str) -> str:
        """Generate comprehensive README.md."""
        instructions = f"""
Create a comprehensive README.md for this Puch AI compatible MCP server:

PROJECT: {intent['main_functionality']}
DESCRIPTION: {prompt}

INCLUDE SECTIONS:
1. Project description and features
2. Puch AI Compatibility Notice (highlight that this is designed specifically for Puch AI)
3. Requirements and dependencies (mention cryptography for auth)
4. Installation instructions
5. Authentication Setup (detailed AUTH_TOKEN and MY_NUMBER explanation)
6. Environment variable setup with detailed explanations
7. Usage examples and tool descriptions
8. Deployment instructions for Render
9. Puch AI Connection Instructions (exact command format)
10. API documentation for each tool
11. Troubleshooting (include auth issues)
12. Security considerations

PUCH AI SPECIFIC CONTENT:
- Explain that AUTH_TOKEN and MY_NUMBER are MANDATORY
- Show exact Puch AI connection command: /mcp connect https://your-app.onrender.com/mcp/ your_auth_token
- Mention bearer token authentication requirement
- Include phone number format examples: 919876543210 (India), 14155552222 (US)
- Add troubleshooting for common Puch AI connection issues (401 errors, phone number validation, etc.)
- Emphasize that this MCP uses advanced authentication and requires proper setup

        AUTHENTICATION SECTION TEMPLATE:
        ```markdown
        ## Authentication Setup

This MCP server uses bearer token authentication required by Puch AI.

### Required Environment Variables

1. **AUTH_TOKEN**: Your secure bearer token
   - Set this to any secure string (e.g., "my-secret-token-123")
   - This will be used when connecting from Puch AI
   
2. **MY_NUMBER**: Your phone number for validation
   - Format: country_code + number (no + or spaces)
   - Examples: 919876543210 (India), 14155552222 (US)
   - This is returned by the validate() tool for Puch AI authentication
```

Make it professional, detailed, and user-friendly. Include code examples and clear step-by-step instructions.
Emphasize throughout that this is a Puch AI specific MCP with advanced authentication.
"""
        
        return await self.blaxel_client.generate_file_content(
            "README.md", instructions, generation_id
        )
    
    async def _generate_deployment_guide(self, deployment_target: str, intent: Dict, generation_id: str) -> str:
        """Generate DEPLOYMENT.md guide."""
        instructions = f"""
Create a detailed DEPLOYMENT.md guide for {deployment_target}:

INCLUDE:
1. Prerequisites and account setup
2. Step-by-step deployment process
3. Environment variable configuration
4. Post-deployment verification
5. Connecting to Puch AI
6. Monitoring and maintenance
7. Troubleshooting common issues
8. Cost considerations
9. Scaling recommendations

Target platform: {deployment_target}
Deployment notes: {intent.get('deployment_notes', '')}
"""
        
        return await self.blaxel_client.generate_file_content(
            "DEPLOYMENT.md", instructions, generation_id
        )
    
    async def _generate_database_module(self, intent: Dict, generation_id: str) -> str:
        """Generate database.py module for database functionality."""
        instructions = f"""
Create a database.py module for data persistence:

REQUIREMENTS:
- Use SQLAlchemy for ORM
- Support PostgreSQL and SQLite
- Include connection management
- Add table models for: {intent.get('data_operations', [])}
- Include CRUD operations
- Add proper error handling
- Use environment variables for connection
"""
        
        return await self.blaxel_client.generate_file_content(
            "database.py", instructions, generation_id
        )
    
    async def _generate_scheduler_module(self, intent: Dict, generation_id: str) -> str:
        """Generate scheduler.py module for scheduled tasks."""
        instructions = f"""
Create a scheduler.py module for background tasks:

REQUIREMENTS:
- Use APScheduler or similar
- Support periodic tasks
- Include task management
- Add logging for scheduled operations
- Use async/await properly
- Include error handling and retries
"""
        
        return await self.blaxel_client.generate_file_content(
            "scheduler.py", instructions, generation_id
        )
    
    async def _generate_user_data_guide(self, intent: Dict, generation_id: str) -> str:
        """Generate user data management guide."""
        instructions = f"""
Create a USER_DATA_GUIDE.md explaining the user data management patterns in this MCP:

CONTENT TO INCLUDE:
1. Explanation of puch_user_id parameter
2. User data separation patterns
3. Data storage structure examples
4. Helper function usage
5. User-specific vs global operations
6. Data persistence considerations
7. Privacy and data handling notes

PUCH AI USER MANAGEMENT:
- Every tool that manages user data includes puch_user_id parameter
- Data is automatically separated by user
- Users can only access their own data
- puch_user_id is provided automatically by Puch AI

EXAMPLE PATTERNS:
- USER_DATA: dict[str, dict] = {{}} for user separation
- _get_user_data(puch_user_id) helper function
- JSON responses for structured data
- Proper error handling for missing users/data

Make it educational and practical for developers.
"""
        
        return await self.blaxel_client.generate_file_content(
            "USER_DATA_GUIDE.md", instructions, generation_id
        )
