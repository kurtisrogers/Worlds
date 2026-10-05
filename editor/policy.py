"""Server-side prompt and policy assembly.

The client cannot set these. They are built from the stored chapter.
"""


def system_instructions() -> str:
    """Policy for the only model provider. The writer keeps the words."""
    return (
        "Suggest and question. Do not write the story.\n"
        "The model never writes the chapter.\n"
        "The writer can dismiss or ignore every finding. "
        "Dismiss does not edit the chapter.\n"
        "No silent rewrite of a draft or a published chapter.\n"
        "This is assistance, not authorship.\n"
        "No generate chapter as a primary action.\n"
        "Ask questions about the writer's words. "
        "Do not return a rewrite."
    )


def chapter_prompt(chapter) -> str:
    """The user message: the stored story and chapter, nothing from the client."""
    return (
        f"Story: {chapter.story.title}\n"
        f"Chapter {chapter.number}: {chapter.title}\n"
        "\n"
        f"{chapter.content}"
    )


def review_instructions() -> str:
    """Same rules as an assist, plus the review output shape."""
    return (
        system_instructions()
        + "\n"
        + "Return questions and locations in the writer's existing text.\n"
        + "Do not return replacement prose.\n"
        + "Reply with JSON only. "
        + "Each finding has an anchor and a question: "
        + '{"findings":[{"anchor":"exact words already in the chapter",'
        + '"question":"a question?"}]}\n'
        + "Locations must be copied from the chapter. "
        + "If nothing is proved, return an empty findings list."
    )


def review_prompt(chapter) -> str:
    """This chapter, plus titles around it. Not other manuscripts or payments."""
    story = chapter.story
    previous = (
        story.chapters.filter(number__lt=chapter.number)
        .order_by("-number")
        .values_list("title", flat=True)
        .first()
    )
    following = (
        story.chapters.filter(number__gt=chapter.number)
        .order_by("number")
        .values_list("title", flat=True)
        .first()
    )
    lines = [f"Story: {story.title}"]
    synopsis = (story.synopsis or "").strip()
    if synopsis:
        lines.append(f"Synopsis: {synopsis}")
    lines.append(
        f"Chapter {chapter.number} of {story.chapters.count()}: {chapter.title}"
    )
    lines.append(f"Previous chapter title: {previous or '(none)'}")
    lines.append(f"Next chapter title: {following or '(none)'}")
    lines.append("")
    lines.append(chapter.content)
    return "\n".join(lines)
