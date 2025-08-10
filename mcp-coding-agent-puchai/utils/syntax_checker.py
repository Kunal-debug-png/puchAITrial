"""
syntax checker for mcp code generator

validates generated python code for basic syntax correctness.
"""

import ast
from typing import Dict


def check_syntax(files: Dict[str, str]) -> Dict[str, str]:
    """check syntax of all python files in the generated project."""
    results = {}
    
    for filename, content in files.items():
        if filename.endswith('.py'):
            results[filename] = _check_python_syntax(filename, content)
        elif filename in ['requirements.txt', 'pyproject.toml', 'render.yaml']:
            results[filename] = _check_config_file(filename, content)
        else:
            results[filename] = "Non-code file"
    
    return results


def _check_python_syntax(filename: str, content: str) -> str:
    """check python file syntax using ast parsing."""
    try:
        # Parse the content as Python AST
        ast.parse(content)
        
        # Additional checks for MCP-specific requirements
        if filename == "mcp_server.py":
            return _check_mcp_requirements(content)
        
        return "Valid Python syntax"
        
    except SyntaxError as e:
        error_msg = f"Syntax error at line {e.lineno}"
        if e.msg:
            error_msg += f": {e.msg}"
        return f"ERROR: {error_msg}"
        
    except Exception:
        return "ERROR: Parse error"


def _check_mcp_requirements(content: str) -> str:
    """check mcp-specific requirements in the main server file."""
    issues = []
    
    # check required imports
    required_imports = [
        ("fastmcp", "FastMCP import missing"),
        ("mcp.types", "MCP types import missing"),
    ]
    
    for import_name, error_msg in required_imports:
        if import_name not in content:
            issues.append(error_msg)
    
    # check for required validate tool
    if "async def validate(" not in content and "@mcp.tool" in content:
        issues.append("validate() tool missing")
    
    # check for my_number usage
    if "MY_NUMBER" not in content and "validate" in content:
        issues.append("MY_NUMBER environment variable not used")
    
    # check fastmcp initialization
    if "FastMCP(" not in content:
        issues.append("FastMCP initialization missing")
    
    # check main function
    if "if __name__ ==" not in content and "async def main(" not in content:
        issues.append("Main execution block missing")
    
    if issues:
        return f"Valid syntax, WARNING: MCP issues: {'; '.join(issues)}"
    else:
        return "Valid Python syntax and MCP compliance"


def _check_config_file(filename: str, content: str) -> str:
    """check configuration files for basic structure."""
    if filename == "requirements.txt":
        return _check_requirements_file(content)
    elif filename == "pyproject.toml":
        return _check_pyproject_file(content)
    elif filename == "render.yaml":
        return _check_render_config(content)
    else:
        return "Config file"


def _check_requirements_file(content: str) -> str:
    """check requirements.txt file structure."""
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    if not lines:
        return "ERROR: Empty requirements file"
    
    # check required packages
    required_packages = ["fastmcp", "python-dotenv", "httpx"]
    missing_packages = []
    
    for package in required_packages:
        if not any(package in line for line in lines):
            missing_packages.append(package)
    
    if missing_packages:
        return f"WARNING: Missing packages: {', '.join(missing_packages)}"
    
    # check invalid lines
    invalid_lines = []
    for i, line in enumerate(lines, 1):
        if not (
            line.startswith('#') or  # Comment
            '==' in line or '>' in line or '<' in line or  # Version specifier
            line.replace('-', '').replace('_', '').replace('[', '').replace(']', '').replace('.', '').isalnum()  # Package name
        ):
            invalid_lines.append(f"line {i}")
    
    if invalid_lines:
        return f"WARNING: Suspicious lines: {', '.join(invalid_lines)}"
    
    return f"Valid requirements ({len(lines)} packages)"


def _check_pyproject_file(content: str) -> str:
    """check pyproject.toml file structure."""
    required_sections = ["[project]", "[build-system]"]
    missing_sections = []
    
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        return f"WARNING: Missing sections: {', '.join(missing_sections)}"
    
    # check required fields
    required_fields = ["name", "version", "description"]
    missing_fields = []
    
    for field in required_fields:
        if f'{field} =' not in content:
            missing_fields.append(field)
    
    if missing_fields:
        return f"WARNING: Missing fields: {', '.join(missing_fields)}"
    
    return "Valid pyproject.toml"


def _check_render_config(content: str) -> str:
    """check render.yaml configuration."""
    required_fields = ["services:", "type:", "env:", "buildCommand:", "startCommand:"]
    missing_fields = []
    
    for field in required_fields:
        if field not in content:
            missing_fields.append(field)
    
    if missing_fields:
        return f"WARNING: Missing fields: {', '.join(missing_fields)}"
    
    # check python environment
    if "env: python" not in content:
        return "WARNING: Not configured for Python"
    
    # check proper start command
    if "python" not in content.lower() or "start" not in content.lower():
        return "WARNING: Start command may be incorrect"
    
    return "Valid Render configuration"
