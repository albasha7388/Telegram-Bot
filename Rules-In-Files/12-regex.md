## 🤖 AI Model Instructions (Vibe Coding)
This file is part of a technical reference for a **Python Telegram bot project**. Apply only the regex concepts you actually need for the current task (e.g., validating user input, parsing command arguments, extracting data from messages). Do not apply anything unnecessary or unfit for the current scope of the project — don't build an overly complex regex when a simple string check or `str.split()` would do the job.

---

# Regular Expressions

> "The power of pattern matching with precision."

---

## 1. Regular Expressions
Regular expressions (regex or regexp) are a powerful tool for processing text. They allow you to specify a pattern of text to search for in a string.

### 1.1 Use Cases
Generally, we need regular expressions for string data in the following use cases:

- **Validation** – Ensuring that strings match a specific format to ensure data integrity and consistency. Examples include validating formats like email addresses, phone numbers, and URLs.

- **Search and Replace** – Finding and replacing substrings within a larger text body. This is useful in code editing, data cleaning, and log processing.

- **Data Extraction** – Extracting information from structured text for analysis or format migration. Examples include parsing data from log files, spreadsheets, or HTML documents.

- **Text Parsing** – Splitting text into tokens or segments based on patterns. This aids in analyzing complex strings or constructing parsers.

- **Complex Pattern Matching** – Identifying patterns within text that are not easily described by standard string methods. Examples include identifying specific word sequences or characters with variable amounts of whitespace.

### 1.2 Example Overview
Regular expressions can be complex. For instance, validating an email address using regex involves a pattern that checks for the correct format: username@domain.com. The pattern ensures that the username contains only allowed characters and that the domain has the proper structure. Don't worry if this seems intimidating—you will learn how to work with regex step by step.

---

## 2. Basic Patterns
Regular expressions use a combination of literal characters and special characters to define patterns for matching strings. In Python, you need to import and use the `re` module to work with regular expressions.

### 2.1 Literal Characters
Literal characters are the simplest form of pattern matching. They match exactly the characters specified in the regex pattern. For example, the pattern `cat` will match the string "cat" in any larger string.

### 2.2 Special Characters and Sequences
Special characters and sequences represent specific instructions in regex. Here are some common ones:

- **Dot (.)** – Matches any single character except newline.
- **Caret (^)** – Matches the start of a string.
- **Dollar ($)** – Matches the end of a string.
- **Asterisk (*)** – Matches 0 or more occurrences of the preceding element.
- **Plus (+)** – Matches 1 or more occurrences of the preceding element.
- **Question Mark (?)** – Makes the preceding element optional, matching 0 or 1 occurrence.
- **Curly Brackets ({n})** – Matches exactly n occurrences of the preceding element.

These special characters allow you to create flexible and powerful search patterns. For example, you can combine them to find strings that start with a specific character, contain any characters in between, and end with another specific character.

---

## 3. Character Classes
Character classes allow you to match specific sets of characters within a string. There are two types: predefined and custom.

### 3.1 Predefined Character Classes
These are built-in options for working with regular expressions:

- **\d** – Matches any digit.
- **\D** – Matches any non-digit character.
- **\s** – Matches any whitespace character (including spaces, tabs, and line breaks).
- **\S** – Matches any non-whitespace character.
- **\w** – Matches any word character (letters, digits, and underscores).
- **\W** – Matches any non-word character.

### 3.2 Custom Character Classes
You can also define your own character classes using square brackets:

- **[abc]** – Matches any one of the characters a, b, or c.
- **[^abc]** – Matches any character that is not a, b, or c.
- **[a-z]** – Matches any lowercase letter.
- **[A-Z]** – Matches any uppercase letter.
- **[0-9]** – Matches any digit (same as \d).

Character classes are useful for matching specific subsets of characters, such as vowels, letters only, or digits.

---

## 4. Quantifiers
Quantifiers define how many instances of a character, group, or character class must be present for a match to occur.

### Common Quantifiers
- **\*** – Matches 0 or more occurrences of the preceding element.
- **+** – Matches 1 or more occurrences of the preceding element.
- **?** – Matches 0 or 1 occurrence of the preceding element, making it optional.
- **{n}** – Matches exactly n occurrences of the preceding element.
- **{n,}** – Matches n or more occurrences of the preceding element.
- **{n,m}** – Matches between n and m occurrences of the preceding element, inclusive.

### Greedy vs Lazy Quantification
Quantifiers are greedy by default, meaning they match as many occurrences of the pattern as possible. To make them lazy, you append a `?` to them, causing them to match as few characters as needed for the pattern to succeed. This distinction is important when you want to capture the smallest possible match rather than the largest.

---

## 5. Anchors and Boundaries
Anchors and boundaries do not match characters but rather match positions within the input text. They are used to assert that the required match is at a particular position.

### 5.1 Word Boundaries
The word boundary anchor `\b` is used to denote the boundaries of words. It allows a regular expression to specify that a given pattern must occur at the beginning or end of a word within the text. For example, `\bWORD\b` matches the exact word "WORD" as a whole word, ensuring it doesn't match substrings of larger words.

### 5.2 Start and End Anchors
- The start anchor `^` matches the beginning of the entire text.
- The end anchor `$` matches the end of the entire text.

These anchors are useful for ensuring that a pattern appears at the very start or very end of a string.

---

## 6. Grouping and Capturing
Grouping and capturing allow you to treat multiple characters as a single unit, extract information from matches, and perform operations on captured groups.

### 6.1 Parentheses for Grouping
Parentheses `()` are used to group parts of the pattern. This is useful for applying quantifiers to a sequence of characters or for isolating parts of a pattern for capturing or backreferencing.

### 6.2 Capturing Groups
By default, groups created with parentheses capture the matched text for later use, such as extracting data. You can access captured groups using methods that return the matched content.

### 6.3 Non-Capturing Groups
If you want to use parentheses to group parts of your pattern without capturing the matched text, you can use non-capturing group syntax: `(?:pattern)`. This allows for grouping without affecting the numbering of other capturing groups.

### 6.4 Common Flags
Regular expressions in Python support several flags that modify how the pattern is applied:

- **Case Insensitivity (re.IGNORECASE or re.I)** – Makes the match case-insensitive, allowing patterns to match letters regardless of case.

- **Multiline (re.MULTILINE or re.M)** – Treats the start (^) and end ($) characters as working across multiple lines, allowing them to match at the start or end of any line within a string.

- **Dot Matches All (re.DOTALL or re.S)** – Makes the dot (.) special character match all characters, including the newline character, which it does not match by default.

---

## 7. Practice
In practice, you will use regular expressions to solve various text-processing tasks. For example, you might work with a large text file containing different sections and use regex to:

- Identify and separate different sections of the text based on headers.
- Find all instances of specific words regardless of case.
- List all names or items listed under specific sections.
- Extract paragraphs or blocks of text, including newlines.
- Capture and categorize specific terms or phrases.
- Identify and extract contact information like email addresses and phone numbers.
- Highlight exact occurrences of specific words.

These tasks demonstrate the versatility of regular expressions in real-world applications, such as validating or parsing commands and arguments sent by users in a Telegram bot.
