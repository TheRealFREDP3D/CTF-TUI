# Tech Context

## Technologies Used
- **Framework**: Textual (Python TUI framework)
- **Language**: Python 3.7+
- **LLM Abstraction**: LiteLLM for abstracting various LLM APIs.
- **Async Support**: Full async/await pattern for non-blocking operations, with emphasis on best practices like using worker threads and incremental output streaming.
- **Process Management**: asyncio subprocess handling for command execution, with a focus on secure input sanitization.
- **Configuration Management**: Utilizing `pyyaml` for configuration files, with added validation using `jsonschema`. Prioritizing environment variables for sensitive information like API keys.
- **Testing**: Employing `pytest-asyncio` and `unittest.mock` for effective testing, including mocking subprocesses.
- **Logging**: Implementing structured logging for better debugging.
- **Packaging**: Planning to use `PyInstaller` for application bundling and distribution.

## Development Setup
- Requires Python 3.7+
- Dependencies are listed in the "Dependencies" section below.
- Development environment should facilitate cross-platform compatibility testing.

## Technical Constraints
- The application is a TUI, which has limitations compared to a GUI.
- Performance optimization is needed for large outputs, requiring techniques like virtualization and throttling.
- Cross-platform compatibility testing is required across various terminals and operating systems.
- Secure handling of sensitive information and subprocess inputs is a critical constraint.

## Dependencies

```python
# Core Requirements
textual>=0.40.0
asyncio  # Built-in Python 3.7+
pathlib  # Built-in Python 3.4+
subprocess  # Built-in
pyyaml # For configuration file handling
jsonschema # For configuration validation
litellm # For LLM abstraction

# Future Production Dependencies
openai  # For OpenAI integration (consider lazy import)
anthropic  # For Claude integration (consider lazy import)
requests  # For API calls
pytest-asyncio # For asynchronous testing
pytest # For testing
```

## Tool Usage Patterns
- Utilizing `asyncio.create_subprocess_exec` for running external commands securely.
- Employing `set_interval` for rate-limiting UI updates.
- Using environment variables for sensitive configuration.
- Leveraging testing frameworks and logging for development and debugging.
- Planning to use `PyInstaller` for application distribution.
- Integrating LiteLLM for unified LLM access.
