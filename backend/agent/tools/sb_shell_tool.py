from typing import Optional, Dict, List
from uuid import uuid4
from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.sandbox import SandboxToolsBase, Sandbox

class SandboxShellTool(SandboxToolsBase):
    """Tool for executing shell commands in an E2B sandbox environment."""

    def __init__(self, sandbox: Sandbox):
        super().__init__(sandbox)
        self._sessions: Dict[str, str] = {}  # Maps session names to session IDs
        self.workspace_path = "/workspace"  # Ensure we're always operating in /workspace

    async def _ensure_session(self, session_name: str = "default") -> str:
        """Ensure a session exists and return its ID."""
        if session_name not in self._sessions:
            session_id = str(uuid4())
            self._sessions[session_name] = session_id
        return self._sessions[session_name]

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command in the workspace directory. Commands can be chained using && for sequential execution, || for fallback execution, and | for piping output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    },
                    "folder": {
                        "type": "string",
                        "description": "Optional relative path to a subdirectory of /workspace where the command should be executed"
                    },
                    "session_name": {
                        "type": "string",
                        "description": "Optional name of the session to use. Use named sessions for related commands that need to maintain state",
                        "default": "default"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout in seconds. Increase for long-running commands",
                        "default": 60
                    }
                },
                "required": ["command"]
            }
        }
    })
    @xml_schema(
        tag_name="execute-command",
        mappings=[
            {"param_name": "command", "node_type": "content", "path": "."},
            {"param_name": "folder", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "session_name", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "timeout", "node_type": "attribute", "path": ".", "required": False}
        ],
        example='''
        <!-- Example 1: Basic command execution -->
        <execute-command>
        ls -l
        </execute-command>

        <!-- Example 2: Command in specific directory -->
        <execute-command folder="data/pdfs">
        pdftotext document.pdf -layout
        </execute-command>

        <!-- Example 3: Using named session -->
        <execute-command session_name="pdf_processing">
        pdftotext input.pdf -layout > output.txt
        </execute-command>
        '''
    )
    async def execute_command(
        self, 
        command: str, 
        folder: Optional[str] = None,
        session_name: str = "default",
        timeout: int = 60
    ) -> ToolResult:
        try:
            # Ensure session exists
            await self._ensure_session(session_name)
            
            # Set up working directory
            cwd = self.workspace_path
            if folder:
                folder = folder.strip('/')
                cwd = f"{self.workspace_path}/{folder}"
            
            # Ensure we're in the correct directory before executing the command
            command = f"cd {cwd} && {command}"
            
            # Execute command using E2B's process execution
            process = await self.sandbox.process.start(command, cwd=cwd)
            output = await process.wait(timeout=timeout)
            
            if output.exit_code == 0:
                return self.success_response({
                    "output": output.stdout,
                    "exit_code": output.exit_code,
                    "cwd": cwd
                })
            else:
                error_msg = f"Command failed with exit code {output.exit_code}"
                if output.stderr:
                    error_msg += f": {output.stderr}"
                return self.fail_response(error_msg)
                
        except Exception as e:
            return self.fail_response(f"Error executing command: {str(e)}")

    async def cleanup(self):
        """Clean up all sessions."""
        self._sessions.clear()
