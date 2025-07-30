TOKEN_LIMIT_ERROR_MESSAGE = "Not enough Credits available for this operation"

class TokenLimitError(Exception):
    """Exception raised when a user does not have enough tokens for an operation."""
    def __init__(self, message: str = TOKEN_LIMIT_ERROR_MESSAGE):
        self.message = message
        super().__init__(self.message) 