"""
memory_summarizer.py

A class that uses an LLM to summarize user behavior and preferences
from raw_memories.jsonl files stored in date-stamped log folders.

Folder structure expected:
  logs/
    USER.md                  ← global user profile (uppercase)
    2026-03-27/
      raw_memories.jsonl
      user.md                ← daily summary (lowercase)
    2026-03-26/
      raw_memories.jsonl
      user.md
    ...
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from langchain_openai import ChatOpenAI

from config import config

from custom_tools.verification import check_env_vars

SUMMARIZE_REQUIRED_ENV_VARS = [
    'SUMMARIZING_MODEL_NAME',
    'DASHSCOPE_API_KEY',
    'DASHSCOPE_BASE_URL'
]
check_env_vars(SUMMARIZE_REQUIRED_ENV_VARS)
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL = config.SUMMARIZING_MODEL_NAME          # Change to your preferred model
MAX_TOKENS = 4096
DATE_FMT = "%Y-%m-%d"
DAILY_FILE = "user.md"              # lowercase – per-day summary
GLOBAL_FILE = "USER.md"             # uppercase – global profile


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
DAILY_SUMMARY_PROMPT = """You are analysing a user's activity log for a single day.
Below are raw memory entries (JSON lines) recorded on {date}.

Your task:
1. Extract **what the user did** that day (tasks, topics, tools used, questions asked).
2. Extract **behavioural preferences** you can infer (e.g. "prefers Python over Bash",
   "asks for concise answers", "works late at night", "frequently iterates on code").
3. Note any recurring patterns or notable one-off actions.

Format the output as Markdown with two sections:
## Activities ({date})
- …bullet list…

## Inferred Preferences / Patterns
- …bullet list…

Raw memory entries:
{entries}
"""

MERGE_SUMMARY_PROMPT = """You are maintaining a long-term user profile.

Below is the **existing global profile** (USER.md) followed by **one or more new
daily summaries** that were just generated.

Your task:
1. Merge the new information into the existing profile without losing any existing
   insights.
2. Consolidate duplicate or overlapping preferences into concise, up-to-date
   statements.
3. Add any genuinely new activities, preferences, or patterns discovered in the
   daily summaries.
4. Keep the output well-structured Markdown, using these top-level sections
   (add sub-sections freely):
   ## User Overview
   ## Behavioural Preferences
   ## Recurring Activities & Interests
   ## Notable Patterns
6. Compress information as much as possible while retaining facts, within 3000 words.

Existing USER.md:
{existing_profile}

