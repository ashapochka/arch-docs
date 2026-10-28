"""Example: the nine architecture diagrams of the MCP Chat CLI project.

A worked example of every diagram type arch-docs supports: runtime view, use
cases, logical structure (classes), module dependencies, contracts, three
sequence diagrams and an activity diagram. Run it to regenerate them:

    uv run --project ~/.claude/skills/arch-docs python examples/mcp_chat_cli/diagrams.py OUT_DIR
"""

import sys
from pathlib import Path

from arch_docs import Diagram
from arch_docs.adapters import save_diagram
from arch_docs.diagram import Kind


def build() -> list[Diagram]:
    """Return all diagrams, in document order."""
    diagrams: list[Diagram] = []
    # 1. Runtime / deployment view ------------------------------------------------
    d = Diagram("runtime-view", 1100, 545)
    d.actor("user", 40, 168, "User\n(terminal)")
    d.container("cli", 130, 40, 520, 490, "CLI process: uv run main.py")
    d.box("main", 160, 80, 200, 56, "main.py\ncomposition root", "app")
    d.cylinder("env", 410, 78, 200, 60, ".env\nCLAUDE_MODEL, API key", "ext")
    d.box("cliapp", 160, 170, 200, 56, "CliApp\nprompt_toolkit UI", "ui")
    d.box("claude", 410, 170, 200, 56, "Claude\nAsyncAnthropic wrapper", "app")
    d.box("chat", 160, 260, 200, 56, "CliChat / Chat\nconversation + agent loop", "app")
    d.box("tools", 410, 260, 200, 56, "ToolManager\ntool list + routing", "app")
    d.box("doc", 160, 350, 200, 56, "MCPClient (doc_client)\nstdio MCP session", "int")
    d.box(
        "extra",
        410,
        350,
        200,
        56,
        "MCPClient (extra)\noptional, one per script",
        "int",
        dashed=True,
    )
    d.cylinder("logs", 160, 440, 200, 60, "logs/*.log\nserver stderr", "ext")
    d.note(
        "extra_note",
        410,
        440,
        220,
        60,
        "uv run main.py a.py b.py\nadds one MCPClient + log file\nper extra server script",
    )
    d.box("api", 760, 170, 270, 56, "Anthropic Messages API\nHTTPS", "ext")
    d.container("srv", 720, 280, 350, 240, "Server subprocess: mcp_server.py", "srv")
    d.box(
        "fastmcp",
        760,
        320,
        270,
        56,
        "DocumentMCP (FastMCP)\n3 tools, 2 resources, 2 prompts",
        "srv",
    )
    d.cylinder(
        "store",
        760,
        420,
        270,
        64,
        "InMemoryDocumentStore\n6 default documents",
        "store",
    )
    d.edge("user", "right", "cliapp", "left", "types / reads")
    d.edge("main", "right", "env", "left", "read_config")
    d.edge("main", "bottom", "cliapp", "top", "creates, run()")
    d.edge("cliapp", "bottom", "chat", "top", "run(query)")
    d.edge(
        "chat",
        "top",
        "claude",
        "bottom",
        "chat()",
        s_f=0.85,
        via=[(330, 243), (510, 243)],
        label_pos=0.62,
    )
    d.edge("chat", "right", "tools", "left", "tools")
    d.edge("claude", "right", "api", "left", "messages.create")
    d.edge("chat", "bottom", "doc", "top", "prompts,\nresources")
    d.edge(
        "tools",
        "bottom",
        "doc",
        "top",
        "",
        s_f=0.25,
        d_f=0.85,
        via=[(460, 333), (330, 333)],
    )
    d.edge("tools", "bottom", "extra", "top", "call_tool", s_f=0.6, d_f=0.6)
    d.edge(
        "doc",
        "bottom",
        "fastmcp",
        "left",
        "MCP over stdio (JSON-RPC)",
        s_f=0.85,
        via=[(330, 424), (690, 424), (690, 348)],
        label_pos=0.42,
    )
    d.edge("doc", "bottom", "logs", "top", "stderr", s_f=0.2, d_f=0.2, kind="dep")
    d.edge("fastmcp", "bottom", "store", "top", "get / update / list_ids")
    diagrams.append(d)

    # 2. Use cases ------------------------------------------------------------------
    d = Diagram("use-cases", 1010, 650)
    d.container("sys", 150, 30, 700, 605, "MCP Chat CLI", "plain", dashed=False)
    d.actor("user", 50, 190, "User")
    d.actor("dev", 50, 515, "Developer")
    d.actor("model", 930, 235, "Claude\n(model)")
    d.ellipse("uc1", 200, 70, 210, 56, "Ask a question")
    d.ellipse("uc3", 200, 150, 210, 56, "Run a prompt command\n(/format, /summarize)")
    d.ellipse("uc2", 200, 240, 210, 56, "Mention a document\n(@doc_id)")
    d.ellipse("uc4", 200, 320, 210, 56, "Autocomplete commands\nand document ids")
    d.ellipse(
        "uc8", 200, 400, 210, 56, "See a failed turn reported,\nkeep the session", "err"
    )
    d.ellipse("uc5", 560, 110, 210, 56, "Answer using tools", "app")
    d.ellipse("uc6", 560, 240, 210, 56, "List / read documents", "app")
    d.ellipse("uc7", 560, 330, 210, 56, "Edit a document", "app")
    d.ellipse("uc9", 200, 490, 210, 56, "Inspect the server\n(MCP Inspector)", "srv")
    d.ellipse("uc10", 200, 565, 210, 56, "Run tests, lint,\ntype check", "srv")
    for uc in ("uc1", "uc3", "uc2", "uc4", "uc8"):
        d.edge("user", "right", uc, "left", kind="assoc")
    for uc in ("uc9", "uc10"):
        d.edge("dev", "right", uc, "left", kind="assoc")
    for uc in ("uc5", "uc6", "uc7"):
        d.edge("model", "left", uc, "right", kind="assoc")
    d.edge("uc1", "right", "uc5", "left", "«include»", kind="dep")
    d.edge("uc3", "right", "uc5", "left", "«include»", kind="dep")
    d.edge("uc2", "right", "uc6", "left", "«include»", kind="dep")
    d.edge("uc6", "top", "uc5", "bottom", "«extend»", kind="dep")
    diagrams.append(d)

    # 3. Logical structure ------------------------------------------------------------
    d = Diagram("logical-structure", 1110, 720)
    d.container("p", 30, 30, 840, 130, "Presentation: core/cli.py", "ui")
    d.box(
        "cliapp",
        60,
        74,
        240,
        70,
        "CliApp\nread input, print replies,\nreport failed turns",
        "ui",
    )
    d.box(
        "completer",
        330,
        74,
        240,
        70,
        "UnifiedCompleter\ncompletes /commands\nand @document ids",
        "ui",
    )
    d.box(
        "suggest",
        600,
        74,
        240,
        70,
        "CommandAutoSuggest\nghost-text hint for a\ncommand's argument",
        "ui",
    )
    d.container("a", 30, 180, 840, 200, "Application: core/", "app")
    d.box(
        "clichat",
        60,
        205,
        240,
        62,
        "CliChat\n@mention context, /command\nto prompt messages",
        "app",
    )
    d.box(
        "chat",
        60,
        305,
        240,
        62,
        "Chat\nagent loop + history,\nrollback on failure",
        "app",
    )
    d.box(
        "tools",
        330,
        250,
        240,
        70,
        "ToolManager\ntools for Claude, routes\ntool_use to its client",
        "app",
    )
    d.box(
        "claude",
        600,
        250,
        240,
        70,
        "Claude\nAsyncAnthropic wrapper,\nmessage helpers",
        "app",
    )
    d.container("i", 30, 400, 840, 120, "Integration: mcp_client.py", "int")
    d.box(
        "client",
        60,
        430,
        380,
        72,
        "MCPClient\nstdio session: tools, prompts, resources;\nserver stderr to a log file",
        "int",
    )
    d.box(
        "errors",
        600,
        430,
        240,
        72,
        "CLIENT_ERRORS\nexpected client failures\n(D-007)",
        "int",
    )
    d.container(
        "s",
        30,
        540,
        840,
        165,
        "Server process: mcp_server.py, document_store.py",
        "srv",
    )
    d.box(
        "server",
        60,
        575,
        380,
        110,
        "create_server(store) -> FastMCP\ntools: list_documents, read_document,\n"
        "edit_document\nresources: docs://documents[/{doc_id}]\nprompts: format, summarize",
        "srv",
    )
    d.box(
        "store",
        600,
        575,
        240,
        110,
        "DocumentStore (protocol)\nget, update, list_ids\n\ndefault:\nInMemoryDocumentStore",
        "store",
    )
    d.box("api", 920, 250, 170, 70, "Anthropic API\nexternal service", "ext")
    d.box(
        "main",
        920,
        430,
        170,
        72,
        "main.py\ncomposition root:\nconfig, clients, wiring",
        "ext",
    )
    d.edge("cliapp", "right", "completer", "left", "owns")
    d.edge(
        "cliapp",
        "top",
        "suggest",
        "top",
        "owns",
        s_f=0.75,
        via=[(240, 60), (720, 60)],
        label_pos=0.6,
    )
    d.edge(
        "cliapp",
        "bottom",
        "clichat",
        "top",
        "run(), list_*()",
        kind="dep",
        label_pos=0.4,
    )
    d.edge("clichat", "bottom", "chat", "top", "extends", kind="inherit")
    d.edge(
        "chat",
        "right",
        "tools",
        "left",
        kind="dep",
        s_f=0.3,
        via=[(315, 324), (315, 285)],
    )
    d.edge(
        "chat",
        "right",
        "claude",
        "bottom",
        "chat()",
        kind="dep",
        s_f=0.75,
        via=[(720, 351)],
        label_pos=0.45,
    )
    d.edge("claude", "right", "api", "left", "HTTPS")
    d.edge(
        "chat",
        "bottom",
        "client",
        "top",
        "doc_client",
        kind="dep",
        d_f=0.316,
        label_pos=0.3,
    )
    d.edge(
        "tools",
        "bottom",
        "client",
        "top",
        "tools",
        kind="dep",
        s_f=0.3,
        d_f=0.9,
        label_pos=0.4,
    )
    d.edge(
        "tools",
        "bottom",
        "errors",
        "top",
        "catches",
        kind="dep",
        s_f=0.8,
        via=[(522, 388), (720, 388)],
        label_pos=0.5,
    )
    d.edge("client", "bottom", "server", "top", "MCP over stdio", label_pos=0.25)
    d.edge("server", "right", "store", "left", "injected store", kind="dep")
    diagrams.append(d)

    # 4. Module dependencies -------------------------------------------------------------
    d = Diagram("module-dependencies", 1160, 570)
    d.container("cp", 330, 20, 800, 400, "Client process modules")
    d.container("sp", 30, 20, 270, 400, "Server process modules", "srv")
    d.box("main", 620, 50, 200, 44, "main.py", "app")
    d.box("cli", 380, 140, 200, 44, "core/cli.py", "ui")
    d.box("clichat", 620, 140, 200, 44, "core/cli_chat.py", "app")
    d.box("claude", 880, 140, 200, 44, "core/claude.py", "app")
    d.box("chat", 620, 240, 200, 44, "core/chat.py", "app")
    d.box("tools", 880, 240, 200, 44, "core/tools.py", "app")
    d.box("client", 620, 340, 200, 44, "mcp_client.py", "int")
    d.box("server", 60, 140, 210, 44, "mcp_server.py", "srv")
    d.box("store", 60, 260, 210, 44, "document_store.py", "store")
    d.edge(
        "main",
        "bottom",
        "cli",
        "top",
        kind="dep",
        s_f=0.2,
        via=[(660, 112), (480, 112)],
    )
    d.edge("main", "bottom", "clichat", "top", kind="dep")
    d.edge(
        "main",
        "bottom",
        "claude",
        "top",
        kind="dep",
        s_f=0.8,
        via=[(780, 112), (980, 112)],
    )
    d.edge(
        "main",
        "right",
        "client",
        "right",
        kind="dep",
        d_f=0.3,
        via=[(1110, 72), (1110, 353)],
    )
    d.edge("cli", "right", "clichat", "left", kind="dep")
    d.edge(
        "cli",
        "bottom",
        "client",
        "top",
        "CLIENT_ERRORS",
        kind="dep",
        d_f=0.15,
        via=[(480, 318), (650, 318)],
        label_pos=0.3,
    )
    d.edge("clichat", "bottom", "chat", "top", kind="dep")
    d.edge("clichat", "right", "claude", "left", kind="dep")
    d.edge("chat", "right", "tools", "left", kind="dep")
    d.edge(
        "chat",
        "top",
        "claude",
        "bottom",
        kind="dep",
        s_f=0.9,
        via=[(800, 214), (940, 214)],
        d_f=0.3,
    )
    d.edge("chat", "bottom", "client", "top", kind="dep")
    d.edge("tools", "bottom", "client", "right", kind="dep", d_f=0.7, via=[(980, 371)])
    d.edge("server", "bottom", "store", "top", kind="dep")
    d.edge(
        "client",
        "left",
        "server",
        "right",
        "spawns + MCP over stdio\n(runtime link, no import)",
        kind="flow",
        via=[(330, 362), (315, 362), (315, 162)],
        label_pos=0.22,
        color="#d79b00",
    )
    d.container(
        "libs", 30, 445, 1100, 110, "Third-party libraries (pyproject.toml)", "plain"
    )
    libs = [
        ("prompt_toolkit", "core/cli.py"),
        ("anthropic", "core/claude, chat, tools,\ncli_chat, cli"),
        ("mcp (Python SDK)", "mcp_client, mcp_server,\ncore/cli, cli_chat, tools"),
        ("pydantic", "mcp_client, mcp_server"),
        ("python-dotenv", "main.py"),
        ("typing-extensions", "core/cli, cli_chat,\nmcp_client"),
    ]
    for i, (name, users) in enumerate(libs):
        d.box(f"lib{i}", 45 + i * 181, 478, 170, 62, f"{name}\n{users}", "ext", size=11)
    d.text(
        840, 425, 290, 18, "dashed arrow = Python import", align="right", italic=True
    )
    diagrams.append(d)

    # 5. Contracts / class view ----------------------------------------------------------
    d = Diagram("contracts", 1140, 470)
    d.classbox(
        "proto",
        40,
        40,
        270,
        None,
        "DocumentStore",
        [
            "+ get(doc_id) -> str",
            "+ update(doc_id, content) -> None",
            "+ list_ids() -> list[str]",
        ],
        stereotype="protocol",
    )
    d.classbox(
        "mem",
        40,
        200,
        270,
        None,
        "InMemoryDocumentStore",
        ["- _docs: dict[str, str]  (a copy)", "+ __init__(docs = DEFAULT_DOCS)"],
    )
    d.classbox(
        "nf",
        40,
        350,
        270,
        None,
        "DocumentNotFoundError",
        ["LookupError subclass", "+ doc_id: str"],
    )
    d.classbox(
        "srv",
        410,
        40,
        340,
        None,
        "DocumentMCP (FastMCP)",
        [
            "tools:",
            "    list_documents() -> list[str]",
            "    read_document(doc_id) -> str",
            "    edit_document(doc_id, old_str, new_str) -> str",
            "resources:",
            "    docs://documents -> JSON array of ids",
            "    docs://documents/{doc_id} -> text",
            "prompts:",
            "    format(doc_id), summarize(doc_id)",
            "errors: ValueError -> MCP error result",
        ],
        kind="srv",
        stereotype="create_server(store)",
    )
    d.classbox(
        "claude",
        410,
        330,
        340,
        None,
        "Claude",
        [
            "+ async chat(messages, system, temperature,",
            "        stop_sequences, tools, thinking,",
            "        thinking_budget, max_tokens) -> Message",
            "+ add_user_message / add_assistant_message",
            "+ text_from_message(message) -> str",
        ],
        kind="app",
    )
    d.classbox(
        "client",
        830,
        40,
        290,
        None,
        "MCPClient",
        [
            "+ MCPClient(command, args, env, stderr_log)",
            "+ list_tools() -> list[Tool]",
            "+ call_tool(name, input) -> CallToolResult",
            "+ list_prompts() -> list[Prompt]",
            "+ get_prompt(name, args)",
            "        -> list[PromptMessage]",
            "+ read_resource(uri) -> Any (parsed)",
            "raises: ConnectionError, McpError,",
            "    ValueError (resource shape)",
        ],
        kind="int",
        stereotype="async context manager",
    )
    d.classbox(
        "errs",
        830,
        330,
        290,
        None,
        "CLIENT_ERRORS",
        [
            "McpError",
            "anyio.ClosedResourceError",
            "anyio.BrokenResourceError",
            "OSError (incl. ConnectionError)",
        ],
        kind="int",
        stereotype="tuple of types",
    )
    d.edge("mem", "top", "proto", "bottom", "implements", kind="inherit")
    d.edge("mem", "bottom", "nf", "top", "raises", kind="dep")
    d.edge(
        "srv",
        "left",
        "proto",
        "right",
        "uses only\nthe contract",
        kind="dep",
        s_f=0.27,
        d_f=0.5,
    )
    d.edge("client", "left", "srv", "right", "MCP\nover stdio", s_f=0.4, d_f=0.4)
    d.edge("client", "bottom", "errs", "top", "raises", kind="dep")
    diagrams.append(d)

    # 6. Startup sequence ------------------------------------------------------------------
    d = Diagram("sequence-startup", 1060, 560)
    startup_parts: list[tuple[str, int, str, Kind]] = [
        ("main", 90, "main.py", "app"),
        ("client", 290, "MCPClient", "int"),
        ("srv", 500, "Server subprocess", "srv"),
        ("app", 710, "CliApp", "ui"),
        ("chat", 920, "CliChat", "app"),
    ]
    for key, cx, label, kind in startup_parts:
        d.lifeline(key, cx, 30, 545, label, kind)
    d.self_msg("main", 90, "load .env, read_config()")
    d.msg("main", "client", 140, "async with MCPClient(...)")
    d.self_msg("client", 160, "open logs/doc_client.log")
    d.msg("client", "srv", 210, "spawn python mcp_server.py")
    d.msg("client", "srv", 245, "initialize")
    d.msg("srv", "client", 275, "capabilities", "return")
    d.msg("client", "main", 305, "connected client", "return")
    d.msg("main", "app", 340, "CliApp(CliChat(...)).initialize()")
    d.msg("app", "chat", 370, "list_docs_ids(), list_prompts()")
    d.msg("chat", "client", 400, "read_resource(docs://documents), list_prompts()")
    d.msg("client", "srv", 430, "resources/read, prompts/list")
    d.msg("srv", "client", 455, "ids, prompts", "return")
    d.msg("client", "app", 480, "ids, prompts -> completer, autosuggest", "return")
    d.msg("main", "app", 515, "run()  (read-answer loop)")
    diagrams.append(d)

    # 7. Query with @mention and tool use ------------------------------------------------------
    d = Diagram("sequence-query", 1290, 1020)
    query_parts: list[tuple[str, int, str, Kind]] = [
        ("user", 50, "User", "ui"),
        ("app", 180, "CliApp", "ui"),
        ("chat", 340, "CliChat / Chat", "app"),
        ("tm", 500, "ToolManager", "app"),
        ("claude", 660, "Claude", "app"),
        ("api", 820, "Anthropic API", "ext"),
        ("client", 990, "MCPClient", "int"),
        ("srv", 1170, "DocumentMCP server\n+ store", "srv"),
    ]
    for key, cx, label, kind in query_parts:
        d.lifeline(
            key,
            cx,
            40,
            1005,
            label,
            kind,
            actor=(key == "user"),
            w=200 if key == "srv" else None,
        )
    d.msg("user", "app", 100, "@report.pdf question")
    d.msg("app", "chat", 130, "run(query)")
    d.self_msg("chat", 150, "checkpoint = len(messages)")
    d.msg("chat", "client", 200, "read_resource(docs://documents)")
    d.msg("client", "srv", 225, "resources/read")
    d.msg("srv", "client", 248, "[ids]", "return")
    d.msg("client", "chat", 271, "ids", "return")
    d.msg("chat", "client", 300, "read_resource(docs://documents/report.pdf)")
    d.msg("client", "srv", 325, "resources/read")
    d.msg("srv", "client", 348, "text", "return")
    d.msg("client", "chat", 371, "content", "return")
    d.self_msg("chat", 390, "append user message:\nquery + <document> context", h=26)
    d.frame(255, 440, 1025, 495, "loop", "[until stop_reason != tool_use]")
    d.msg("chat", "tm", 480, "get_all_tools(clients)")
    d.msg("tm", "client", 505, "list_tools()  (tools/list)")
    d.msg("client", "tm", 528, "tools", "return")
    d.msg("tm", "chat", 551, "ToolParam list", "return")
    d.msg("chat", "claude", 585, "await chat(messages, tools)")
    d.msg("claude", "api", 610, "messages.create")
    d.msg("api", "claude", 633, "Message", "return")
    d.msg("claude", "chat", 656, "response (appended)", "return")
    d.frame(270, 675, 1000, 245, "alt", "[stop_reason == tool_use]")
    d.msg("chat", "tm", 715, "execute_tool_requests(response)")
    d.self_msg("tm", 728, "map tool -> owning client (list_tools)", h=18)
    d.msg("tm", "client", 772, "call_tool(read_document, {doc_id})")
    d.msg("client", "srv", 797, "tools/call -> store.get()")
    d.msg("srv", "client", 820, "CallToolResult", "return")
    d.msg("client", "tm", 843, "result", "return")
    d.msg("tm", "chat", 866, "tool_result blocks (appended)", "return")
    d.divider(270, 885, 1000, "[else] final text -> leave loop")
    d.msg("chat", "app", 960, "final text", "return")
    d.msg("app", "user", 985, "print Response", "return")
    diagrams.append(d)

    # 8. /format command -------------------------------------------------------------------------
    d = Diagram("sequence-format-command", 1240, 880)
    format_cmd_parts: list[tuple[str, int, str, Kind]] = [
        ("user", 50, "User", "ui"),
        ("app", 190, "CliApp", "ui"),
        ("chat", 380, "CliChat / Chat\n(+ ToolManager)", "app"),
        ("client", 610, "MCPClient", "int"),
        ("srv", 880, "DocumentMCP server\n+ store", "srv"),
        ("claude", 1110, "Claude\n(Anthropic API)", "app"),
    ]
    for key, cx, label, kind in format_cmd_parts:
        d.lifeline(
            key,
            cx,
            40,
            865,
            label,
            kind,
            actor=(key == "user"),
            w=180 if key in ("chat", "srv", "claude") else None,
        )
    d.msg("user", "app", 100, "/format plan.md")
    d.msg("app", "chat", 130, 'run("/format plan.md")')
    d.self_msg("chat", 150, "_process_command:\nformat, {doc_id: plan.md}", h=26)
    d.msg("chat", "client", 210, 'get_prompt("format", {doc_id})')
    d.msg("client", "srv", 235, "prompts/get")
    d.self_msg("srv", 250, "_require_doc(plan.md)", h=20)
    d.msg("srv", "client", 295, "[user message: rewrite via tools]", "return")
    d.msg("client", "chat", 320, "PromptMessage list", "return")
    d.self_msg("chat", 335, "convert to MessageParam, append", h=20)
    d.frame(300, 385, 915, 405, "loop", "[agent loop, same as a plain query]")
    d.msg("chat", "claude", 425, "chat(messages, tools)")
    d.msg("claude", "chat", 450, "tool_use: read_document(plan.md)", "return")
    d.msg("chat", "client", 480, "call_tool(read_document)")
    d.msg("client", "srv", 505, "tools/call -> store.get()")
    d.msg("srv", "client", 528, "current text", "return")
    d.msg("client", "chat", 551, "tool_result", "return")
    d.msg("chat", "claude", 585, "chat(... tool_result)")
    d.msg("claude", "chat", 610, "tool_use: edit_document(old_str, new_str)", "return")
    d.msg("chat", "client", 640, "call_tool(edit_document)")
    d.msg("client", "srv", 665, "tools/call -> unique match? store.update()")
    d.msg("srv", "client", 690, '"Doc plan.md updated"', "return")
    d.msg("client", "chat", 713, "tool_result", "return")
    d.msg("chat", "claude", 745, "chat(... tool_result)")
    d.msg("claude", "chat", 770, "end_turn: summary of changes", "return")
    d.msg("chat", "app", 820, "final text", "return")
    d.msg("app", "user", 845, "print Response", "return")
    d.note(
        "n1",
        430,
        800,
        300,
        56,
        "Unknown doc id, missing or unknown prompt:\nMcpError -> history rolled back,\nCLI prints one line",
    )
    diagrams.append(d)

    # 9. Turn handling and failures (activity) ---------------------------------------------------
    d = Diagram("activity-turn-errors", 860, 840)
    d.terminal("read", 330, 20, 240, 40, "Read input (prompt_async)", "ui")
    d.diamond("eof", 360, 90, 180, 70, "Ctrl+C or\nCtrl+D?")
    d.terminal("exit", 640, 105, 120, 40, "Exit")
    d.diamond("blank", 360, 190, 180, 70, "Blank input?")
    d.box("ckpt", 330, 290, 240, 50, "Chat.run\ncheckpoint = len(messages)", "app")
    d.box(
        "ctx",
        330,
        370,
        240,
        56,
        "/command -> get_prompt\nor @mentions -> read_resource",
        "app",
    )
    d.box("loop", 330, 456, 240, 50, "Agent loop\nClaude <-> tools", "app")
    d.diamond("failed", 360, 536, 180, 70, "Turn failed?")
    d.box("reply", 330, 650, 240, 44, "Print Response", "ui")
    d.box(
        "restore", 40, 546, 240, 50, "Restore history to checkpoint,\nre-raise", "err"
    )
    d.diamond("known", 70, 630, 180, 70, "API error or\nCLIENT_ERRORS?")
    d.box("report", 40, 750, 240, 44, "Print 'Error: Type: message'", "err")
    d.terminal("crash", 300, 760, 210, 40, "Propagate (a real bug)", "err")
    d.edge("read", "bottom", "eof", "top")
    d.edge("eof", "right", "exit", "left", "yes")
    d.edge("eof", "bottom", "blank", "top", "no")
    d.edge("blank", "left", "read", "left", "yes", d_f=0.7, via=[(250, 225), (250, 48)])
    d.edge("blank", "bottom", "ckpt", "top", "no")
    d.edge("ckpt", "bottom", "ctx", "top")
    d.edge("ctx", "bottom", "loop", "top")
    d.edge("loop", "bottom", "failed", "top")
    d.edge("failed", "bottom", "reply", "top", "no")
    d.edge("failed", "left", "restore", "right", "yes")
    d.edge("restore", "bottom", "known", "top")
    d.edge("known", "bottom", "report", "top", "yes")
    d.edge("known", "right", "crash", "left", "no", via=[(290, 665), (290, 780)])
    d.edge(
        "reply",
        "right",
        "read",
        "right",
        "next input",
        via=[(800, 672), (800, 40)],
        label_pos=0.5,
    )
    d.edge(
        "report",
        "left",
        "read",
        "left",
        "next input",
        d_f=0.3,
        via=[(15, 772), (15, 32)],
        label_pos=0.86,
    )
    diagrams.append(d)
    return diagrams


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("diagrams")
    for d in build():
        print("wrote", save_diagram(d, out))


if __name__ == "__main__":
    main()
