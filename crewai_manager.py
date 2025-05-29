import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import (
    DirectoryReadTool,
    FileReadTool,
    SerperDevTool,
    WebsiteSearchTool,
    SearchDuckDuckGoTool
)
from langchain_openai import ChatOpenAI # Added import
import os # Ensure os is imported

# Set up environment variables for tools if not already set
# SERPER_API_KEY is for the SerperDevTool.
os.environ["SERPER_API_KEY"] = os.environ.get("SERPER_API_KEY", "YOUR_SERPER_API_KEY_IF_USING_SERPER")
# GEMINI_API_KEY and LITELLM_MODEL will be fetched in setup_crew for the agent LLM.
# OPENAI_API_KEY and OPENAI_MODEL_NAME are no longer primary for agent LLM configuration here.


class CrewAIManager:
    def __init__(self):
        self.crew = None
        # Initialize tools - these are LLM-agnostic
        self.directory_read_tool = DirectoryReadTool()
        self.file_read_tool = FileReadTool()
        self.serper_dev_tool = SerperDevTool() # For focused web searches if API key is available
        self.website_search_tool = WebsiteSearchTool() # For scraping specific websites
        self.duckduckgo_search_tool = SearchDuckDuckGoTool() # For general web searches

    def setup_crew(self, notes_content: str):
        # Determine the correct API key and model from environment variables
        llm_model_name = os.getenv("LITELLM_MODEL", "gemini/gemini-pro")
        gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not gemini_api_key:
            # Handle missing API key gracefully, perhaps by raising an error
            # or using a fallback mechanism if one exists.
            # For now, this will likely cause ChatOpenAI to fail if the model isn't local.
            print("Warning: GEMINI_API_KEY not found in environment.")
            # Depending on how ChatOpenAI handles a None key for certain models,
            # this might still work for local LiteLLM-proxied models not needing a key.
            # However, for "gemini/gemini-pro", a key is expected.
        
        agent_llm = None
        try:
            agent_llm = ChatOpenAI(
                model=llm_model_name, # e.g., "gemini/gemini-pro"
                api_key=gemini_api_key # Pass the Gemini key
            )
        except Exception as e:
            print(f"Error initializing ChatOpenAI with direct LiteLLM model: {e}")
            # Attempting a common fallback for when ChatOpenAI needs to be pointed
            # to a LiteLLM OpenAI-compatible server endpoint.
            # This requires LiteLLM to be running as a server (e.g., `litellm --model gemini/gemini-pro`).
            # The default LiteLLM server runs on http://localhost:8000.
            # If not running a server, this configuration is not applicable.
            # For this setup, we are primarily aiming for direct model usage via LiteLLM's capabilities
            # integrated within the ChatOpenAI/Langchain stack, not necessarily requiring a separate server.
            # If the above direct instantiation fails, it implies a deeper configuration or version compatibility issue.
            # We will re-raise or handle as appropriate. For now, we'll assume the first try should work
            # if LiteLLM is correctly interpreting "gemini/gemini-pro" and using the GEMINI_API_KEY.
            # If the initial attempt fails, we'll proceed with agent_llm as None,
            # and agents might fail if they strictly require an LLM.
            # A more robust solution would involve more sophisticated error handling or configuration options.
            # For now, let's stick to the primary intended path and log the error.
            # Re-raising the exception might be better to halt if LLM can't be configured.
            raise ConnectionError(f"Failed to initialize ChatOpenAI for agents: {e}. Ensure GEMINI_API_KEY is set and LITELLM_MODEL is correct.")


        # Define Agents
        team_leader = Agent(
            role="CTF Strategist and Team Leader",
            goal="Coordinate the team to analyze the provided CTF notes and generate a comprehensive, step-by-step, actionable CTF plan. Ensure the plan is clear, easy to follow, and covers all critical aspects mentioned in the notes.",
            backstory="You are a seasoned CTF veteran, known for your strategic thinking and ability to lead teams to victory. You can break down complex challenges into manageable steps and anticipate potential roadblocks.",
            verbose=True,
            allow_delegation=True,
            llm=agent_llm
        )

        code_executer = Agent(
            role="CTF Code and Command Specialist",
            goal="Analyze the CTF notes to identify potential commands, scripts, or code snippets relevant to the challenges. Suggest specific tools and commands for reconnaissance, exploitation, and post-exploitation, tailored to the information in the notes.",
            backstory="You are a hands-on cybersecurity expert with a deep understanding of penetration testing tools and scripting. You can quickly identify the right command for the job and understand how different code snippets can be used in CTF scenarios. You are familiar with tools like nmap, sqlmap, gobuster, and scripting languages like Python and Bash.",
            verbose=True,
            allow_delegation=False,
            tools=[self.file_read_tool, self.directory_read_tool],
            llm=agent_llm
        )

        searcher = Agent(
            role="CTF Intelligence Gatherer",
            goal="Based on the CTF notes, search for relevant information online, including potential vulnerabilities, exploits for specific software versions, documentation for tools, and general OSINT (Open Source Intelligence) that could be useful.",
            backstory="You are a skilled online researcher, adept at using search engines to find obscure technical details, vulnerability databases, and community discussions related to CTF challenges. You know how to filter information effectively and identify credible sources.",
            verbose=True,
            allow_delegation=False,
            tools=[self.duckduckgo_search_tool, self.serper_dev_tool, self.website_search_tool],
            llm=agent_llm
        )

        writer_archivist = Agent(
            role="CTF Plan Scribe and Documenter",
            goal="Compile all inputs from the team (Team Leader, Code Executer, Searcher) into a clear, concise, and actionable step-by-step CTF plan. The plan should be well-organized, easy for a CTF player to follow, and include all recommended commands, tools, and strategies.",
            backstory="You are a meticulous technical writer with a talent for transforming complex information into clear, actionable guides. You ensure that every detail is captured and presented in a logical and user-friendly format. Your plans are legendary for their clarity and effectiveness.",
            verbose=True,
            allow_delegation=False,
            llm=agent_llm
        )

        # Define Task
        ctf_task = Task(
            description=f"""
Based on the following CTF notes, create a comprehensive, step-by-step, actionable plan for a CTF player.
The plan must be easy to follow and should guide the player through the process of tackling the challenges.

CTF Notes:
---
{notes_content}
---

The plan should include:
1.  Prioritized list of potential vulnerabilities to investigate.
2.  Specific tools to use for each step (e.g., reconnaissance, scanning, exploitation).
3.  Exact commands or code snippets where appropriate and clearly explained.
4.  Strategies for different types of challenges mentioned in the notes (e.g., web, network, OSINT).
5.  Any relevant information found by the Searcher that could aid the player.
6.  A logical flow, starting from initial reconnaissance to potential exploitation and post-exploitation steps if applicable.

Coordinate with the Code Executer to get specific commands and scripts, and with the Searcher to incorporate relevant external information.
The Team Leader will oversee the process to ensure the plan is comprehensive and meets all requirements.
The final output will be compiled by the Writer/Archivist into a single, coherent document.
""",
            expected_output="A detailed, step-by-step, actionable CTF plan document, formatted clearly for a CTF player to use. It should include sections for reconnaissance, enumeration, vulnerability analysis, suggested exploitation steps, and any relevant commands or tools for each part.",
            agent=team_leader # The TeamLeader will orchestrate this task, delegating sub-tasks.
        )

        # Initialize Crew
        self.crew = Crew(
            agents=[team_leader, code_executer, searcher, writer_archivist],
            tasks=[ctf_task],
            process=Process.sequential,
            verbose=True,
        )

    def run_crew(self) -> str:
        if not self.crew:
            return "Error: Crew not set up. Please call setup_crew() first."

        try:
            result = self.crew.kickoff()
            return result
        except Exception as e:
            return f"Error running crew: {str(e)}"

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    manager = CrewAIManager()
    sample_notes = """
    Target: Example Corp (example.com)
    Scope: Web application security, network penetration testing.
    Potential areas:
    - Web server: Apache/2.4.52 (Ubuntu) - check for known vulnerabilities.
    - Login page: Possible SQL injection or XSS.
    - File upload functionality: Test for unrestricted file uploads.
    - Network: Scan for open ports, identify services.
    - OSINT: Gather information about employees, technologies used.
    Tools to consider: nmap, dirb, sqlmap, Burp Suite, Metasploit.
    Previous findings: Weak password policy noted in last year's internal audit.
    """
    manager.setup_crew(notes_content=sample_notes)
    crew_result = manager.run_crew()
    print("\n--- Crew Execution Result ---")
    print(crew_result)
