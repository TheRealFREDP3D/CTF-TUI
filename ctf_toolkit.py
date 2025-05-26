#!/usr/bin/env python3
"""
CTF Toolkit TUI - A Textual-based Interface for CTF Operations.

This script provides a Terminal User Interface (TUI) to assist with common
Capture The Flag (CTF) tasks. It includes features like an integrated terminal,
markdown note-taking, an AI assistant, and a plugin/tool manager.

This version is a Proof of Concept, demonstrating the core UI structure
and foundational functionality of these components.
"""

from dotenv import load_dotenv

load_dotenv()

import asyncio
import subprocess
from datetime import datetime
from typing import Optional, AsyncGenerator, Tuple, Any
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    TabbedContent, TabPane, TextArea, Static, Input, Button, 
    DataTable, Footer, Header, Markdown, Select, Label
)
from textual.binding import Binding
from textual.message import Message

from litellm import acompletion
import os

# =============================================================================
# MANAGERS - Business Logic Layer
# =============================================================================

class TerminalManager:
    """
    Manages terminal operations, including command execution and history.

    This class is responsible for running shell commands in a non-blocking way,
    capturing their stdout and stderr streams, and maintaining a history of
    executed commands.
    """
    
    def __init__(self):
        """
        Initializes the TerminalManager.
        
        Sets up an empty command history list and sets the initial current
        directory to the directory from which the script was launched.
        """
        self.history: list[dict[str, str]] = []
        self.current_dir: Path = Path.cwd()
    
    async def execute_command(self, command: str) -> AsyncGenerator[Tuple[str, Any], None]:
        """
        Executes a shell command asynchronously and yields its output incrementally.

        The output is yielded as tuples, where the first element is the stream
        type ('stdout', 'stderr', 'error', 'returncode') and the second element
        is the corresponding data.

        Args:
            command: The shell command string to execute.

        Yields:
            Tuple[str, Any]: A tuple containing the output type and the data.
                             Possible types are:
                             - ('stdout', str): A line from standard output.
                             - ('stderr', str): A line from standard error.
                             - ('error', str): An error message if an exception occurred
                                               during command setup or execution.
                             - ('returncode', int): The exit code of the command.
        
        Raises:
            RuntimeError: If the subprocess fails to provide stdout/stderr streams.
                          (This is caught internally and yielded as an 'error' event).
        """
        try:
            # Record command in history
            self.history.append({
                'command': command,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'cwd': str(self.current_dir)
            })
            
            # Launch the command as a subprocess
            # Note: Using shell=True can be a security risk if `command` comes from
            # untrusted input. For this PoC, it's assumed to be from user input
            # within the TUI.
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.current_dir) # Execute in the manager's current directory
            )

            # Ensure stdout and stderr streams were successfully captured
            if process.stdout is None or process.stderr is None:
                # This should ideally not happen with PIPE, but good to check.
                raise RuntimeError("Failed to get stdout/stderr streams from subprocess.")

            # Queues to hold lines from stdout and stderr
            stdout_queue: asyncio.Queue[str] = asyncio.Queue()
            stderr_queue: asyncio.Queue[str] = asyncio.Queue()

            # Create tasks to read from stdout and stderr streams concurrently
            # and put lines into their respective queues.
            stdout_task = asyncio.create_task(self._enqueue_stream(process.stdout, stdout_queue))
            stderr_task = asyncio.create_task(self._enqueue_stream(process.stderr, stderr_queue))

            # Main loop to yield output as it becomes available from the queues
            while True:
                stdout_done = stdout_task.done()
                stderr_done = stderr_task.done()
                stdout_empty = stdout_queue.empty()
                stderr_empty = stderr_queue.empty()

                # Exit condition: both stream reading tasks are done, and their queues are empty.
                if stdout_done and stderr_done and stdout_empty and stderr_empty:
                    break

                # Yield lines from stdout if available
                if not stdout_empty:
                    yield ('stdout', await stdout_queue.get())
                
                # Yield lines from stderr if available
                if not stderr_empty:
                    yield ('stderr', await stderr_queue.get())
                
                # If queues are empty but tasks are still running,
                # sleep briefly to prevent busy-waiting and allow other tasks to run.
                if stdout_empty and stderr_empty and (not stdout_done or not stderr_done):
                    await asyncio.sleep(0.001)

            # Ensure both stream reading tasks have fully completed.
            await asyncio.gather(stdout_task, stderr_task)
            # Wait for the subprocess itself to terminate.
            await process.wait()
            # Yield the final return code of the command.
            yield ('returncode', process.returncode or 0)

        except Exception as e:
            # If any other exception occurs (e.g., command not found, permission issues),
            # yield an error message and a non-zero return code.
            yield ('error', str(e))
            yield ('returncode', 1) # Indicate failure

    async def _enqueue_stream(self, stream: asyncio.StreamReader, queue: asyncio.Queue[str]) -> None:
        """
        Asynchronously reads lines from a stream and puts them into a queue.

        This helper function is used to concurrently process stdout and stderr
        of a subprocess. It decodes lines as UTF-8, replacing errors.

        Args:
            stream: The asyncio.StreamReader to read from (e.g., process.stdout).
            queue: The asyncio.Queue to put the read lines into.
        """
        while True:
            line_bytes = await stream.readline()
            if not line_bytes: # EOF
                break
            await queue.put(line_bytes.decode('utf-8', errors='replace'))


