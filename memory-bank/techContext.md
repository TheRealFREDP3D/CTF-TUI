# Tech Context

## Technologies Used
- **Framework**: Textual (Python TUI framework)
- **Language**: Python 3.7+
- **Async Support**: Full async/await pattern for non-blocking operations
- **Process Management**: asyncio subprocess handling for command execution

## Development Setup
- Requires Python 3.7+
- Dependencies are listed in the "Dependencies" section below.

## Technical Constraints
- The application is a TUI, which has limitations compared to a GUI.
- Performance optimization is needed for large outputs.
- Cross-platform compatibility testing is required.

## Dependencies

```python
# Core Requirements
textual>=0.40.0
asyncio  # Built-in Python 3.7+
pathlib  # Built-in Python 3.4+
subprocess  # Built-in

# Future Production Dependencies
openai  # For OpenAI integration
anthropic  # For Claude integration
requests  # For API calls
pyyaml  # For configuration files
