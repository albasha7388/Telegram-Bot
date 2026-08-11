## 🤖 AI Model Instructions (Vibe Coding)
This file is part of a technical reference for a **Python Telegram bot project**. Apply only the concepts from this file that you actually need while writing or improving the current code (e.g., adding docstrings to a new function, type hints for a function's parameters, or writing/updating the project's README). Do not apply anything unnecessary or unfit for the current task — for example, there's no need to add advanced types (Generics, Protocols) unless there's an actual need for them in the code.

---

# Documenting Python Code

> "Just cheat sheets for you and your clients."

---

## 1. Introduction

Well-documented code can save countless hours of debugging and troubleshooting, by providing clear guidance and explaining the code's functions and usage.

### 1.1 Types of Documentation

- **Internal Documentation:** Consists of comments and docstrings within the codebase that explain the purpose, logic, and usage of different parts of the program.

- **External Documentation:** Includes README files, project function documentation, user guides, and developer guides that describe how to use the software, how it works, and how to contribute to it.

**I recommend writing both types of documentation to make your application as clear as possible, both for the user and the team.**

---

## 2. Code Comments and Docstrings

### 2.1 Inline Comments

As you already know, comments in Python start with the hash sign (#) and should explain "why" behind a piece of code rather than "how".

**Best practices:**
- Inline comments are placed on the same line as the code statement.
- They should be used to clarify complex parts of the code.
- They should be meaningful and add value to understanding the code.

**Bad example:** Comments that are redundant and just repeat what the code does.

**Good example:** Provides a justification for why the operation is implemented, adding value to code readability.

**Note:** One of Python's greatest achievements is that the code is mostly self-explanatory in most cases, but that doesn't mean we should forget inline comments or docstrings.

---

### 2.2 Docstrings

**Docstring standards and conventions:**
Docstrings provide a built-in way to document Python modules, functions, classes, and methods. They're written between triple quotes (""") and should follow the PEP 257 conventions.

**Important:** A good docstring should describe what the function/class does, its parameters, return values, and any exceptions it raises.

---

### 2.3 Docstring Components

1. **Brief Description:** A short summary of what the function does. It should be in imperative mood (e.g., "Return" instead of "Returns").

2. **Parameters Section:** Lists each parameter, its expected type, and a short description. Although types can be indicated in the function's signature (from Python 3.5+), repeating them in the docstring can enhance readability and clarity.

3. **Returns Section:** Describes the return value's type and purpose.

A good docstring should also clarify any exception that might be raised, and it's helpful to include a usage example when needed.

---

## 3. Annotations (Type Hints)

Python's type system, although dynamic at runtime, supports optional type hints that enable static type checking. This feature, introduced in Python 3.5 through PEP 484, allows developers to annotate their code with type hints, making it more readable, maintainable, and less error-prone.

**The main idea behind annotations is that we specify the expected data type that should be passed to the function/method or variable.**

**Very important:** Annotations don't guarantee that exactly this type will be passed — they aren't enforcement, they're more for documentation.

---

### 3.1 Basic Types

These are the basic types that correspond to Python's built-in types:

- **int:** For integers.
- **float:** For floating-point numbers.
- **bool:** For boolean values (True or False).
- **str:** For strings.
- **bytes:** For byte sequences.

---

### 3.2 Composite Types

Composite types, also known as collection types, allow you to specify the type of elements in a collection:

- **list[Type]:** A list where all elements are of the specified type.
- **tuple[Type, ...]:** A tuple with specified element types.
- **dict[KeyType, ValueType]:** A dictionary with specified key and value types.
- **set[Type]:** A set where all elements are of the specified type.

---

### 3.3 Specialized Types

The `typing` module in Python also includes more specialized types for more complex scenarios:

- **Optional[Type]:** Indicates a variable that can be of the specified type or None.
- **Union[Type1, Type2, ...]:** Indicates a variable that can be any of the specified types.
- **Callable[[ArgType1, ArgType2, ...], ReturnType]:** Represents a callable object (a function or an object with `__call__`) with specified argument and return types.
- **Any:** A special type indicating the variable can be of any type. Use it sparingly, as it disables type checking for that variable.

**Note:** Using `Any` is a very bad practice that can lead to unpleasant consequences and errors, if we perform an operation specific to certain data types.

---

### 3.4 Type Aliases

Type aliases let you define custom names for complex type hints, improving code readability.

---

### 3.5 Advanced Type Hints

- **Generics:** Python's `typing` module allows defining generic types, making it possible to create container types that can hold objects of any type, determined at runtime. This is particularly useful for classes that act as wrappers or containers for other objects.

- **NewType:** You can create distinct types that are treated as separate types by static type checkers, but are equivalent at runtime to their base types. This is useful for adding semantic meaning to basic types.

- **Literal Types:** Literal types indicate that a variable or parameter can only take specific literal values. This is particularly useful when a function accepts a limited set of string or integer values.

- **TypedDict:** For dictionaries with a fixed set of keys, where each key has a specific type, `TypedDict` provides a way to explicitly define type hints for each key-value pair.

- **Protocols:** Introduced in Python 3.8, Protocols allow for duck typing, by defining a set of methods that a class must implement without specifying a particular inheritance chain.

---

### 3.6 Setting Up a Type Checker

When it comes to applying and checking type hints in your Python code, **Mypy** is the recommended tool. Mypy is a static type checker that helps you catch type errors before runtime.

**Quick start:**
- **Installation:** Install Mypy using pip.
- **Basic usage:** Check a single Python file for type errors.
- **Checking multiple files:** You can also check multiple files or entire directories.
- **Configuration:** For more complex projects, Mypy can be configured via a `mypy.ini` or `pyproject.toml` file in your project's root directory.

**Some useful flags:**
- `--ignore-missing-imports`: Ignores errors related to missing import statements.
- `--strict`: Enables all of Mypy's strictness flags for comprehensive checks.
- `--follow-imports=silent`: Follows import statements but doesn't check the imported modules.
- `--exclude`: Excludes specific files or directories from the check.

---

## 4. External Documentation

### 4.1 The README File

The README file is often the first document readers encounter in your project. It's not just an introduction; it's your project's handshake with the outside world. A good README effectively tells the purpose of your project, how to use it, and how others can contribute.

**Components:**
- **Project name and logo:** Start with the project name, and if you have one, include a logo.
- **Introduction:** A brief description of the project and its purpose.
- **Installation instructions:** Clear and concise steps to run your project on another machine.
- **Usage:** Examples of how to use your project, including code snippets and command-line examples.
- **Contributing:** Guidelines on how others can contribute to your project, including coding standards, testing procedures, and how to submit pull requests.
- **License:** Information about the project's license, allowing others to understand how they can use, modify, and distribute your work.
- **Acknowledgements:** Recognition of contributors, external resources, or dependencies.

---

### 4.2 End-Users

Try to include the following in your end-user documentation:

- **Getting Started:** A beginner-friendly introduction to the project, highlighting core functionality and simple use cases.
- **Step-by-Step Guides:** Detailed tutorials that address specific tasks or problems, guiding the user from start to finish.
- **FAQs:** A list of frequently asked questions (and their answers) that users might have when using your project.

**Note:** You'll need to learn more about documentation hosting and building tools like **Sphinx**, **MkDocs**, and **Read the Docs** to present your documentation to the world.

**Don't forget to update the documentation regularly to reflect changes in the project. Always keep it up to date!**
