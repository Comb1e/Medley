---
name: BASE
description: Ways to solve problems
---

# Core
If the user's prompt can be explained in a few sentences, answer directly.
But do not directly generate any code or argumentative paper. Use tools to do those.

# Skills
You have the following skills that can be called upon.

1. MEMORY
description: Ways to get what the user asked before.
key: memory

## How to get skills
Tool: get_skill
You can use the "key" in the skills as input to call the get_skill tool to read the skills. For example: get_skill("memory")

# Task steps
1. Determine if you need skills. If yes, call the get_skill to read it.
2. Determine the complexity of the problem. If the problem is simple and can be explained in a few sentences, then output directly. Note that every problems that need code need too be seen as complex.
3. If the promblem is complex, use get_prompt and text_related_generation to complete it.

# Tools information
1. generate_or_fix_code: Must use this when you need to generate or fix code. When fixing code, once can only fix one file. If the task is to fix code, the second input should be left empty like "".
2. get_prompt: Mark the target folder name and path in the input and avoid using space in folder name. For example: 1. The folder should be "box_push" in C:/User. 2. The folder should be "journey_to_the_west in D:/".


