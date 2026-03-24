
from langchain_core.prompts import PromptTemplate

# ====== Prompt Template ======
llm_template = '''
#Background#
{background}

#Purpose#
{purpose}

#Style#
{style}

#Tone#
{tone}

#Audience#
{audience}

#Skills#
{skills}

Begin!
'''

agent_template = '''
#Background#
{background}

#Tools#
The following tools are available：
{tools}

#Purpose#
{purpose}

#Style#
{style}

#Tone#
{tone}

#Audience#
{audience}

#Project Path#
Generate the project in:
{project_path}

#Skills#
{skills}

#Task Steps#
Firstly, Understand backgournd, purpose, style, tone, audience and preferences.
Then, Think and act in the following format:

Thought: Do I need tools? Why?

Action: Tool name to use (must be one of {tool_names}).
Action Input: Input parameters of the tool.
Observation: Results returned by the tool.
... (repeatable five times, output the number of attempts when starting a new attempt)
Final check: Check whether the output meets the output sytle, tone, audience and preferences.
Final Answer: {final_answer}

Thought: {agent_scratchpad}
'''

prompt_get_template = '''
#Raw Prompt#
{raw_prompt}

#Tools#
The following tools are available：
{tools}

#Task#
Help the user classify problems and optimize prompt structure.

#Skills#
{skills}

#Examples#
Input:
raw_prompt: How to respond appropriately to the difficulties of users as customer service. Generate in "C:/Users/Public/Desktop/customer_service_answer".

Output:
file_name: "customer_service_prompt.json"
type: "text"
background: "As a customer service, you need to properly solve the difficulties encountered by users."
purpose: "Improve customer experience and satisfaction with reasonable language."
style: "Practical orientation: emphasizing operable and specific behavior suggestions."
tone: "empathy, positive."
audience: "Customers."
folder_name: "customer_service_answer"
path: "C:/Users/Public/Desktop"

#Task Steps#
Think and act in the following format:

Thought: Do I need tools? Why?
Action: Tool name to use (must be one of {tool_names}).
Action Input: Input parameters of the tool.
Observation: Results returned by the tool.
... (repeatable two times, output the number of attempts when starting a new attempt)
Final check: Check whether the output meets the examples.
Final Answer: {final_answer}

Thought: {agent_scratchpad}
'''

llm_prompt_template = PromptTemplate.from_template(llm_template)
agent_prompt_template = PromptTemplate.from_template(agent_template)
prompt_get_prompt_template = PromptTemplate.from_template(prompt_get_template)