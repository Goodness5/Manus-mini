import os
from typing import Optional
from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox as E2BSandbox

from agentpress.tool import Tool
from utils.logger import logger
from utils.files_utils import clean_path

load_dotenv()

logger.debug("Initializing E2B sandbox configuration")

class Sandbox:
    """E2B sandbox wrapper class to maintain compatibility with existing tool structure"""
    
    def __init__(self, sandbox: E2BSandbox):
        self.session = sandbox
        self.fs = sandbox.files  # Using files instead of filesystem
        self.process = sandbox
        self.id = sandbox.id

    async def execute_command(self, command: str, cwd: Optional[str] = None) -> str:
        """Execute a command in the sandbox"""
        try:
            if cwd:
                command = f"cd {cwd} && {command}"
            execution = self.session.run_code(command)
            return execution.logs
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            raise e
    
    def get_preview_link(self, port: int):
        """Get a preview link for an exposed port"""
        return self.session.expose_port(port)

    async def execute_session_command(self, command: str, cwd: Optional[str] = None) -> str:
        """Execute a command maintaining session state"""
        return await self.execute_command(command, cwd)

def create_sandbox(password: str = None) -> Sandbox:
    """Create a new sandbox instance"""
    sandbox = E2BSandbox()  # Create a new sandbox with 5 minute timeout by default
    return Sandbox(sandbox)

async def get_or_start_sandbox(sandbox_id: str = None) -> Sandbox:
    """Create or retrieve an E2B sandbox session"""
    logger.info(f"Creating new E2B sandbox environment")
    try:
        sandbox = E2BSandbox()  # Create a new sandbox with 5 minute timeout by default
        sandbox_wrapper = Sandbox(sandbox)
        logger.info(f"Sandbox created with ID: {sandbox_wrapper.id}")
        return sandbox_wrapper
    except Exception as e:
        logger.error(f"Error creating sandbox: {str(e)}")
        raise e

class SandboxToolsBase(Tool):
    """Base class for tools that execute in an E2B sandbox environment"""
    
    def __init__(self, sandbox: Sandbox):
        super().__init__()
        self.sandbox = sandbox
        self.workspace_path = "/workspace"
        self.sandbox_id = sandbox.id
        
        logger.debug(f"Initialized SandboxToolsBase with sandbox ID: {self.sandbox_id}")

    def clean_path(self, path: str) -> str:
        """Clean and normalize a path relative to workspace"""
        cleaned_path = clean_path(path, self.workspace_path)
        logger.debug(f"Cleaned path: {path} -> {cleaned_path}")
        return cleaned_path

    async def execute_command(self, command: str, cwd: Optional[str] = None) -> str:
        """Execute a command in the sandbox"""
        return await self.sandbox.execute_command(command, cwd)
