
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
#Raw Prompt#
{raw_prompt}

#Tools#
The following tools are available：
{tools}

#Task#
{task}

#Skills#
{skills}

#Main distinctions#
1. The tool "get_files_in_folder" should be use to check the folder {prompt_folder}
2. The parameter "path" should be the path indicated by the user in #Raw Prompt#. If the user did not indicate one, it should be {default_generate_path}.

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
