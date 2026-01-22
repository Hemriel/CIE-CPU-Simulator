from textual.widgets import Label

class VSpacer(Label):
    """A vertical spacer widget to create space between other widgets."""

    DEFAULT_CSS = """
    VSpacer {
        height: 1fr;
    }
    """