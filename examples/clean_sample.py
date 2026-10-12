"""A small, clean Python file for trying the analyzer."""


def greeting(name: str) -> str:
    if not name:
        return "Hello, visitor!"
    return "Hello, {}!".format(name)
