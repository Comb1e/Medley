---
name: TEXT_RELATED
description: Specification for generating text.
---

# Core
1. Line breaks can only use "\n"!!!!!! # Do not use Newline Characters!!!!! #
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

# Error Output
1.
output:
{
    "file_name1.py": "code1.0
    code1.1

    code1.2"
}
error reason: use Newline Characters to do line breaks. Only "\n" is available for line breaks.
correct:
{
    "file_name1.py": "code1.0  \ncode1.1  \ncode1.2",
}
2.
output:
{
    "file_name1.py": "code1.0  \ncode1.1  \ncode1.2",
}
{
    "file_name2.py": "code2.0  \ncode2.1  \ncode2.2",
}
error reason: Output two json files. Only one json file is available.
correct:
{
    "file_name1.py": "code1.0  \ncode1.1  \ncode1.2",
    "file_name2.py": "code2.0  \ncode2.1  \ncode2.2",
}