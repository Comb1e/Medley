---
name: RAG
description: Get the latest knowledge related to user prompts. Call get_skill to get the full skill.
key: rag
func: {"rag": ["retrieve"]}
---

# Get relevant knowledge
Description: Retrieve conversation records with users on certain dates.
Tool: retrieve
Input Key0: user_input
Input Value0: A string containin user input.
Output: A string containing relevant knowledge
Example: If users ask specific and time sensitive questions, such as what is the latest version of macOS, call this tool.