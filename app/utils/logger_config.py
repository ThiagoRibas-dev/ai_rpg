import logging

class EmojiFormatter(logging.Formatter):
    """
    A custom log formatter that adds an emoji to the beginning of the log message
    based on the log level.
    """
    
    # Define the emojis for each log level
    LEVEL_EMOJIS = {
        logging.DEBUG: "🐛",
        logging.INFO: "✅",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
    }

    def format(self, record):
        """
        Overrides the default format method to prepend the emoji.
        """
        # Get the original formatted message
        s = super().format(record)
        
        # Find the corresponding emoji, default to empty string if not found
        emoji = self.LEVEL_EMOJIS.get(record.levelno, "")
        
        # Prepend the emoji to the message
        return f"{emoji} {s}"

def setup_logging():
    """
    Configures the root logger with the custom EmojiFormatter.
    This function should be called once at the application's entry point.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # Set the lowest level to capture all messages

    # Create a console handler
    console_handler = logging.StreamHandler()

    # Define the format for the log messages (without the emoji)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create an instance of our custom formatter
    formatter = EmojiFormatter(log_format)
    
    # Set the formatter for the handler
    console_handler.setFormatter(formatter)

    # Remove any existing handlers to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    # Add the new handler to the root logger
    root_logger.addHandler(console_handler)
