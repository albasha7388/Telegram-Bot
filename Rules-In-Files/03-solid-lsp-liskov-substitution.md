## 🤖 AI Model Instructions (Vibe Coding)
This file is part of a technical reference for a **Python Telegram bot project**. Apply only the concepts or advice from this file that you actually need when using inheritance in the project (e.g., different handler classes inheriting from a base class). Do not apply anything unnecessary or unfit for the current size or context of the project — if there's no actual inheritance in the code, there's no need to apply this principle.

---

# Liskov Substitution Principle (LSP)

## 📌 Definition
> **"Objects of a superclass should be replaceable with objects of a subclass without affecting the correctness of the program."**

The principle means that any derived class must be able to substitute for the base class anywhere in the program, while maintaining the expected behavior and without causing errors or unexpected results.

---

## 🎯 Importance
- Ensures consistent and smooth system behavior.
- Prevents unexpected runtime errors.
- Strengthens confidence in using inheritance.
- Makes code reuse safer.
- Makes the system more predictable and reliable.
- Supports extension and modification without risking breaking current behavior.

---

## ✅ Advantages
- **Predictable behavior:** The behavior of derived classes can be predicted.
- **Fewer errors:** Reduces runtime errors.
- **Easier testing:** You can test the base class and pass derived classes.
- **Safe reuse:** Derived classes can be used in any context.
- **Clean design:** Encourages a sound class hierarchy design.
- **Easy extension:** Adding new classes without worrying about breaking the system.

---

## ❌ Drawbacks and Challenges
- **Application difficulty:** It can be hard to design a correct inheritance hierarchy.
- **Constraints:** May limit design flexibility in some cases.
- **Performance trade-offs:** May require extra design to ensure compatibility.
- **Modification difficulty:** Changing the base class may affect all derivatives.
- **Deep inheritance:** May lead to complexity in inheritance relationships.

---

## 🛠️ When to use this principle?
- When using inheritance in the system.
- In systems that rely on polymorphism.
- In libraries and frameworks that users extend.
- In large projects with a class hierarchy.
- When you need to guarantee consistent behavior for derived classes.
- In systems that require high reliability.

---

## ❌ When NOT to use this principle?
- When inheritance isn't used in the system.
- In very small projects with limited inheritance.
- When an alternative design (like Composition) is more suitable.
- In parts completely independent of inheritance.
- When the cost of the ideal design outweighs the benefit.

---

## 🤔 Key questions for applying the principle
- **Can this derived class be used instead of the base class?**
- **Does the derived class preserve the contracts of the base class?**
- **Does the derived class throw new, unexpected exceptions?**
- **Does the derived class radically change the behavior of methods?**
- **Does the derived class impose stronger preconditions?**
- **Does the derived class weaken the postconditions?**
- **Can I test the derived class as if it were the base type?**

---

## 📊 Signs of a violation
- **Unexpected exceptions:** The derived class throws exceptions the base class doesn't.
- **Behavior change:** A radical change in the behavior of inherited methods.
- **Stronger preconditions:** The derived class requires stricter conditions.
- **Weaker postconditions:** The derived class doesn't guarantee what the base class guarantees.
- **Unsupported properties:** The derived class doesn't support some properties of the base class.
- **Unnatural inheritance:** The IS-A relationship is illogical (e.g., a penguin is a flying bird).

---

## 🔗 Relationship with other principles
- **OCP:** LSP supports OCP because substitutable classes make extension easier.
- **ISP:** Small interfaces reduce the chance of violating LSP.
- **DIP:** Depending on abstractions instead of details makes LSP easier to apply.
- **SRP:** Single-responsibility classes are easier to design to be substitutable.

---

## 📝 Practical tips
1. **Use Composition instead of inheritance:** When the inheritance relationship is unclear.
2. **Split large classes:** Into smaller, more specific classes.
3. **Test derived classes:** As if they were the base type.
4. **Don't throw new exceptions:** In inherited methods unless supported.
5. **Make sure to respect contracts:** The base class's methods are contracts that must be honored.
6. **Use static analysis tools:** Like `mypy` to catch problems early.
7. **Think about Design by Contract:** To clearly define expectations.

---

## 🧠 Summary
The LSP principle is a guarantee of quality and reliability in systems that use inheritance. By ensuring that derived classes can substitute for base classes without problems, we guarantee predictable and safe system behavior. The biggest challenge is designing a correct inheritance hierarchy, but the benefits in stability and reliability are worth the effort.
