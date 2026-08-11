## 🤖 AI Model Instructions (Vibe Coding)
This file is part of a technical reference for a **Python Telegram bot project**. Apply only the concepts or practices from this file that you actually need while working on the current part of the project (e.g., writing tests for command handlers, message parsing, or database logic). Do not apply anything unnecessary or unfit for the current scope of the project — for example, don't force full TDD or heavy mocking on a trivial script if it isn't warranted.

---

# Testing in Python

> "In the world of Python, testing is not just a phase. It's a commitment to excellence in craftsmanship."

---

## 1. Why do we need testing?
Testing your code is essential for verifying its correctness, ensuring reliability, and maintaining code quality.

The general idea of testing is ensuring that your application works as expected. Due to testing, you will be able to:
- Detect bugs early during the development process and fix them immediately.
- Provide a form of documentation that helps developers understand how the application should work and show its behavior.

---

## 2. Types of Testing
There are several types of testing widely used in the IT industry:

- **Unit Testing** – Testing individual units or components of a program in isolation to verify that each part functions correctly.
- **Integration Testing** – Testing the integration or interfaces between components to ensure they work together as expected.
- **Functional Testing** – Testing the application against its functional requirements to ensure it behaves as expected from an end-user perspective.

The best approach is to cover all these scenarios using testing tools, but this lesson focuses primarily on **unit testing** and the available options in Python.

---

## 3. Introduction to unittest
The most common way to test Python applications is to use the built-in `unittest` library.

### Key Considerations When Testing
As a developer, several questions should come to mind regarding potential issues:
- What if functions are passed non-numeric types, like a string and a number?
- What happens when attempting to divide by zero?
- Will the application crash, or will it handle these situations gracefully?

Instead of making assumptions, we write tests to guarantee that our application behaves as intended under various circumstances.

### Writing Your First Unit Test
Unit tests are designed to test individual components, or "units," of your application in isolation. This means testing the smallest part of an application, like a function or method, to ensure it does exactly what it's supposed to do.

### Testing OOP Applications
Testing object-oriented applications isn't really different from testing functions. You can test classes, their methods, and their behavior. Common elements include setting up a clean environment before each test and optionally cleaning up afterward.

### Structuring Your Tests
As with everything in programming, tests MUST have a correct structure. Each test case should include:
- **Setup** – Prepare the necessary environment or state before the actual tests run.
- **Test Cases** – Individual test functions that check specific behaviors.
- **Assertions** – Statements that check if the output matches the expected result.
- **Teardown (Optional)** – Clean-up steps after test cases run.

Generally, tests should not be mixed with production code. A great approach is to keep tests in a separate directory.

### Running Tests
You can run tests by executing the test file directly, or you can run all tests across different test files using a test discovery command.

---

## 4. Introduction to pytest
There isn't much difference between `pytest` and `unittest` in terms of serving their purposes. Both are configurable, both test your application, and they work similarly. However, `pytest` simplifies writing small tests yet scales to support complex functional testing. This is why `pytest` is often favored in production code.

### Installing pytest
To begin using `pytest`, you need to install it via pip.

### Writing Tests with pytest
Once installed, writing a test is as straightforward as defining a function prefixed with `test_` and using plain `assert` statements.

### Running Tests with pytest
There are several useful commands for running tests with `pytest`:
- Run all tests in a specific file.
- Run all tests in a directory.
- Get verbose output with detailed results.
- Run only specific test functions.
- Run tests that match a given expression.
- Ignore certain directories or files.
- Stop after a certain number of failures.
- Modify traceback output format for easier debugging.
- Stop on the first failure.
- Rerun only failed tests from the last run.

These commands can save a significant amount of time during development and help with debugging.

---

## 5. Test-Driven Development (TDD)
Test-Driven Development (TDD) is a modern software development practice where tests are written **before** the code that will make the tests pass. It follows a simple iterative cycle known as **"Red-Green-Refactor"**:

- **Red** – Write a test that defines a function or improvement, which should fail because the function isn't implemented yet.
- **Green** – Implement the function in the simplest way possible to make the test pass.
- **Refactor** – Clean up the code while ensuring that tests still pass.

TDD encourages developers to think through their design before writing the code.

### Benefits of TDD
- **Documentation** – The tests serve as live documentation for the application.
- **Design** – Helps in building a better design as it requires writing testable code.
- **Confidence** – Each change is made with confidence that existing features are not broken.

**Disadvantage:** Sometimes it can be difficult to follow this approach—it may be time-consuming, especially for large projects.

---

## 6. Mocking and Patching

### Mocking
Mocking involves simulating the behavior of real objects within your system. Mock objects can be programmed with predefined responses, making them highly flexible for testing a wide range of scenarios.

**Benefits of mocking:**
- Test components in isolation from the rest of the system.
- Simulate various states of external systems or resources that are difficult or time-consuming to replicate.
- Avoid side effects that can interfere with test outcomes.
- Control the test environment by specifying expected inputs and outputs.

### Patching
Patching (often used with mocking) involves temporarily replacing the actual implementation of a class, method, or function with a mock during test execution.

**Common use cases for patching:**
- Functions and methods – to control their outputs or side effects.
- System-level operations, like file I/O – to prevent tests from altering the system's state.
- Libraries and frameworks – to test your code's interaction without invoking the actual implementation.

### Practice with Mocking and Patching
`pytest` can integrate with the mocking library from the Python standard library, enabling the use of mocks and patches in your tests. This integration allows you to:
- Simulate complex behaviors.
- Assert interactions with mock objects.

A common workflow involves using a decorator to replace functions with mocks, then asserting that the mock was called with the expected arguments—simulating actions instead of performing the actual operation.

> **Note for a Telegram bot project:** mocking is especially useful for simulating Telegram API calls (e.g., sending messages) without actually hitting the network during tests.

---

## 7. Advanced Techniques

### Parameterized Testing
Parameterized testing allows you to run the same test function with different inputs, reducing code duplication and making it easier to cover a wide range of scenarios.

`pytest` offers a simple way to parameterize tests using a built-in decorator. This allows running the same test logic multiple times with different input values, instead of writing duplicate code.

### Fixture Management
Fixtures are functions that run before (and sometimes after) the actual test functions to which they're applied. Fixtures are a powerful feature for setting up and tearing down test environments or contexts.

**Key benefits of fixtures:**
- Reusable test data setup.
- Automatic injection into test functions.
- Clean separation of test preparation from test logic.

### Error Handling in Tests
Testing how your application handles errors is as crucial as testing its success paths. It simplifies the process of asserting exceptions.

**Common approach:**
- Check that a specific exception is raised under certain conditions.
- Assert that the exception message matches the expected value.

All these tools can be easily integrated to enhance the quality of your tests. With this knowledge, you'll be able to write well-structured, easy-to-use tests.

---

## 8. Coverage Analysis
Code coverage is a measure used to describe the degree to which the source code of a program is executed when a particular test suite runs. A program with high code coverage has had more of its source code tested, which can lead to fewer bugs.

### Coverage Tool
There is a tool for measuring code coverage of Python programs. It monitors your program, noting which parts of the code have been executed.

### Using Coverage with pytest
You can run your tests under coverage, then generate reports that show which lines of code were not executed by your tests. This helps identify areas needing additional testing.
