import logging

RED = "\033[31m"
BLUE = "\033[34m"
RESET = "\033[0m"
CROSS = "\u274c"
CHECK = "\u2705"


class ColorAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"{BLUE}{msg}{RESET}", kwargs
