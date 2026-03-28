---
name: TEXT_RELATED
description: Specification for generating text.
---

# Core
1. Line breaks can only use "\n". #Do not use Newline Characters!!!#
2. Double quotes inside values must be escaped.

# Output
1. The output should be a dict with multiple items, the keys should be the file names and the values should be the code content.

## Example1
{
    "file_name1.py": "code1",
    "file_name2.cpp": "code2",
}
## Example2
{
    "file_name1.md": "text1"
}