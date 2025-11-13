"""MCP (Model Context Protocol) servers for workflow automation"""

from .email_server import EmailMCPServer, email_mcp
from .api_server import APIMCPServer, api_mcp

__all__ = ["EmailMCPServer", "email_mcp", "APIMCPServer", "api_mcp"]

