---
name: CODING
description: A thinking and writing process of fixing or generating code.
---

# CODING
Firstly, Understand backgournd, purpose, style, tone, audience and preferences.
Then, confirm whether the task is to fix or generate code.

# Generate Code
1. Understand the Problem First
Before touching a keyboard, ask:
- What is the input? What is the expected output?
- What are the constraints (performance, memory, scale)?
- What edge cases exist (empty input, nulls, very large numbers)?
- Can you explain the problem in plain English?
2. Break It Down (Decompose)
Large problems are just small problems stacked together. Decompose into:
- Sub-problems — smaller, independently solvable units
- Steps — ordered sequence of operations
- Responsibilities — what each function/module/class should own
3. Think in Abstractions (Before Syntax)
Resist the urge to jump to code. Instead, think in pseudocode or plain English:
## EXAMPLE
- "First, loop through the list..."
- "For each item, check if it meets condition X..."
- "If it does, add it to the result..."
This separates logic from syntax, reducing bugs caused by confusing the two.
4. Choose the Right Data Structures & Algorithms
Data structure choice often determines everything else:
- Do you need fast lookup? → Hash map
- Ordered data? → Array or sorted set
- Hierarchical relationships? → Tree
- First-in-first-out? → Queue
Think about time and space complexity before committing to an approach.
5. Write Incrementally — Not All at Once
Good code is written in layers:
- Make it work (correct output, passing tests)
- Make it clear (readable, named well, structured logically)
-  Make it efficient (optimize only where necessary)
Avoid premature optimization — get correctness first.
6. Name Things Carefully
Naming is thinking made visible:
- Variables should describe what they hold (userAge, not x)
- Functions should describe what they do (calculateTotal, not doStuff)
- Booleans should read like conditions (isValid, hasPermission)
7. Write for the Reader, Not the Machine
Code is read far more than it's written. Ask yourself:
- Would a teammate understand this in 6 months?
- Is the intent clear without needing a comment?
- Are comments explaining why, not just what?
8. Test as You Think
Tests aren't an afterthought — they clarify your thinking:
- Write a test before the function (TDD) to nail down expected behavior
- Test edge cases, not just the happy path
- If something is hard to test, it's usually a design problem
9. Review & Refactor
After a first working version:
- Read your code like a stranger would
- Look for duplication, unclear logic, and unnecessary complexity
- Refactor mercilessly — simplicity is the goal

# Fix Code
1. What errors does the user encounter when executing the code? Or what functions does the user want to optimize?
2. Fix the code according to the error messages or optimization requirements and generate the new code for this file.

# Output
The output should be a dict with multiple items, the keys should be the file names and the values should be the code content.

# Preferences
1. Notes need to be concise.
2. Do not mark the language before the output dict.

## Example
{
    "file_name1.py": "code1",
    "file_name2.cpp": "code2",
}

# Final check
Check whether the output meets the sytle, tone, audience and preferences.

# Final Answer:
A dict with file names and code contents."
