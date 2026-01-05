"""Custom exceptions for configuration loading and validation.

This module defines custom exception classes for configuration-related errors
to provide clear, actionable error messages when configuration loading or
validation fails.
"""



class ConfigurationError(Exception):
    """Exception raised when configuration loading or validation fails.

    This exception provides structured error information including the filename,
    field name, and error message to help diagnose configuration issues quickly.

    Attributes:
        message: The error message describing what went wrong.
        filename: Optional name of the configuration file that caused the error.
        field: Optional name of the specific configuration field that failed.

    Examples:
        >>> # Basic usage with just a message
        >>> raise ConfigurationError("Invalid configuration format")

        >>> # With filename context
        >>> raise ConfigurationError(
        ...     "Missing required field",
        ...     filename="config/global.yaml"
        ... )

        >>> # With full context (filename and field)
        >>> raise ConfigurationError(
        ...     "Value must be positive",
        ...     filename="config/projects/example.yaml",
        ...     field="database.pool_size"
        ... )

        >>> # Catching and inspecting the error
        >>> try:
        ...     raise ConfigurationError(
        ...         "Invalid value",
        ...         filename="config.yaml",
        ...         field="timeout"
        ...     )
        ... except ConfigurationError as e:
        ...     print(e.message)
        ...     print(e.filename)
        ...     print(e.field)
        ...     print(str(e))
    """

    def __init__(
        self,
        message: str,
        filename: str | None = None,
        field: str | None = None,
    ) -> None:
        """Initialize the ConfigurationError.

        Args:
            message: The error message describing what went wrong.
            filename: Optional name of the configuration file that caused the error.
            field: Optional name of the specific configuration field that failed.
        """
        self.message = message
        self.filename = filename
        self.field = field
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with optional context.

        Returns:
            str: A formatted error message including filename and field if available.
        """
        parts = []

        if self.filename:
            parts.append(f"Configuration error in '{self.filename}'")
        else:
            parts.append("Configuration error")

        if self.field:
            parts.append(f"at field '{self.field}'")

        # Build the final message, properly handling the colon
        if parts:
            base = " ".join(parts)
            return f"{base}: {self.message}"
        else:
            return self.message

    def __str__(self) -> str:
        """Return a string representation of the error for debugging.

        Returns:
            str: A formatted error message with all available context.

        Examples:
            >>> error = ConfigurationError("Invalid value", filename="config.yaml", field="port")
            >>> str(error)
            "Configuration error in 'config.yaml' at field 'port': Invalid value"

            >>> error = ConfigurationError("Missing file", filename="config.yaml")
            >>> str(error)
            "Configuration error in 'config.yaml': Missing file"

            >>> error = ConfigurationError("Invalid format")
            >>> str(error)
            "Configuration error: Invalid format"
        """
        return self._format_message()

    def __repr__(self) -> str:
        """Return a detailed representation of the error for debugging.

        Returns:
            str: A representation showing the class name and all attributes.

        Examples:
            >>> error = ConfigurationError("Invalid", filename="config.yaml", field="db.url")
            >>> repr(error)
            "ConfigurationError(message='Invalid', filename='config.yaml', field='db.url')"
        """
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"filename={self.filename!r}, "
            f"field={self.field!r})"
        )
