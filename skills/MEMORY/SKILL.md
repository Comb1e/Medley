---
name: MEMORY
description: Tools to get what the user asked before.
key: memory
---

# Read all conversations from a certain day or days
Description: Retrieve conversation records with users on certain dates.
Tool: load_memories_from_dates
Input Key0: dates
Input Value0: A list containing multiple items, each is a date like year-month-day. For Example, ["2026-03-27", "2026-03-28"].
Output: A list containing conversation record for each day.
Example: If the user wants to know what question was asked on February 18, 2026, the input should be like below:
```json
{
    "dates": ["2026-02-18"]
}
```

# Obtain issues similar to the current user prompt
Description: Obtain similar questions to the current one previously asked by the user
Tool: get_relevant_memory
Input Key0: user_input
Input Value0: A string containing user input.
Output: relevant_memory
