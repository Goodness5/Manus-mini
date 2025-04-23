from typing import Optional
from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.sandbox import SandboxToolsBase, Sandbox

class SandboxExposeTool(SandboxToolsBase):
    """Tool for exposing and retrieving preview URLs for sandbox ports."""

    def __init__(self, sandbox: Sandbox):
        super().__init__(sandbox)
        self.workspace_path = "/workspace"

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "expose_port",
            "description": "Expose a port from the sandbox environment to the public internet and get its preview URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "description": "The port number to expose. Must be between 1 and 65535.",
                        "minimum": 1,
                        "maximum": 65535
                    }
                },
                "required": ["port"]
            }
        }
    })
    @xml_schema(
        tag_name="expose-port",
        mappings=[
            {"param_name": "port", "node_type": "content", "path": "."}
        ],
        example='''
        <!-- Example: Expose a web server running on port 8000 -->
        <expose-port>
        8000
        </expose-port>
        '''
    )
    async def expose_port(self, port: int) -> ToolResult:
        try:
            # Convert port to integer if it's a string
            port = int(port)
            
            # Validate port number
            if not 1 <= port <= 65535:
                return self.fail_response(f"Invalid port number: {port}. Must be between 1 and 65535.")

            # Use E2B's port exposure functionality
            try:
                url = await self.sandbox.session.expose_port(port)
                
                return self.success_response({
                    "url": url,
                    "port": port,
                    "message": f"Successfully exposed port {port}. Access the service at: {url}"
                })
                
            except Exception as e:
                return self.fail_response(f"Failed to expose port {port}: {str(e)}")
                
        except ValueError:
            return self.fail_response(f"Invalid port number: {port}. Must be a valid integer between 1 and 65535.")
        except Exception as e:
            return self.fail_response(f"Error exposing port {port}: {str(e)}")
