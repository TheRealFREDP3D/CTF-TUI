#!/usr/bin/env python3
"""
CTF Toolkit TUI - Proof of Concept
A demonstration of the core UI structure and functionality
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
import random

# =============================================================================
# MANAGERS - Business Logic Layer
# =============================================================================

class TerminalManager:
    """Handles command execution and terminal operations"""
    
    def __init__(self):
        self.history = []
        self.current_dir = Path.cwd()
    
    async def execute_command(self, command: str) -> AsyncGenerator[Tuple[str, Any], None]:
        """Execute a command and yield output incrementally"""
        try:
            # Add to history
            self.history.append({
                'command': command,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'cwd': str(self.current_dir)
            })
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.current_dir)
            )

            if process.stdout is None or process.stderr is None:
                raise RuntimeError("Failed to get stdout/stderr streams from subprocess.")

            stdout_queue: asyncio.Queue[str] = asyncio.Queue()
            stderr_queue: asyncio.Queue[str] = asyncio.Queue()

            stdout_task = asyncio.create_task(self._enqueue_stream(process.stdout, stdout_queue))
            stderr_task = asyncio.create_task(self._enqueue_stream(process.stderr, stderr_queue))

            # Continuously yield output as it becomes available
            while True:
                stdout_done = stdout_task.done()
                stderr_done = stderr_task.done()
                stdout_empty = stdout_queue.empty()
                stderr_empty = stderr_queue.empty()

                if stdout_done and stderr_done and stdout_empty and stderr_empty:
                    break # All tasks finished and queues are empty

                if not stdout_empty:
                    yield ('stdout', await stdout_queue.get())
                if not stderr_empty:
                    yield ('stderr', await stderr_queue.get())
                
                # If both queues are empty but tasks are not done, wait a bit
                if stdout_empty and stderr_empty and (not stdout_done or not stderr_done):
                    await asyncio.sleep(0.001) # Small sleep to prevent busy waiting

            await asyncio.gather(stdout_task, stderr_task) # Ensure stream reading tasks are truly complete
            await process.wait() # Wait for the process to finish
            yield ('returncode', process.returncode or 0)

        except Exception as e:
            yield ('error', str(e))
            yield ('returncode', 1)

    async def _enqueue_stream(self, stream: asyncio.StreamReader, queue: asyncio.Queue[str]):
        """Helper to read from a stream and put lines into a queue"""
        while True:
            line = await stream.readline()
            if not line:
                break
            await queue.put(line.decode('utf-8', errors='replace'))


class MarkdownManager:
    """Handles markdown note taking and rendering"""
    
    def __init__(self):
        self.notes_file = Path("ctf_notes.md")
        self.current_note = "# CTF Toolkit Notes\n\n*Start taking notes...*" # Default content
        if self.notes_file.exists():
            try:
                self.current_note = self.notes_file.read_text(encoding="utf-8")
            except (IOError, OSError) as e:
                print(f"Error loading notes from {self.notes_file}: {e}")
                # Keep default content if loading fails
    
    def update_content(self, content: str):
        """Update the current markdown content and save to file"""
        self.current_note = content
        try:
            self.notes_file.write_text(self.current_note, encoding="utf-8")
        except (IOError, OSError) as e:
            print(f"Error saving notes to {self.notes_file}: {e}")
            # Optionally, notify the user here if a more sophisticated error handling is needed
    
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
        self.available_models = ["gpt-4", "ollama/mistral", "claude-2", "gpt-3.5-turbo"]
    
    async def query_llm(self, prompt: str, context: str = "") -> str:
        """Query the LLM via LiteLLM"""
        try:
            # Build messages like Chat API expects
            messages = [{"role": "system", "content": context}] if context else []
            messages.extend(self.conversation_history) # Prepend conversation history
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
            
            # Append to conversation history
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": content})
            
            return content
        except Exception as e:
            # Handle errors during the API call
            return f"⚠️ LLM error: {e}"

    def set_model(self, model_name: str):
        """Sets the LLM model."""
        self.model = model_name


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

    def refresh_plugins(self):
        """Simulates refreshing plugin statuses."""
        possible_statuses = ["Installed", "Available", "Not Found"]
        for plugin in self.plugins:
            plugin['status'] = random.choice(possible_statuses)


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
        yield TextArea("Welcome to CTF Toolkit Terminal!\n$ ", id="terminal-output", read_only=True)
        with Horizontal(id="terminal-input-container"):
            yield Static("$ ", classes="prompt")
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
        output_widget.text += f"\n$ {command}\n[Executing...]\n"
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
        
        with Horizontal():
            yield Label("Model:")
            yield Select(
                [(model, model) for model in self.llm_manager.available_models],
                value=self.llm_manager.model,
                id="llm-model-select"
            )
        
        with Horizontal():
            yield Input(placeholder="Ask the AI about your CTF challenge...", id="ai-input")
            yield Button("Send", id="ai-send", variant="primary")

        yield TextArea("", id="ai-conversation", read_only=True)

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle model selection change."""
        if event.select.id == "llm-model-select":
            if event.value is not None: # Ensure event.value is not None
                self.llm_manager.set_model(str(event.value))

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
        
        # Clear input
        input_widget.value = ""
        
        # Append user's query
        conversation_widget.text += f"\n🧑 You: {query}\n"
        
        # Placeholder for AI response
        thinking_message = f"\n🤖 AI ({self.llm_manager.model}): [Thinking...]\n"
        conversation_widget.text += thinking_message
        conversation_widget.scroll_end(animate=False)
        
        # Get AI response
        response = await self.llm_manager.query_llm(query)
        
        # Update conversation: Replace only the last "[Thinking...]"
        # A simple approach: find the last occurrence of the specific thinking message
        last_thinking_index = conversation_widget.text.rfind(thinking_message.strip()) # Use strip to match text area content
        
        if last_thinking_index != -1:
            # Calculate the start and end of the placeholder text to replace
            placeholder_start_index = last_thinking_index
            # We need to be careful if "[Thinking...]" is part of the actual model name, though unlikely.
            # The replacement logic relies on replacing the *entire* "🤖 AI (model): [Thinking...]" line.
            # For robustness, we replace the entire line.
            
            # Find the end of the "Thinking..." line
            end_of_thinking_line = conversation_widget.text.find("\n", placeholder_start_index)
            if end_of_thinking_line == -1: # If it's the last line
                end_of_thinking_line = len(conversation_widget.text)

            # Construct the new AI response line
            new_ai_response_line = f"\n🤖 AI ({self.llm_manager.model}): {response}\n"

            # Replace the placeholder line with the actual response line
            conversation_widget.text = (
                conversation_widget.text[:placeholder_start_index] +
                new_ai_response_line +
                conversation_widget.text[end_of_thinking_line:]
            )
        else: # Fallback if "[Thinking...]" wasn't found (should not happen in normal flow)
            conversation_widget.text += f"\n🤖 AI ({self.llm_manager.model}): {response}\n" # Append if placeholder not found

        conversation_widget.text += "─" * 50 + "\n"
        conversation_widget.scroll_end(animate=False)


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
            # Call the refresh logic in the manager
            self.plugin_manager.refresh_plugins()
            
            # Get the DataTable widget
            table = self.query_one(DataTable)
            
            # Clear existing rows
            table.clear()
            
            # Re-populate the table
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
            # self.notify("🔄 Plugin refresh would happen here!") # Removed as per requirement


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class CTFToolkitApp(App):
    """Main CTF Toolkit TUI Application"""
    
    CSS_PATH = None  # Using inline CSS for POC
    CSS = """
    .tab-header {
        text-style: bold;
        background: green;
        color: white;
        padding: 1;
        margin-bottom: 1;
    }
    
    .prompt {
        color: $accent;
        text-style: bold;
        width: 2; 
    }
    
    #terminal-output {
        /* height: 20; -- Removed for flexible height */
        background: $surface;
        border: solid $primary;
        height: 1fr; /* Allow terminal output to expand */
        overflow-y: auto; /* Enable vertical scrolling */
    }

    #terminal-input { /* Added for input field font size */
        /* font-size: 75%; -- Removed, not a valid Textual CSS property here */
    }
    
    #markdown-editor, #markdown-preview {
        height: 30;
    }
    
    #ai-conversation {
        height: 30;
        background: $surface;
        border: solid $accent;
    }
    
    Footer {
        background: $primary;
    }
    """
    
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
