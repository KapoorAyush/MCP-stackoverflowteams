import os
import html
from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP
from urllib.parse import quote

# Load environment variables
load_dotenv()
PAT = os.environ.get("API_KEY")
TEAM = os.environ.get("TEAM")
BASE_URL = os.environ.get("BASE_URL")

# MCP Server
mcp = FastMCP("StackOverflow MCP")

# Helper
def clean_html(html_text: str) -> str:
    """Simple clean HTML to Markdown-like text."""
    text = html.unescape(html_text)
    text = text.replace("<p>", "").replace("</p>", "\n\n")
    text = text.replace("<code>", "`").replace("</code>", "`")
    text = text.replace("<strong>", "**").replace("</strong>", "**")
    text = text.replace("<em>", "*").replace("</em>", "*")
    return text.strip()

async def http_get(url: str, params: dict) -> dict:
    headers = {"X-API-Access-Token": PAT}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

# 1. Search Questions
@mcp.tool(description="Search Stack Overflow Teams for relevant questions matching a query")
async def stackoverflow_search_questions(query: str) -> str:
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "team": TEAM,
        "pagesize": 5,
        "filter": "!9_bDE(fI5"
    }
    url = f"{BASE_URL}/search/advanced"
    try:
        data = await http_get(url, params)
        if not data.get("items"):
            return "No relevant questions found."
        results = []
        for q in data["items"]:
            title = clean_html(q.get("title", ""))
            link = q.get("link", "#")
            body = clean_html(q.get("body", ""))
            results.append(f"### {title}\n{body}\n🔗 [View Question]({link})")
        return "\n\n".join(results)
    except Exception as e:
        return f"HTTP Error: {str(e)}"

# 2. Search Answers
@mcp.tool(description="Search Stack Overflow Teams for relevant answers matching a query")
async def stackoverflow_search_answers(query: str) -> str:
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "team": TEAM,
        "pagesize": 5
    }
    url = f"{BASE_URL}/search/excerpts"
    try:
        data = await http_get(url, params)
        items = [i for i in data.get("items", []) if i.get("item_type") == "answer"]
        if not items:
            return "No relevant answers found."
        results = []
        for ans in items:
            excerpt = clean_html(ans.get("excerpt", ""))
            qid = ans.get("question_id")
            link = f"https://{TEAM}.stackoverflowteams.com/c/{TEAM}/questions/{qid}" if qid else "#"
            results.append(f"**Answer Excerpt:**\n{excerpt}\n🔗 [View Answer]({link})")
        return "\n\n".join(results)
    except Exception as e:
        return f"HTTP Error: {str(e)}"

# 3. Search Excerpts (Questions + Answers)
@mcp.tool(description="Search Stack Overflow Teams excerpts matching a query (questions and answers)")
async def stackoverflow_search_excerpts(query: str) -> str:
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "team": TEAM,
        "pagesize": 5
    }
    url = f"{BASE_URL}/search/excerpts"
    try:
        data = await http_get(url, params)
        if not data.get("items"):
            return "No relevant excerpts found."
        results = []
        for item in data["items"]:
            item_type = item.get("item_type", "unknown")
            title = clean_html(item.get("title", ""))
            excerpt = clean_html(item.get("excerpt", ""))
            qid = item.get("question_id")
            link = f"https://{TEAM}.stackoverflowteams.com/c/{TEAM}/questions/{qid}" if qid else "#"
            results.append(
                f"**Type:** {item_type}\n**Title:** {title}\n{excerpt}\n🔗 [View Full Post]({link})"
            )
        return "\n\n".join(results)
    except Exception as e:
        return f"HTTP Error: {str(e)}"

# 4. Fetch full question by ID
@mcp.tool(description="Fetch full question (body and answers) from Stack Overflow Teams given a question ID")
async def stackoverflow_fetch_question_by_id(question_id: str) -> str:
    try:
        q_url = f"{BASE_URL}/questions/{question_id}"
        a_url = f"{BASE_URL}/questions/{question_id}/answers"

        q_data = await http_get(q_url, {"team": TEAM, "filter": "!9_bDE(fI5"})
        a_data = await http_get(a_url, {"team": TEAM, "filter": "!9_bDE(fI5"})

        if not q_data.get("items"):
            return "Question not found."

        question = q_data["items"][0]
        title = clean_html(question.get("title", ""))
        body = clean_html(question.get("body", ""))

        response = f"## {title}\n\n{body}\n\n"

        answers = a_data.get("items", [])
        if answers:
            response += "\n\n### Top Answers:\n"
            for ans in answers:
                body = clean_html(ans.get("body", ""))
                score = ans.get("score", 0)
                response += f"\n**Score:** {score}\n{body}\n\n---"
        else:
            response += "\n\n_No answers found._"

        return response

    except Exception as e:
        return f"HTTP Error: {str(e)}"

# 5. Search questions by tags
@mcp.tool(description="Search Stack Overflow Teams questions by tags")
async def stackoverflow_search_by_tags(tags: str) -> str:
    params = {
        "order": "desc",
        "sort": "activity",
        "tagged": tags,
        "team": TEAM,
        "pagesize": 5
    }
    url = f"{BASE_URL}/questions"
    try:
        data = await http_get(url, params)
        if not data.get("items"):
            return "No questions found for the given tags."
        results = []
        for q in data["items"]:
            title = clean_html(q.get("title", ""))
            link = q.get("link", "#")
            results.append(f"**{title}**\n🔗 [View Question]({link})")
        return "\n\n".join(results)
    except Exception as e:
        return f"HTTP Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
