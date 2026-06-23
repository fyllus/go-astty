class ExecutionError(Exception):
    """Exception raised for execution errors with dynamic case dictionary."""

    _cases = {
        "none_assignment": "Property/Attribute cannot be None: expected {expected}, got <{got}>",
        "unable_assignment": "Unable to assign type <{got}>: expected {expected}",
        "invalid_assignment": "Invalid Assignment: expected {expected}, cannot use <{got}>",
        "index_not_found": "Index not found in <type {got}>",
        "all_must_be": "All values must be <type {got}>",
        "invalid_type": "Trying to set invalid type of <{got}>, but is expected <{expected}>",
        "empty_value_error": "Arguments collection cannot be empty",
    }

    def __init__(self, case: str, obj: object, *expected: type) -> None:
        expected_types = ", ".join(f"<{t.__name__}>" for t in expected)
        got_type = type(obj).__name__
        template = self._cases.get(case, "Unknown error case with <{got}>")
        self.message = template.format(expected=expected_types, got=got_type)
        super().__init__(self.message)
