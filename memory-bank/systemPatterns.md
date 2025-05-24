# System Patterns

## Architecture
The application follows a **Manager-Component** architecture pattern.

### Core Design Pattern
- **Managers**: Handle business logic and data operations (e.g., TerminalManager, MarkdownManager, LLMManager, PluginManager).
- **UI Components**: Render interface elements and handle user interactions (e.g., TerminalTab, MarkdownTab, AITab, PluginTab).
- **Main Application**: Orchestrates the overall user experience (CTFToolkitApp).

## Component Relationships
- The Main Application (`CTFToolkitApp`) orchestrates the various Managers and UI Components.
- UI Components interact with Managers to perform actions and display data. For example, `TerminalTab` interacts with `TerminalManager` to execute commands.

## Critical Implementation Paths
- Asynchronous operations are critical for non-blocking behavior, especially for command execution and LLM API calls.
- The interaction between UI Components and Managers for data flow and updates.
