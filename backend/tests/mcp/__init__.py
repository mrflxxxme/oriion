"""mcp test suite root.

Unit tests for the MCP framework + built-in tools. No live network /
database access — Redis is faked, httpx is stubbed via respx or
unittest.mock.AsyncMock. Live tests (`@pytest.mark.live`) hit real APIs
and are deselected via ``-m "not live and not integration"``.
"""
