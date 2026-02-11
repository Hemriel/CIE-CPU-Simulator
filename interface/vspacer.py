from textual.widgets import Label

class VSpacer(Label):
    """A vertical spacer widget for creating flexible space between UI elements.
    
    This widget expands to fill available vertical space, useful for distributing
    child widgets vertically with gaps. It wraps Textual's Label with a CSS rule
    that sets height to 1fr (one fractional unit), allowing the space to grow and
    shrink as the terminal is resized.
    
    Example use: space out register displays in a column so they're evenly spaced.
    """

    DEFAULT_CSS = """
    VSpacer {
        height: 1fr;
    }
    """