New daily summaries to incorporate:
{new_summaries}
"""


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _today() -> date:
    return date.today()


def _date_folders(logs_dir: Path, days: int = 30) -> list[Path]:
    """Return existing date-stamped sub-folders within the last *days* days."""
    today = _today()
    folders = []
    for delta in range(1, days + 1):
        candidate = today - timedelta(days=delta)
        folder = logs_dir / candidate.strftime(DATE_FMT)
        if folder.is_dir():
            folders.append(folder)
    return folders


def _read_jsonl(path: Path) -> list[dict]:
    """Read a .jsonl file; skip malformed lines gracefully."""
    entries = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # Preserve the raw line so nothing is silently dropped
                entries.append({"raw": line})
    return entries


def _entries_to_text(entries: list[dict]) -> str:
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

def check_today(logs_dir=config.MEMORY_PATH):
    today_folder = logs_dir / _today().strftime(DATE_FMT)
    if today_folder.is_dir():
        print(f"[INFO] Today's folder already exists: {today_folder}")
        print("[INFO] No back-fill needed.")
        return True
    return False

class MemorySummarizer:
    """
    Summarises raw_memories.jsonl files using an LLM and maintains a
    global USER.md profile in the logs directory.

    Parameters
    ----------
    logs_dir : str | Path
        Path to the root logs directory.
    api_key : str, optional
        Anthropic API key.  Falls back to the ``ANTHROPIC_API_KEY`` env var.
    lookback_days : int
        How many calendar days to look back when today's folder is missing.
    model : str
        Anthropic model identifier to use for summarisation.
    """

    def __init__(
        self,
        logs_dir = config.MEMORY_PATH,
        lookback_days: int = 14,
        model: str = MODEL,
    ) -> None:
        self.logs_dir = logs_dir
        if not self.logs_dir.is_dir():
            raise FileNotFoundError(f"logs_dir does not exist: {self.logs_dir}")
        if check_today(logs_dir):
            self.need = False
            return
        else:
            self.need = True
        self.lookback_days = lookback_days
        self.model = model
        self.chat = ChatOpenAI(
            openai_api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
            model=self.model,
            temperature=0,
        )

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Main workflow:

        1. Check whether today's date folder exists.
        2. If it does NOT exist, scan the previous *lookback_days* folders
           for any that contain raw_memories.jsonl but no user.md yet.
        3. Generate a daily user.md summary for each such folder.
        4. Merge all newly created user.md files into the global USER.md.
        """
        if self.need == False:
            return

        print(f"[INFO] Scanning the previous {self.lookback_days} days …")

        past_folders = _date_folders(self.logs_dir, self.lookback_days)
        if not past_folders:
            print("[WARN] No date folders found in the lookback window. Nothing to do.")
            return

        newly_created: list[Path] = []

        for folder in past_folders:
            daily_md = folder / DAILY_FILE          # user.md  (lowercase)
            memories_file = folder / "raw_memories.jsonl"

            if daily_md.exists():
                print(f"  [SKIP] {folder.name}/user.md already exists.")
                continue

            if not memories_file.exists():
                print(f"  [SKIP] {folder.name}/raw_memories.jsonl not found.")
                continue

            print(f"  [WORK] Summarising {folder.name} …")
            summary = self._summarise_daily(memories_file, folder.name)
            daily_md.write_text(summary, encoding="utf-8")
            print(f"  [OK]   Written → {daily_md}")
            newly_created.append(daily_md)

        if not newly_created:
            print("[INFO] No new daily summaries were generated.")
            return

        print(f"\n[INFO] {len(newly_created)} new daily summary/summaries created.")
        print("[INFO] Updating global USER.md …")
        self._update_global_profile(newly_created)
        print(f"[OK]  Global profile updated → {self.logs_dir / GLOBAL_FILE}")

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the text of the first text block."""
        return self.chat.invoke(prompt).content

    def _summarise_daily(self, memories_file: Path, date_str: str) -> str:
        """
        Generate a per-day user.md summary from a raw_memories.jsonl file.
        Returns Markdown text ready to be written to disk.
        """
        entries = _read_jsonl(memories_file)
        if not entries:
            return (
                f"## Activities ({date_str})\n\n_No entries found._\n\n"
                "## Inferred Preferences / Patterns\n\n_N/A_\n"
            )

        prompt = DAILY_SUMMARY_PROMPT.format(
            date=date_str,
            entries=_entries_to_text(entries),
        )
        return self._call_llm(prompt)

    def _update_global_profile(self, new_daily_files: list[Path]) -> None:
        """
        Merge newly created daily user.md files into the global USER.md
        (uppercase) located directly inside logs_dir.

        Steps
        -----
        1. Read the existing USER.md (or use a placeholder if absent).
        2. Collect the text of every newly created daily user.md.
        3. Ask the LLM to produce an updated, merged profile.
        4. Write the result back to USER.md.
        """
        global_md_path = self.logs_dir / GLOBAL_FILE  # USER.md (uppercase)

        # --- 1. Read existing global profile ---
        if global_md_path.exists():
            existing_profile = global_md_path.read_text(encoding="utf-8").strip()
        else:
            existing_profile = "_No existing profile. This is the first run._"

        # --- 2. Collect new daily summaries ---
        summaries_parts: list[str] = []
        for path in new_daily_files:
            date_label = path.parent.name          # e.g. "2026-03-26"
            content = path.read_text(encoding="utf-8").strip()
            summaries_parts.append(f"### {date_label}\n{content}")

        new_summaries_text = "\n\n---\n\n".join(summaries_parts)

        # --- 3. Ask LLM to merge ---
        prompt = MERGE_SUMMARY_PROMPT.format(
            existing_profile=existing_profile,
            new_summaries=new_summaries_text,
        )
        updated_profile = self._call_llm(prompt)

        # --- 4. Write back ---
        global_md_path.write_text(updated_profile, encoding="utf-8")

# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Summarise raw_memories.jsonl files and maintain USER.md"
    )
    parser.add_argument(
        "logs_dir",
        help="Path to the root logs directory (must already exist)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Anthropic API key (defaults to ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=30,
        help="Number of past days to scan (default: 30)",
    )
    parser.add_argument(
        "--model",
        default=MODEL,
        help=f"Anthropic model to use (default: {MODEL})",
    )
    args = parser.parse_args()

    summarizer = MemorySummarizer(
        logs_dir=args.logs_dir,
        api_key=args.api_key,
        lookback_days=args.lookback_days,
        model=args.model,
    )
    summarizer.run()