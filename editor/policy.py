"""Server-side prompt and policy assembly.

The client cannot set these. They are built from the stored chapter.
"""


def system_instructions() -> str:
    """Policy for the only model provider. The writer keeps the words."""
    return (
        "Suggest, question, and highlight. Do not write the story.\n"
        "Never replace chapter text unless the writer takes a separate, "
        "explicit action that names that replacement.\n"
        "The writer can dismiss or ignore every finding. "
        "Dismiss does not edit the chapter.\n"
        "No silent rewrite of a draft or a published chapter.\n"
        "This is assistance, not authorship.\n"
        "No generate chapter as a primary action.\n"
        "Ask questions and point at the writer's words. "
        "Do not return replacement prose."
    )


def chapter_prompt(chapter) -> str:
    """The user message: the stored story and chapter, nothing from the client."""
    return (
        f"Story: {chapter.story.title}\n"
        f"Chapter {chapter.number}: {chapter.title}\n"
        "\n"
        f"{chapter.content}"
    )