class MarkdownManager:
    """Handles markdown note taking and rendering"""
    
    def __init__(self):
        self.current_note = "# CTF Toolkit Notes\n\n*Start taking notes...*"
    
    def update_content(self, content: str):
        """Update the current markdown content"""
        self.current_note = content
    
    def get_rendered_content(self) -> str:
        """Get the current markdown content"""
        return self.current_note


class LLMManager:
    """Handles LLM integration using LiteLLM"""
    
    def __init__(self):
        self.conversation_history = []
        # Read model from environment variable
        model_env = os.getenv("LITELLM_MODEL", "gpt-4")
        self.model = model_env # Store the full model name, e.g., "ollama/mistral" or "gpt-4"
    
    async def query_llm(self, prompt: str, context: str = "") -> str:
        """Query the LLM via LiteLLM"""
        try:
            # Build messages like Chat API expects
            messages = [{"role": "system", "content": context}] if context else []
            messages.append({"role": "user", "content": prompt})
            
            response = await acompletion(
                model=self.model,
                messages=messages,
                stream=False,  # Set True if you want streaming later
            )
            # Extract content from the response
            # Extract content from the response
            # Pylance may incorrectly infer 'response' as CustomStreamWrapper here.
            # LiteLLM documentation states acompletion(stream=False) returns a ModelResponse.
            content = response.choices[0].message.content # type: ignore[attr-defined]
            if content is None:
                # Consider logging this case or raising a more specific error
                return "⚠️ LLM returned no content."
            return content
        except Exception as e:
            # Handle errors during the API call
            return f"⚠️ LLM error: {e}"


class PluginManager:
    """Handles plugin discovery and management"""
    
    def __init__(self):
        self.plugins = [
            {"name": "CyberChef", "status": "Available", "description": "Data manipulation toolkit"},
            {"name": "John the Ripper", "status": "Installed", "description": "Password cracking"},
            {"name": "Wireshark", "status": "Available", "description": "Network protocol analyzer"},
            {"name": "Burp Suite", "status": "Not Found", "description": "Web app security testing"},
            {"name": "Ghidra", "status": "Installed", "description": "Reverse engineering suite"},
        ]
    
    def get_plugins(self):
        """Get list of available plugins"""
        return self.plugins


# =============================================================================
# UI COMPONENTS - Individual Tab Implementations
# =============================================================================

class TerminalTab(Container):
    """Terminal tab with command execution"""
    
    def __init__(self):
        super().__init__()
        self.terminal_manager = TerminalManager()
    
    def compose(self) -> ComposeResult:
        yield Static("🖥️  Terminal", classes="tab-header")
        yield TextArea("Welcome to CTF Toolkit Terminal!\n", id="terminal-output", read_only=True)
        with Horizontal(id="terminal-input-container"):
            yield Input(placeholder="Enter command...", id="terminal-input")
            yield Button("Execute", id="terminal-execute", variant="primary")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "terminal-execute":
            await self.execute_command()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "terminal-input":
            await self.execute_command()
    
    async def execute_command(self):
        """Execute the command from input"""
        input_widget = self.query_one("#terminal-input", Input)
        output_widget = self.query_one("#terminal-output", TextArea)
        
        command = input_widget.value.strip()
        if not command:
            return
        
        # Clear input and show executing
        input_widget.value = ""
        output_widget.text += f"\n{command}\n[Executing...]\n"
        output_widget.scroll_end(animate=False) # Auto-scroll
        
        # Execute command and process output incrementally
        return_code = 1 # Default to error
        async for stream_type, value in self.terminal_manager.execute_command(command):
            if stream_type == 'stdout':
                output_widget.text += value
            elif stream_type == 'stderr':
                output_widget.text += f"[STDERR] {value}"
            elif stream_type == 'error':
                output_widget.text += f"[ERROR] {value}\n"
            elif stream_type == 'returncode':
                return_code = value
            output_widget.scroll_end(animate=False) # Auto-scroll

        output_widget.text += f"[Exit Code: {return_code}]\n"
        output_widget.scroll_end(animate=False) # Auto-scroll


