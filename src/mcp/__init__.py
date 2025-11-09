"""MCP (Model Context Protocol) servers for workflow automation"""

from .email_server import EmailMCPServer, email_mcp

__all__ = ["EmailMCPServer", "email_mcp"]

