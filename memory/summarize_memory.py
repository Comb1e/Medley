import os
import json
import anthropic
from datetime import datetime, timedelta
from config import config

client = anthropic.Anthropic()


class SummarizingAgent:
    def __init__(self, window=6, summarize_after=20):
        self.recent = []
        self.summary = ""
        self.window = window
        self.summarize_after = summarize_after
        self.logs_dir = config.MEMORY_LOGS_PATH
        self.user_profile_path = os.path.join(self.logs_dir, "user.md")
        self._ensure_today_folder()

    # ── Path helpers ───────────────────────────────────────────────────────────

    def _day_dir(self, date) -> str:
        return os.path.join(self.logs_dir, date.strftime("%Y-%m-%d"))

    def _raw_path(self, date) -> str:
        return os.path.join(self._day_dir(date), "raw_memories.jsonl")

    def _summary_path(self, date) -> str:
        return os.path.join(self._day_dir(date), "daily_summary.md")

    # ── Startup: today-folder detection & backfill pipeline ───────────────────

    def _ensure_today_folder(self):
        """
        Check whether today's folder exists.
        If not — run the full backfill + user-profile pipeline, then create it.
        """
        today = datetime.now()
        today_dir = self._day_dir(today)

        if os.path.exists(today_dir):
            print(f"[SummarizingAgent] Today's folder exists: {today_dir}")
            self._load_latest_summary()
            return

        print(f"[SummarizingAgent] Today's folder not found. "
              f"Running backfill pipeline ...")

        # 1. Summarize each past day in the last month that has raw data
        newly_created = self._backfill_past_month(today)

        # 2. Re-summarize all daily summaries → user.md
        if newly_created:
            self._rebuild_user_profile()

        # 3. Create today's folder now that the pipeline is done
        os.makedirs(today_dir, exist_ok=True)
        print(f"[SummarizingAgent] Today's folder created: {today_dir}")

        self._load_latest_summary()

    def _backfill_past_month(self, today: datetime) -> list[str]:
        """
        Walk the past 30 days. For each day that has raw_memories.jsonl
        but no daily_summary.md, generate and save the summary.
        Returns list of newly created summary file paths.
        """
        newly_created = []

        for offset in range(1, 31):          # yesterday → 30 days ago
            date = today - timedelta(days=offset)
            raw_path = self._raw_path(date)
            summary_path = self._summary_path(date)

            if not os.path.exists(raw_path):
                continue                     # no data for this day

            if os.path.exists(summary_path):
                print(f"[Backfill] Skipping {date.date()} — summary exists.")
                continue

            print(f"[Backfill] Summarising {date.date()} ...")
            summary_text = self._summarize_day(date)
            if not summary_text:
                continue

            os.makedirs(self._day_dir(date), exist_ok=True)
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"# Daily Summary — {date.strftime('%Y-%m-%d')}\n\n")
                f.write(summary_text)

            newly_created.append(summary_path)
            print(f"[Backfill] Saved: {summary_path}")

        return newly_created

    def _rebuild_user_profile(self):
        """
        Collect every daily_summary.md from the past 30 days,
        feed them all to the LLM, and overwrite logs/user.md with
        distilled user preferences and absolute facts.
        """
        today = datetime.now()
        summaries = []

        for offset in range(1, 31):
            date = today - timedelta(days=offset)
            summary_path = self._summary_path(date)
            if not os.path.exists(summary_path):
                continue
            with open(summary_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                summaries.append(
                    f"### {date.strftime('%Y-%m-%d')}\n{content}"
                )

        if not summaries:
            print("[SummarizingAgent] No daily summaries found — skipping user.md rebuild.")
            return

        # Also fold in the existing user.md if present, so nothing is lost
        existing_profile = ""
        if os.path.exists(self.user_profile_path):
            with open(self.user_profile_path, "r", encoding="utf-8") as f:
                existing_profile = f.read().strip()

        combined = "\n\n---\n\n".join(summaries)
        prompt = (
            "You are building a persistent user profile.\n\n"
            "Below are daily conversation summaries from the past month"
            + (", plus the existing user profile:\n\n"
               f"## Existing Profile\n{existing_profile}\n\n"
               if existing_profile else ":\n\n")
            + f"## Daily Summaries\n{combined}\n\n"
            "Based on all of the above, produce a concise Markdown document that captures:\n"
            "1. **User Preferences** — communication style, topics of interest, "
            "recurring requests, tools or languages favoured.\n"
            "2. **Absolute Facts** — confirmed personal details, constraints, "
            "or decisions the user has stated explicitly.\n\n"
            "Be factual, concise, and deduplicate. "
            "Do not invent anything not evidenced in the summaries."
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        profile_text = response.content[0].text

        os.makedirs(self.logs_dir, exist_ok=True)
        with open(self.user_profile_path, "w", encoding="utf-8") as f:
            f.write(f"# User Profile\n")
            f.write(f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
            f.write(profile_text)

        print(f"[SummarizingAgent] user.md rebuilt: {self.user_profile_path}")

    # ── Raw log helpers ────────────────────────────────────────────────────────

    def _log_message(self, role: str, content: str):
        """Append one turn to today's raw_memories.jsonl."""
        today = datetime.now()
        day_dir = self._day_dir(today)
        os.makedirs(day_dir, exist_ok=True)
        record = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content
        }
        with open(self._raw_path(today), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_raw_records(self, date) -> list[dict]:
        """Read and validate all records from raw_memories.jsonl for a date."""
        path = self._raw_path(date)
        if not os.path.exists(path):
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if (isinstance(entry, dict)
                            and entry.get("role") in ("user", "assistant")
                            and str(entry.get("content", "")).strip()):
                        records.append(entry)
                except json.JSONDecodeError:
                    continue
        return records

    # ── Summarization helpers ──────────────────────────────────────────────────

    def _summarize_day(self, date) -> str:
        """Summarize one day's raw conversation into a short markdown block."""
        records = self._load_raw_records(date)
        if not records:
            return ""

        conversation = "\n".join(
            f"{r['role'].capitalize()}: {r['content']}"
            for r in records
        )
        prompt = (
            "Summarise the following conversation between a user and an AI assistant. "
            "Focus on: what the user asked about, decisions made, key information "
            "exchanged, and any preferences or facts revealed about the user. "
            "Be concise and use bullet points.\n\n"
            f"{conversation}"
        )
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _summarize_recent(self) -> str:
        """Compress self.recent into a short summary for the rolling context window."""
        conversation = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}"
            for m in self.recent
        )
        prompt = (
            "Briefly summarise this conversation segment to preserve context "
            "for an ongoing dialogue. Be concise.\n\n"
            f"{conversation}"
        )
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _load_latest_summary(self):
        """
        Load the most recent daily_summary.md found in the past 30 days
        as the initial rolling summary for this session.
        """
        today = datetime.now()
        for offset in range(1, 31):
            date = today - timedelta(days=offset)
            summary_path = self._summary_path(date)
            if os.path.exists(summary_path):
                with open(summary_path, "r", encoding="utf-8") as f:
                    self.summary = f.read().strip()
                print(f"[SummarizingAgent] Loaded summary from {date.date()}")
                return

    def _build_messages(self, user_input: str) -> list[dict]:
        """
        Assemble the message list sent to the LLM:
          [user profile] → [rolling summary] → [recent turns] → [user input]
        """
        messages = []

        # Inject persistent user profile if available
        if os.path.exists(self.user_profile_path):
            with open(self.user_profile_path, "r", encoding="utf-8") as f:
                profile = f.read().strip()
            if profile:
                messages.append({
                    "role": "user",
                    "content": f"User profile for context:\n\n{profile}"
                })
                messages.append({
                    "role": "assistant",
                    "content": "Understood. I'll keep this profile in mind."
                })

        # Inject rolling compression summary
        if self.summary:
            messages.append({
                "role": "user",
                "content": f"Summary of earlier conversation:\n\n{self.summary}"
            })
            messages.append({
                "role": "assistant",
                "content": "Understood."
            })

        messages.extend(self.recent)
        messages.append({"role": "user", "content": user_input})
        return messages

    # ── Core chat ──────────────────────────────────────────────────────────────

    def chat(self, user_input: str) -> str:
        # 1. Log incoming user message
        self._log_message("user", user_input)

        # 2. Build context and call LLM
        messages = self._build_messages(user_input)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=messages
        )
        reply = response.content[0].text

        # 3. Log assistant reply
        self._log_message("assistant", reply)

        # 4. Update rolling in-memory window
        self.recent.append({"role": "user", "content": user_input})
        self.recent.append({"role": "assistant", "content": reply})

        # 5. Compress when window exceeds threshold
        if len(self.recent) >= self.summarize_after:
            print("[SummarizingAgent] Compressing rolling window ...")
            self.summary = self._summarize_recent()
            self.recent = self.recent[-self.window:]

        return reply

    # ── Utility ────────────────────────────────────────────────────────────────

    def show_status(self):
        print(f"\n── SummarizingAgent Status ─────────────────")
        print(f"  Recent turns   : {len(self.recent)}")
        print(f"  Rolling summary: {'yes' if self.summary else 'none'}")
        print(f"  User profile   : "
              f"{'exists' if os.path.exists(self.user_profile_path) else 'none'}")
        print(f"  Logs root      : {self.logs_dir}/YYYY-MM-DD/")
        print(f"────────────────────────────────────────────\n")


# ── Example usage ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = SummarizingAgent(window=6, summarize_after=20)

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break
        if user_input.lower() == "/status":
            agent.show_status()
            continue

        reply = agent.chat(user_input)
        print(f"Agent: {reply}\n")