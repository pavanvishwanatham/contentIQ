@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="# Content IQ",
        author=AUTHOR_NAME
    ).send()
    await cl.Message(
        content=(
            "> Welcome to Content IQ! \n"
            "> \n"
            "> This assistant helps you search and explore documents stored in Azure Blob Storage. "
            "Ask me to find specific documents or ask questions based on their content.\n"
            "---\n"
            "![Logo](wocircle.png)"  # If you want to show an image and the file exists
        ),
        author=AUTHOR_NAME
    ).send()