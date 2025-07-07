import re
import chainlit as cl
from agent_backend import run_agent

# Author name to display in chat
AUTHOR_NAME = "Content IQ"

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="Welcome to Content IQ!",
        author=AUTHOR_NAME
    ).send()
    await cl.Message(
        content=(
            "🔍 **What I can do for you:**\n\n"
            "- Search across your Azure Blob Storage\n"
            "- Fetch or preview specific documents\n"
            "- Answer questions based on document contents\n\n"
            "---\n"
        ),
        author=AUTHOR_NAME
    ).send()
    

@cl.on_message
async def main(message: cl.Message):
    response = run_agent(message.content)
    if isinstance(response, dict):
        response = response.get("response", "")
    # Convert HTML <a> tags to Markdown
    response = re.sub(r'<a\s+href="([^\"]+)">([^<]+)</a>', r"[\2](\1)", response)
    await cl.Message(
        content=response,
        author=AUTHOR_NAME
    ).send()
