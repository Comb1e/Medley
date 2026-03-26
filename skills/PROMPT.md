---
name: PROMPT
description: Considerations for optimizing prompt.
---

# Core
Only need to provide detailed descriptions and standardize the user's prompt.

# Parameters to generate
1. File name is the name of the json file, including suffix.
2. Type is the classification of the prompt. It should be one of the 'coding, text, mixture'.
3. Background: The prompt related context information or prerequisites.
4. Purpose: The specific tasks or objectives to be completed.
5. Style: The language style, style or structural format of the output.
6. Tone: The emotional color or attitude tendency expressed.
7. Audience: The reading group after prompt is completed. For example, if the prompt need to generate code, the audience is programmers.
8. Folder name: The name of the folder where the files are stored(not the json file). Use the project name provided by the user. If the user does not provide it, come up with one. For example, if the user want to write a book report on Journey to the West but do not specify the project name, this paramter should be "book_report". Avoid using space there.
9. Path: The place where files are generated. Follow the second point in #Main Distriction#

# Prompt Preferences
1. Before using generate_prompt_params, use get_files_in_folder to get the file names in the default prompt folder. Avoid creating files with the same name.
2. Each parameter should be as detailed as possible to avoid vague descriptions.

# Examples
## Input:
raw_prompt: How to respond appropriately to the difficulties of users as customer service. Generate in "C:/Users/Public/Desktop/customer_service_answer".

## Output:
file_name: "customer_service_prompt.json"
type: "text"
background: "As a customer service, you need to properly solve the difficulties encountered by users."
purpose: "Improve customer experience and satisfaction with reasonable language."
style: "Practical orientation: emphasizing operable and specific behavior suggestions."
tone: "empathy, positive."
audience: "Customers."
folder_name: "customer_service_answer"
path: "C:/Users/Public/Desktop"