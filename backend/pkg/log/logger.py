import sys
from typing import Any, Dict

from loguru import logger


class Logger:
    """Console-only logger configuration"""

    def __init__(self) -> None:
        # Remove any existing handlers
        logger.remove()

        # Define a clean, colorized console format with extra fields
        log_format = (
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[filename]}:{extra[line_no]}</cyan> | "
            "{extra[context]} | "  # Add extra fields section
            "<cyan>{message}</cyan>"
        )

        # Add console handler only
        logger.add(
            sys.stdout,  # Use stdout instead of stderr for cleaner output
            format=log_format,
            level="DEBUG",
            colorize=True,
            backtrace=False,  # Disable traceback for cleaner error messages
            diagnose=False,  # Disable diagnosis for cleaner error messages
        )

    def _get_caller_info(self) -> dict[str, Any]:
        """Get caller's filename and line number"""
        import inspect

        frame = inspect.currentframe()
        # Get the caller's frame (2 frames up from current frame)
        caller_frame = frame.f_back.f_back if frame and frame.f_back else None

        if caller_frame:
            filename = caller_frame.f_code.co_filename.split("/")[-1]
            line_no = caller_frame.f_lineno
            return {"filename": filename, "line_no": line_no, "context": ""}
        return {"filename": "unknown", "line_no": 0, "context": ""}

    def _format_extra(self, extra: dict[str, Any] | None) -> str:
        """Format extra fields into a string"""
        if not extra:
            return ""
        return " ".join(f"{k}={v}" for k, v in extra.items())

    def info(self, message: str, extra: dict[str, Any] | None = None) -> None:
        caller_info = self._get_caller_info()
        caller_info["context"] = self._format_extra(extra)
        logger.bind(**caller_info).info(message)

    def error(
        self, message: str, exc_info: bool = False, extra: dict[str, Any] | None = None
    ) -> None:
        caller_info = self._get_caller_info()
        caller_info["context"] = self._format_extra(extra)
        logger.bind(**caller_info).error(message)
        if exc_info:
            import traceback

            logger.bind(**caller_info).error(traceback.format_exc())

    def debug(self, message: str, extra: dict[str, Any] | None = None) -> None:
        caller_info = self._get_caller_info()
        caller_info["context"] = self._format_extra(extra)
        logger.bind(**caller_info).debug(message)

    def warning(self, message: str, extra: dict[str, Any] | None = None) -> None:
        caller_info = self._get_caller_info()
        caller_info["context"] = self._format_extra(extra)
        logger.bind(**caller_info).warning(message)


# Dictionary to store named logger instances
_loggers: Dict[str, Logger] = {}


def get_logger(name: str = "default") -> Logger:
    """Return a named instance of the Logger class.
    
    Args:
        name: Optional name for the logger context. Defaults to "default".
        
    Returns:
        A Logger instance.
    """
    global _loggers
    if name not in _loggers:
        _loggers[name] = Logger()
    return _loggers[name]
