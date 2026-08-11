## 🤖 AI Model Instructions (Vibe Coding)
This file is part of a technical reference for a **Python Telegram bot project**. Apply only the concepts or advice from this file that you actually need when designing interfaces or base classes/protocols in the project. Do not apply anything unnecessary or unfit for the current size or context of the project, and avoid splitting code into many small interfaces without a real need.

---

# Interface Segregation Principle (ISP)

## 📌 Definition
> **"No client should be forced to depend on methods it does not use."**

The principle means that large, bloated interfaces should be split into smaller, more specific interfaces, so that each client implements only the functions it actually needs, and isn't forced to implement functions it doesn't use.

---

## 🎯 Importance
- Prevents interface bloat and increased complexity.
- Makes the system more flexible and adaptable.
- Makes the code easier to understand and maintain.
- Reduces errors caused by unsupported functions.
- Enhances Separation of Concerns.
- Makes unit testing easier.

---

## ✅ Advantages
- **Cleaner code:** Small, focused interfaces.
- **High flexibility:** Interfaces can be changed and extended easily.
- **Fewer errors:** Clients implement only what they need.
- **Easier maintenance:** Changing one interface doesn't affect everything.
- **Better reusability:** Small interfaces are easier to reuse.
- **Easier testing:** Each small interface is tested separately.
- **Better compatibility:** With the SRP and OCP principles.

---

## ❌ Drawbacks and Challenges
- **Too many interfaces:** May lead to a large number of small interfaces.
- **Design complexity:** Managing many interfaces can become difficult.
- **Difficulty determining boundaries:** It can be hard to decide where to split an interface.
- **Increased initial effort:** Needs more design time.
- **Over-splitting:** May lead to unnecessary splitting in some cases.
- **Tracking difficulty:** It can be hard to track relationships between multiple interfaces.

---

## 🛠️ When to use this principle?
- When there are large interfaces containing unrelated functions.
- When you have different types of clients, each needing a subset of functions.
- In modular systems.
- In applications with many roles or types.
- When you want to improve testability.
- In projects that require high flexibility for extension.

---

## ❌ When NOT to use this principle?
- When interfaces are already small and don't need splitting.
- In very simple projects.
- When splitting interfaces is costly and doesn't add value.
- In the Prototype or rapid development stage.
- When the relationships between functions are tightly coupled.
- In systems that won't grow much.

---

## 🤔 Key questions for applying the principle
- **Do all clients need all functions of this interface?**
- **Are there clients forced to implement functions they don't use?**
- **Can I split this interface into smaller interfaces?**
- **What are the logical groupings of functions in this interface?**
- **Does changing one interface affect clients who don't use it?**
- **Can I define interfaces based on roles or responsibilities?**
- **Does implementing this interface cause dead code or exceptions?**

---

## 📊 Signs of a violation
- **Bloated interfaces:** Interfaces containing many unrelated functions.
- **Unused functions:** Clients are forced to implement empty functions or throw exceptions.
- **Dead code:** Unused code exists in many classes.
- **Testing difficulty:** Testing a large interface requires testing unused functions.
- **Frequent changes:** Changing one interface affects all clients.
- **Frequent exceptions:** Functions throwing exceptions because they're unsupported.

---

## 🔗 Relationship with other principles
- **SRP:** ISP and SRP both call for splitting, but ISP focuses on interfaces while SRP focuses on classes.
- **OCP:** Small interfaces make extension easier without modifying clients.
- **LSP:** Small interfaces reduce the chance of violating LSP.
- **DIP:** Small interfaces make it easier to inject and separate dependencies.

---

## 📝 Practical tips
1. **Identify the clients first:** Know who will use the interface and what they need.
2. **Split into small interfaces:** Each interface represents a single responsibility or a related group.
3. **Use multiple inheritance:** In languages that support it, to combine multiple interfaces.
4. **Use composition:** As an alternative to multiple inheritance in languages that don't support it.
5. **Review interfaces continuously:** As the project evolves, you may need to split new interfaces.
6. **Don't be afraid of having many interfaces:** A large number of small interfaces is better than one bloated interface.
7. **Name interfaces clearly:** Each interface should clearly reflect its purpose.

---

## 🧠 Summary
The ISP principle is a powerful tool for keeping interfaces clean and flexible. By splitting large interfaces into small, specific ones, we ensure that clients depend only on what they actually need. Although having many interfaces might be confusing at first, the benefits in maintainability and flexibility far outweigh the challenges.
