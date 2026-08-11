## 🤖 AI Model Instructions (Vibe Coding)
This file is part of a technical reference for a **Python Telegram bot project**. Apply only the concepts or advice from this file that you actually need while building the specific part of the project you're currently working on (e.g., designing classes responsible for commands, handlers, or database access). Do not apply anything unnecessary or unfit for the current size or context of the project, and avoid over-splitting code when there's no real need for it.

---

# Single Responsibility Principle (SRP)

## 📌 Definition
> **"A class should have only one reason to change."**

The principle means that every class or code module should be responsible for one specific part of the system's functionality, and should have a single, clear purpose. Any change in the requirements of that purpose is the only reason to modify the class.

---

## 🎯 Importance
- Reduces code complexity by separating responsibilities.
- Makes the code easier to understand and maintain.
- Increases reusability.
- Makes testing easier and more accurate.
- Reduces the impact of changes on other parts of the system.
- Helps in applying other principles like OCP and DIP.

---

## ✅ Advantages
- **Code clarity:** Each class has a specific purpose, making the code easy to read and understand.
- **Easier maintenance:** Modifying a specific function happens in one place only.
- **Testability:** Each responsibility can be tested separately.
- **Reusability:** Classes can be used in different contexts.
- **Reduced complexity:** Breaking down a big problem into smaller ones.
- **Easier collaboration:** Multiple developers can work on different responsibilities at the same time.

---

## ❌ Drawbacks and Challenges
- **Increased number of classes:** May lead to an inflated number of classes in the project.
- **Difficulty identifying responsibilities:** It can be hard to define the boundaries between responsibilities.
- **Over-splitting:** May lead to unjustified complexity in small projects.
- **Code duplication:** Excessive splitting may lead to duplication of some logic.
- **Increased development time:** Needs more time for design and planning.

---

## 🛠️ When to use this principle?
- In large and complex projects.
- When there are classes that perform more than one task.
- When you expect frequent changes in a specific part of the system.
- In applications that need long-term maintenance.
- When developing libraries or frameworks used by others.
- When you want to make unit testing easier.

---

## ❌ When NOT to use this principle?
- In very small projects (simple scripts).
- In the Prototype or MVP (Minimum Viable Product) stage.
- When splitting is costly and doesn't add real value.
- In parts that will never change.
- When the performance trade-off from too many classes is unacceptable.

---

## 🤔 Key questions for applying the principle
- **What is the core responsibility of this class?**
- **Is there more than one reason to change this class?**
- **Can I reuse this class in another context?**
- **Can I easily test this class?**
- **Does this class do one thing well?**
- **Will another part of the system be affected if I change this class?**
- **Can I separate these responsibilities into independent classes?**

---

## 📊 Signs of a violation
- **God Class:** A large class containing a lot of functions and properties.
- **Frequent changes:** The class changes frequently for different reasons.
- **Naming difficulty:** Inability to give the class a meaningful name.
- **Duplicated code:** The same logic exists in more than one place.
- **Complex tests:** Difficulty writing tests for the class.
- **Many dependencies:** The class depends on many other classes.

---

## 🔗 Relationship with other principles
- **OCP:** SRP helps achieve OCP because single-responsibility classes are easier to extend.
- **ISP:** SRP and ISP both call for splitting, but ISP focuses on interfaces while SRP focuses on classes.
- **DIP:** SRP makes DIP easier to apply because small classes are easier to inject dependencies into.

---

## 📝 Practical tips
1. **Start simple:** Don't over-split from the beginning; start with clear classes.
2. **Review the design continuously:** As the project evolves, new responsibilities may appear.
3. **Use expressive names:** The class name should reflect its responsibility.
4. **Think about refactoring:** When you notice a violation of the principle, refactor the code.
5. **Use composition:** Instead of inheriting multiple responsibilities.

---

## 🧠 Summary
The SRP principle is the cornerstone of clean software design. It helps keep code understandable, maintainable, and flexible to change. Despite the challenges of precisely identifying responsibilities, the long-term benefits outweigh the costs, especially in large and complex projects.