class MarkdownTab(Container):
    """Markdown notes tab with live preview"""
    
    def __init__(self):
        super().__init__()
        self.markdown_manager = MarkdownManager()
    
    def compose(self) -> ComposeResult:
        yield Static("📝 Notes", classes="tab-header")
        with Horizontal():
            with Vertical():
                yield Label("Editor")
                yield TextArea(
                    self.markdown_manager.current_note,
                    id="markdown-editor",
                    language="markdown"
                )
            with Vertical():
                yield Label("Preview")
                yield Markdown(self.markdown_manager.current_note, id="markdown-preview")
    
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "markdown-editor":
            # Update manager
            self.markdown_manager.update_content(event.text_area.text)
            # Update preview
            preview = self.query_one("#markdown-preview", Markdown)
            preview.update(event.text_area.text)


class AITab(Container):
    """AI assistant tab for LLM integration"""
    
    def __init__(self):
        super().__init__()
        self.llm_manager = LLMManager()
    
    def compose(self) -> ComposeResult:
        yield Static("🤖 AI Assistant", classes="tab-header")
        
        # Removed provider selection as LiteLLM handles this via config
        # with Horizontal():
        #     yield Label("Provider:")
        #     yield Select(
        #         [(provider, provider) for provider in self.llm_manager.providers],
        #         value=self.llm_manager.current_provider,
        #         id="llm-provider"
        #     )
        
        with Horizontal():
            yield Input(placeholder="Ask the AI about your CTF challenge...", id="ai-input")
            yield Button("Send", id="ai-send", variant="primary")

        yield TextArea("", id="ai-conversation", read_only=True)
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ai-send":
            await self.send_ai_query()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "ai-input":
            await self.send_ai_query()
    
    async def send_ai_query(self):
        """Send query to AI and display response"""
        input_widget = self.query_one("#ai-input", Input)
        conversation_widget = self.query_one("#ai-conversation", TextArea)
        
        query = input_widget.value.strip()
        if not query:
            return
        
        # Clear input and show thinking
        input_widget.value = ""
        conversation_widget.text += f"\n🧑 You: {query}\n\n🤖 AI: [Thinking...]\n"
        
        # Get AI response
        response = await self.llm_manager.query_llm(query)
        
        # Update conversation
        conversation_widget.text = conversation_widget.text.replace("[Thinking...]", response)
        conversation_widget.text += "\n" + "─" * 50 + "\n"


class PluginTab(Container):
    """Plugin management tab"""
    
    def __init__(self):
        super().__init__()
        self.plugin_manager = PluginManager()
    
    def compose(self) -> ComposeResult:
        yield Static("🔧 Tools & Plugins", classes="tab-header")
        
        table = DataTable()
        table.add_columns("Tool", "Status", "Description")
        
        for plugin in self.plugin_manager.get_plugins():
            status_emoji = {
                "Installed": "✅",
                "Available": "📦", 
                "Not Found": "❌"
            }.get(plugin["status"], "❓")
            
            table.add_row(
                plugin["name"],
                f"{status_emoji} {plugin['status']}",
                plugin["description"]
            )
        
        yield table
        yield Button("Refresh Plugins", id="refresh-plugins", variant="success")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-plugins":
            self.notify("🔄 Plugin refresh would happen here!")


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class CTFToolkitApp(App):
    """Main CTF Toolkit TUI Application"""
    
    CSS_PATH = "ctf_toolkit.css"
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+t", "focus_terminal", "Terminal"),
        Binding("ctrl+m", "focus_markdown", "Notes"),
        Binding("ctrl+a", "focus_ai", "AI"),
        Binding("ctrl+p", "focus_plugins", "Tools"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with TabbedContent(id="main-tabs"):
            with TabPane("Terminal", id="terminal-tab"):
                yield TerminalTab()
            with TabPane("Notes", id="markdown-tab"):
                yield MarkdownTab()
            with TabPane("AI Assistant", id="ai-tab"):
                yield AITab()
            with TabPane("Tools", id="plugin-tab"):
                yield PluginTab()
        
        yield Footer()
    
    def action_focus_terminal(self) -> None:
        """Focus the terminal tab"""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "terminal-tab"
    
    def action_focus_markdown(self) -> None:
        """Focus the markdown tab"""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "markdown-tab"
    
    def action_focus_ai(self) -> None:
        """Focus the AI tab"""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "ai-tab"
    
    def action_focus_plugins(self) -> None:
        """Focus the plugins tab"""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "plugin-tab"
    
    def on_mount(self) -> None:
        """Called when app starts"""
        self.title = "CTF Toolkit v0.1.0"
        self.sub_title = "Proof of Concept"


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app = CTFToolkitApp()
    app.run()
