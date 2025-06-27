# MCP:CONNECT TO YOUR INDUSTRY DATA
This was comstomized created by me for Metris Platform, if you are interested in mcp and want to create a mcp for your own company, contact me.😊

# Table of Contents
1.Adding MCP to your Python project
2.Running the standalone MCP development tools
3.Addingmcp.py` and installing dependencies

# First,Adding MCP to your python project
We recommend using uv to manage your Python projects.

1.If you haven't created a uv-managed project yet, create one:

uv init mcp-server-demo
cd mcp-server-demo

2.Then add MCP to your project dependencies:

uv add "mcp[cli]"

▶️ Alternatively, for projects using pip for dependencies:
pip install "mcp[cli]"
Running the standalone MCP development tools

3.To run the mcp command with uv:

uv run mcp

# Then ,Addingmcp.py and installing dependencies
Add the mcp.py file(Copy it from my project) to your project. Then, install the packages listed inrequirements.txt(From my project) using the following command:

pip install -r requirements.txt

# This setup allows you to connect to industry data using the MCP for the Metris Platform. If you encounter any issues, feel free to reach me.

