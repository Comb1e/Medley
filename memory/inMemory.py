# context_memory.py
class InMemoryContextStore:
    def __init__(self, max_turns=10):
        self.history = []
        self.max_turns = max_turns

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        # 保留最近 max_turns * 2 条消息（用户+助手为一轮）
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

    def get_context(self):
        return self.history.copy()

# 使用示例
store = InMemoryContextStore(max_turns=5)
store.add_message("user", "你好！")
store.add_message("assistant", "你好呀！有什么我可以帮你的吗？")
store.add_message("user", "今天心情不好。")

print(store.get_context())