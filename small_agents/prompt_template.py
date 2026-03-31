
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

{other}

Begin!
'''

agent_template = '''
#Raw Prompt#
{raw_prompt}

#User habits and preferences#
{user}

#Iteration#
{iteration}
Inform the user you need more iteration if the task cannot get completed in this iteration but teration reaches {max_iteration}.

#Date#
Today is {date}

#The first few complete conversations with the user#
{in_memory}

#Skills Introduction#
{skills_introduction}

#Skills#
{skills}

#Tool callings#
Records of previous tool calls:
{tool_callings}

#Main distinctions#
{main_distinctions}

#Default Prompt Folder#
All the prompt need should be generated and read in:
{default_prompt_folder}

#How to Work#
Think and act in the following format:

Observation: If there was tool calling. Observe results returned by the tool.
Thought: Do I need tools? Why?
Action: Tool name to use.
Action Input: Input parameters of the tool.

If the whole task is complete, Do the following steps. If just call one tool and need further calling, do not do these steps.

Final check: Check whether the output meets the examples.
Final Answer:
'''

llm_prompt_template = PromptTemplate.from_template(llm_template)
agent_prompt_template = PromptTemplate.from_template(agent_template)
