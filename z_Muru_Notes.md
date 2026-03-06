Mermaid Link - https://mermaid.live/


I have a Google ADK multi-agent demo project at c:\Muru_Workspace\metro_city_demo.
Please read the CLAUDE.md file in that folder to get up to speed on the project architecture, agents, tools, and business rules.

Once you've read it, launch the ADK web server so I can test the demo.

CRITICAL: The server MUST be launched from c:\Muru_Workspace (the PARENT directory), NOT from inside metro_city_demo/. The correct command is:

  cd c:\Muru_Workspace
  adk web

If port 8000 is already in use, find and kill the stale process first:
  netstat -ano | findstr ":8000"
  taskkill /F /PID [PID]

Then relaunch. Confirm the server is running and give me the URL to open in my browser.
