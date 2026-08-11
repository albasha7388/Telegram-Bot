## 🤖 AI Model Instructions (Vibe Coding)
This file is part of a technical reference for a **Python Telegram bot project**. This is one of the most directly relevant files in this reference set, since frameworks like **Pyrogram** and **aiogram** are built on `asyncio`. Apply the concepts you actually need for the current task (e.g. writing an `async def` handler, using `aiohttp` for an HTTP call, scheduling a background task with `asyncio.create_task`). Do not apply anything unnecessary or unfit for the current scope of the project.

---

# Asyncio

> "The conductor of asynchronous symphonies, and bugs xD"

---

## 1. Introduction
Asynchronous programming is a concurrency model that allows certain operations, especially I/O-bound tasks, to run without blocking the execution of your program. It's about doing other work while waiting for an I/O operation to complete, without the need for multi-threading or multi-processing.

### 1.1 Definition
- **Non-blocking Execution:** Functions that perform lengthy operations (like network or file I/O) return immediately, allowing the program to continue running.

- **Event Loop:** A programming construct that waits for and dispatches events or messages in a program. It facilitates the management of asynchronous tasks.

### Comparison: Synchronous vs Asynchronous

**Synchronous Execution:**
- Tasks run sequentially. Each task must complete before the next begins.
- Can lead to poor resource utilization during I/O operations, as the program waits for the operation to complete.

**Asynchronous Execution:**
- Tasks run independently, allowing the execution of other tasks in the meantime.
- Improves resource utilization by freeing up the program to perform other tasks during I/O operations.

---

## 2. Coroutines
Coroutines allow you to write code that looks sequential but actually executes asynchronously, pausing and resuming at specific points. It is more about cooperation between routines – waiting for and yielding control to other routines.

Initially, Python used generators (Python < 3.5) to yield values and execute asynchronously. They were a stepping stone towards full asynchronous support.

### 2.2 async and await
- **async:** Declares a function as a coroutine. An async function can contain await expressions, and it doesn't run immediately. Instead, it returns an awaitable object (like a coroutine object).

- **await:** Pauses the execution of the enclosing coroutine, waiting for an awaitable object (like another coroutine) to complete. This pause allows other tasks to run while waiting, making it non-blocking.

The use of `async` and `await` makes asynchronous code look and behave more like traditional synchronous code, though it's concurrent execution.

---

## 3. Event Loop
Consider the Event Loop like the conductor of an orchestra. It keeps track of all the tasks that need to run, starts them at the right moment, and manages their execution until they're done.

### 3.1 How it works?
Python's `asyncio` library brings this concept into your programs. It runs an event loop that efficiently manages all your asynchronous tasks.

- **Task Scheduling:** You tell the event loop about all the tasks (coroutines) you want to run by scheduling them.
- **Running Tasks:** The event loop starts running the tasks. If a task needs to wait (say, for a file to download), it pauses that task and moves on to the next one.
- **Waiting and Resuming:** Once the waiting is over (the file is downloaded), the task is resumed right where it left off.
- **Completion:** This process continues until all tasks are done.

You usually don't need to create or manage the event loop yourself—`asyncio` provides a high-level API for running asynchronous tasks.

> **Note for a Telegram bot project:** Pyrogram and aiogram already run their own event loop for you. In most cases you don't create or manage the loop manually — you just write `async def` handlers and `await` the calls you need.

---

## 4. Practice

### 4.1 HTTP Requests
To make asynchronous HTTP requests, you would use the `aiohttp` library. This allows you to fetch web pages concurrently without blocking the event loop.

### 4.2 Async File I/O
For file operations, `asyncio` offers a different set of APIs since disk operations can also block the event loop. The `aiofiles` library provides asynchronous file handling capabilities, allowing you to read and write files without blocking.

### 4.3 Multiple Async I/O Operations
`asyncio.gather` and `asyncio.wait` are two powerful functions for handling multiple asynchronous operations concurrently.

- **asyncio.gather:** Takes multiple coroutines and runs them concurrently, waiting for all of them to complete and returning their results in order.
- **asyncio.wait:** Allows for more flexible waiting on tasks, including waiting for any task to complete or all tasks to complete.

In conclusion, `asyncio` is all about managing asynchronous I/O operations in a simpler and more efficient way—much better than threading and easier to understand.

---

## 5. Scheduling Tasks

### 5.1 asyncio.create_task
The `asyncio.create_task()` function is used to schedule the execution of a coroutine: it wraps the coroutine into a Task and schedules its execution. The coroutine itself runs concurrently with other tasks and operations and does not block the code itself.

### 5.2 Task Scheduling and Execution Order
If a task awaits another operation, the event loop can switch to running another task, effectively using concurrency to process different operations. Tasks are executed in the order they are scheduled, considering their await expressions. This demonstrates that one task can complete before another despite being scheduled after it, thanks to asynchronous operations.

These concepts form the foundation of working with `asyncio`. For a deeper understanding, you can explore:
- Async Streaming Patterns
- Custom Async Context Managers
- Async Iterators

These topics are too wide to be covered in this reference, but you can refer to the official `asyncio` documentation for more details.

---

## 6. Debugging Async Code

**Using pdb:** Python's built-in debugger `pdb` can be used to debug async code. You can set breakpoints and inspect variables just like in synchronous code.

**Using debug=True:** When running an asyncio event loop, you can enable debug mode by passing `debug=True` to `asyncio.run()`. This provides detailed logging information about the event loop's operations, including selector information and connection details, which can help identify issues in your asynchronous code.
