# Medley
A small tool for writing code and articles, gradually adding various functions.
# 🚀 Quick Start
## Prequisites

1. Clone
```powershell
git clone https://github.com
cd
```
2. Setup environment
```powershell
pip install -r requirements.txt
```
3. Configure
```powershell
cp .env.example .env.local
```

Fill in varies under Essential
```powershell
#Essential
DASHSCOPE_API_KEY=...
```
4. Fill in your prompt

Write your prompt in user_prompt.md

5. Run
```powershell
python main.py
```

# 📝 Introdustion
You can use this for coding or wrting text. Code and long text will be saved in logs.

# Usage
## Quit
Type "quit" to end the conversation.

## Read
Type "read" to get read the prompt from user_prompt.md

## Use directly
Type your prompt directly and press Enter

# Feature
1. The content of each conversation will be stored in the memory/logs folder by date. Before the first conversation starts each day, the previous conversation content will be summarized as user habits and hobbies to help the agent better understand user needsThe content of each conversation will be stored in the memory/logs folder by date. Before the first conversation starts each day, the previous conversation content will be summarized as user habits and hobbies to help the agent better understand user needs. You can view the information summarized by the agent in memory/logs/USER.md and memory/logs/year-month-day/user.md.
2. Use all-MiniLM-L6-v2 to find similar conversations from the past seven days.