from agency_swarm import Agent

agency_code_agent = Agent(
    name="Agency Code Agent",
    description="A comprehensive coding assistant that provides advanced development assistance similar to Claude Code CLI, featuring comprehensive code editing, file management, testing, and development workflow automation for software engineers and developers.",
    instructions="./instructions.md",
    tools_folder="./tools",
    model="gpt-4o",
)
