## 🤖 AI Model Instructions (Vibe Coding)
This file is part of a technical reference for a **Python Telegram bot project**. Apply only the concepts from this file that you actually need for the current task. Multiprocessing is mainly relevant here for genuinely CPU-bound work (e.g. processing a very large batch of collected links or doing heavy text/data crunching), not for typical Telegram API calls or web scraping, which are I/O-bound and better handled with `asyncio` or threading. Do not apply anything unnecessary or unfit for the current scope of the project — don't reach for multiprocessing when a simple loop or `asyncio` task would do.

---

# Multiprocessing

> "Turbo booster of Python, and nothing to say else"

---

## 1. Multiprocessing vs Multithreading
Multiprocessing in Python is a powerful paradigm that allows developers to achieve true parallelism in their applications, particularly in CPU-bound tasks. Here's a detailed comparison of both mechanisms:

**Multiprocessing:**
- Uses parallel execution of processes.
- Each process has separate memory space.
- Best suited for CPU-bound tasks requiring full CPU utilization.
- Bypasses the Global Interpreter Lock (GIL), allowing full use of multiple CPU cores.
- Has higher resource usage due to separate memory space and process management overhead.
- Processes do not share memory, reducing data corruption risks.

**Multithreading:**
- Uses concurrent execution of threads within a single process.
- Threads share memory space.
- Best suited for I/O-bound tasks or when tasks need to share memory and resources.
- Limited by the GIL, not suitable for CPU-bound tasks.
- Has lower resource usage as threads are lighter than processes.
- Shared memory can lead to data corruption if not properly managed.

### 1.1 Use Cases
Multiprocessing shines in scenarios where tasks are CPU-bound and can be performed independently, such as data processing and computing-intensive operations. It can also be useful for certain web-related tasks.

---

## 2. multiprocessing

### 2.1 Creating Processes
To create a new process, you instantiate a `Process` object and call its `start()` method. Each process requires a target function to execute and can also accept arguments for the target function. The `join()` method is used to wait for the process to finish.

### 2.2 Process Management
The `Process` class represents an activity that is run in a separate process. The class has methods like `start()`, `join()`, and `terminate()` to manage the process lifecycle. You can also check if the process is still running using `is_alive()`. This allows you to monitor and control processes throughout their execution.

---

## 3. Inter-process Communication (IPC)
In multiprocessing, since each process operates in its own memory space, direct data sharing like in multithreading (with shared memory) is not possible. Python's `multiprocessing` module provides several ways to enable IPC, with Pipes and Queues being the most common.

### 3.1 Pipes
A Pipe can be used for two-way communication between processes. Data in a pipe is buffered, meaning it's held in a temporary storage area until the recipient retrieves it. Pipes are best for simple, unidirectional communication between two processes.

### 3.2 Queues
Queues are thread and process-safe, making them ideal for IPC. They can be used to exchange data between processes. Queues are more flexible and suitable for complex data exchange between multiple producers and consumers.

### 3.3 Real-world Application
A common real-world scenario is a data processing application that performs several tasks: fetching data from a database, processing this data (filtering, aggregation), and finally saving the results to a new location. This is common in data analytics and ETL (Extract, Transform, Load) operations.

**Application Requirements:**
- **Data Fetcher Process:** Connects to a database or data source, fetches data, and sends it through a Pipe to the next stage.
- **Data Processor Process:** Receives raw data through a Pipe, performs processing (filtering, aggregating), and places processed data into a Queue.
- **Data Saver Process:** Takes processed data from the Queue and saves it to a database, file system, or another storage system.

This pipeline efficiently processes large datasets by dividing the work across multiple processes. Processing in parallel is much faster than the synchronous approach.

---

## 4. Synchronisation
Same as multithreading, the `multiprocessing` module provides several synchronization primitives that help prevent data corruption and ensure data consistency across concurrent processes.

### 4.1 Lock
A Lock is a synchronization primitive that can be locked or unlocked. It is used to prevent simultaneous access to a shared resource by multiple processes, ensuring that only one process can access the resource at a time. This is useful for synchronizing access to files or other shared resources.

### 4.2 Semaphore
A Semaphore is a more general version of a Lock. While a Lock allows only one process to access a certain section of code at a time, a Semaphore allows a fixed number of processes to do so. This is useful when you want to limit concurrent access to a resource (like a database connection pool).

### 4.3 Event
An Event is a synchronization primitive that can be used to notify one or more processes that something has happened. Processes can wait for an event to be set before proceeding. This is useful for signaling between processes.

### 4.4 Condition
A Condition is a synchronization primitive that allows one process to wait for a condition to be met, while allowing other processes to notify it that the condition has been met. This is commonly used in producer-consumer patterns where consumers wait for items to be produced.

These synchronization primitives help avoid race conditions and ensure data consistency across concurrent processes. Always be extremely careful with shared resources!

---

## 5. Process Pooling

### 5.1 Pool
The `Pool` class allows you to create a pool of worker processes that can execute tasks in parallel. It manages the available processes and assigns tasks to them as they become available. This is more efficient than creating and managing individual processes manually.

### 5.2 Applying Pool
The `Pool` class provides several methods to parallelize tasks. The `map` and `apply` methods are particularly useful for distributing tasks among the pool's worker processes.

### 5.3 map
The `map` function applies a given function to each item of an iterable (like a list) and collects the results. It blocks until the result is ready, making it suitable for parallel processing of collections.

### 5.4 apply
The `apply` function applies a given function with arguments to a worker process. Unlike `map`, `apply` is used for a single invocation and blocks until the result is ready.

### 5.5 Worker Processes
The `Pool` class also provides ways to manage the worker processes, allowing for asynchronous task execution and callback handling. The `apply_async` method enables non-blocking task submission to the pool, allowing the main program to continue executing while the task is processed in the background.

---

## 6. Production Approaches
In real-world cases, programmers generally prefer to use `Manager` and `ProcessPoolExecutor` classes to let Python handle synchronization and reduce potential bugs.

### 6.1 Manager
The `Manager` class in the `multiprocessing` module allows creating shared objects that can be accessed and modified by different processes. This is especially useful for creating complex data structures (like lists, dictionaries) shared across processes. Managers handle the synchronization automatically.

### 6.2 ProcessPoolExecutor
The `concurrent.futures` module provides a high-level interface for asynchronously executing callables with `ProcessPoolExecutor`. It simplifies the management of process pools, offering an alternative to the `Pool` class for executing tasks in parallel. It provides a more modern, Pythonic interface for process pooling.
