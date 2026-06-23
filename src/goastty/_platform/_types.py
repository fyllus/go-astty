from typing import Any, Iterator, get_type_hints


class UnifiedStruct:
    pass


class XMetaClass(type):
    """Metaclass that extracts type hints from subclasses to generate validation blueprints."""

    def __new__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any]):

        new_class = super().__new__(cls, name, bases, attrs)
        # Avoid generating defines for the base structural class itself
        if name != "XStruct":
            new_class.__defines__ = get_type_hints(new_class)
        return new_class


class static_eval:
    def __init__(self) -> None:
        pass

    def set(self, _name: str, _type: type, _value: Any) -> None:
        if not isinstance(_value, _type):
            raise TypeError(
                f"Expected static type of <{_type.__name__}>, but given <{type(_value).__name__}>"
            )
        super().__setattr__(_name, _value)

    def get(self, _name: str) -> Any:
        return getattr(self, _name, None)


class static_struct(static_eval, metaclass=XMetaClass):
    def __init__(self) -> None:
        for name in self.types.keys():
            super().__setattr__(name, None)

    @property
    def types(self) -> dict:
        return getattr(self, "__types__", {})


class XStruct(metaclass=XMetaClass):
    """Base interface for structured, strictly typed data containers."""

    def __init__(self) -> None:
        """Instantiate an XVar container for each declared struct field."""
        for name in self.struct_types.keys():
            super().__setattr__(name, XVar(self.struct_types[name]))

    @staticmethod
    def typage(x: str, y: str):
        return f"< name: {x}, value: {y} >"

    @staticmethod
    def match_type(name: Any, value: Any, type_name: type, type_value: type) -> tuple:
        """Validate that both name and value conform to their expected types, respecting inheritance."""
        value_t = (
            type_value.__name__
            if isinstance(value, type_value)
            else type(value).__name__
        )
        name_t = (
            type_name.__name__ if isinstance(name, type_name) else type(name).__name__
        )

        expected = XStruct.typage(type_name.__name__, type_value.__name__)
        given = XStruct.typage(name_t, value_t)
        if expected == given:
            return name, value

        raise TypeError(f"Expected {expected} but {given} was given")

    @property
    def struct_types(self):
        """Return the dictionary mapping field names to their expected types."""
        return getattr(self, "__defines__", {})

    @property
    def struct_tuples(self):
        """Return the of tuples mapping fields ((names), (types), (values))"""
        names = [name for name in self.struct_items.keys()]
        values = [getattr(self, name).value for name in names]
        typages = [getattr(self, name).typage for name in names]
        return tuple(names), tuple(typages), tuple(values)

    @property
    def struct_name(self) -> str:
        """Return the class name of the structural object."""
        return f"{self.__class__.__name__}"

    @property
    def struct_json(self) -> str:
        return json.dumps(self.struct_items, indent=4, ensure_ascii=True)

    @property
    def struct_items(self) -> dict:
        """Return a dictionary mapping field names to their internal primitive values."""
        output = {}
        for key in self.struct_types.keys():
            value = getattr(self, key).value
            if isinstance(value, XStruct):
                value = value.struct_items
            output[key] = value
        return output

    @property
    def struct_lines(self):
        """Yield formatted definition strings for each field container."""
        for name in self.struct_items.keys():
            yield f"{getattr(self, name).typage} {name}={getattr(self, name).value}"

    def __getitem__(self, name: str) -> Any:
        """Retrieve the raw XVar container instance via key lookup."""
        return self.__getattr__(name)

    def __getattr__(self, name: str) -> Any:
        """Retrieve the raw XVar container instance, validation access boundaries."""
        if name not in self.struct_types:
            raise NameError(
                f"Name <{name}> was not defined in <{self.__class__.__name__}>"
            )
        return getattr(self, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Intercept attribute assignment to validate and set the inner value via XVar."""
        pointer = self.__getitem__(name)
        pointer <= self.__compiled_value__(value, name)

    def __compiled_value__(self, value: Any, name: str) -> Any:
        """Intercepts assignment as a final hook to mutate or sanitize the value before storage."""
        return value

    def __setitem__(self, name: str, value: Any) -> None:
        """Intercept key assignment to validate and set the inner value via XVar."""
        self.__setattr__(name, value)

    def __repr__(self) -> str:
        """Return a string representation of the struct layout and values."""
        return f"{self.struct_name} <= ( {', '.join([line for line in self.struct_lines])} )"

    def __iter__(self) -> Iterator:
        """Return an iterator over the field names."""
        return iter(self.struct_items)

    def __len__(self) -> int:
        """Return the total number of fields defined in the struct."""
        return len(self.struct_items)
