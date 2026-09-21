import json
import subprocess
import sys
import time
from pathlib import Path


# =========================================================
# Prime Agent RPC Client
# =========================================================

class PrimeAgentClient:

    def __init__(self):

        self.process = subprocess.Popen(
            [
                "bash",
                "./../prime-agent.sh",

                "--mode", "rpc",
                "--no-session",

                "--provider", "groq",
                "--model", "openai/gpt-oss-20b",
                
                # Keep reasoning controlled because Groq currently
                # has an 8K TPM limit.
                "--thinking", "low",

                "--no-context-files",
                "--no-prompt-templates",

                "--tools", "ipython",
                "--autonomous-max-tokens", "2000",
                "--autonomous-max-turns", "1",
            ],

            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,

            # Show Prime Agent errors in our terminal.
            stderr=None,

            text=True,
            bufsize=1,
        )

        # Prime Agent RPC supports automatic retry for transient
        # provider errors such as 429 rate limits.
        self._send_command({
            "type": "set_auto_retry",
            "enabled": True,
        })

    # -----------------------------------------------------
    # Low-level RPC command
    # -----------------------------------------------------

    def _send_command(self, command):

        if self.process.poll() is not None:
            raise RuntimeError(
                "Prime Agent process is no longer running."
            )

        self.process.stdin.write(
            json.dumps(command) + "\n"
        )

        self.process.stdin.flush()

    # -----------------------------------------------------
    # Send prompt
    # -----------------------------------------------------

    def send_prompt(self, message):

        request = {
            "id": "review-agent-request",
            "type": "prompt",
            "message": message,
        }

        print()
        print(
            "[RPC] Sending task to Prime Agent...",
            flush=True,
        )

        self._send_command(request)

        events = []

        import time
        for line in self.process.stdout:

            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)

            except json.JSONDecodeError:
                continue

            events.append(event)

            event_type = event.get("type")

            # -------------------------------------------------
            # Agent lifecycle
            # -------------------------------------------------

            if event_type == "agent_start":

                print(
                    "[AGENT] Started",
                    flush=True,
                )

            elif event_type == "agent_end":

                print(
                    "[AGENT] Finished",
                    flush=True,
                )

                break

            # -------------------------------------------------
            # Turn lifecycle
            # -------------------------------------------------

            elif event_type == "turn_start":

                print(
                    "[TURN] Started",
                    flush=True,
                )

            elif event_type == "turn_end":

                message_data = event.get(
                    "message",
                    {},
                )

                stop_reason = message_data.get(
                    "stopReason"
                )

                if stop_reason == "error":

                    error_message = message_data.get(
                        "errorMessage",
                        "",
                    )

                    print(
                        f"[TURN] Error: {error_message}",
                        flush=True,
                    )

                else:

                    print(
                        "[TURN] Finished",
                        flush=True,
                    )

            # -------------------------------------------------
            # Assistant streaming
            # -------------------------------------------------

            elif event_type == "message_update":

                assistant_event = event.get(
                    "assistantMessageEvent",
                    {},
                )

                message_type = assistant_event.get(
                    "type"
                )

                if message_type == "text_delta":

                    delta = assistant_event.get(
                        "delta",
                        "",
                    )

                    if delta:

                        print(
                            delta,
                            end="",
                            flush=True,
                        )

                elif message_type == "thinking_delta":

                    delta = assistant_event.get(
                        "delta",
                        "",
                    )

                    if delta:

                        print(
                            f"\n[THINKING] {delta}",
                            end="",
                            flush=True,
                        )

            # -------------------------------------------------
            # Tool started
            # -------------------------------------------------

            elif event_type == "tool_execution_start":

                tool_name = event.get(
                    "toolName",
                    "unknown",
                )

                print(
                    f"\n[TOOL START] {tool_name}",
                    flush=True,
                )

            # -------------------------------------------------
            # Tool progress
            # -------------------------------------------------

            elif event_type == "tool_execution_update":

                tool_name = event.get(
                    "toolName",
                    "unknown",
                )

                print(
                    f"[TOOL UPDATE] {tool_name}",
                    flush=True,
                )

            # -------------------------------------------------
            # Tool finished
            # -------------------------------------------------

            elif event_type == "tool_execution_end":

                tool_name = event.get(
                    "toolName",
                    "unknown",
                )

                is_error = event.get(
                    "isError",
                    False,
                )

                print(
                    f"[TOOL END] {tool_name} "
                    f"ERROR={is_error}",
                    flush=True,
                )

                # Print compact tool output.
                result = event.get(
                    "result",
                    {},
                )

                content = result.get(
                    "content",
                    [],
                )

                for item in content:

                    if item.get("type") == "text":

                        text = item.get(
                            "text",
                            "",
                        )

                        if text:

                            print(
                                "[TOOL RESULT]",
                                text[:4000],
                                flush=True,
                            )

            # -------------------------------------------------
            # Automatic retry
            # -------------------------------------------------

            elif event_type == "auto_retry_start":

                delay_ms = event.get(
                    "delayMs",
                    0,
                )

                attempt = event.get(
                    "attempt",
                    "?",
                )

                print(
                    f"\n[RETRY] Attempt {attempt}; "
                    f"waiting {delay_ms} ms...",
                    flush=True,
                )

            elif event_type == "auto_retry_end":

                success = event.get(
                    "success",
                    False,
                )

                print(
                    f"[RETRY] Finished "
                    f"success={success}",
                    flush=True,
                )

            # -------------------------------------------------
            # Extension errors
            # -------------------------------------------------

            elif event_type == "extension_error":

                print(
                    "\n[EXTENSION ERROR]",
                    event,
                    flush=True,
                )

        return events

    # -----------------------------------------------------
    # Extract final assistant text
    # -----------------------------------------------------

    def get_text(self, events):

        output = []

        for event in events:

            if event.get("type") != "message_update":
                continue

            assistant_event = event.get(
                "assistantMessageEvent",
                {},
            )

            if assistant_event.get("type") == "text_delta":

                output.append(
                    assistant_event.get(
                        "delta",
                        "",
                    )
                )

        return "".join(output)

    # -----------------------------------------------------
    # Close
    # -----------------------------------------------------

    def close(self):

        if self.process.poll() is not None:
            return

        try:

            if self.process.stdin:
                self.process.stdin.close()

        except (BrokenPipeError, OSError):
            pass

        try:

            self.process.wait(
                timeout=5
            )

        except subprocess.TimeoutExpired:

            self.process.terminate()

            try:

                self.process.wait(
                    timeout=2
                )

            except subprocess.TimeoutExpired:

                self.process.kill()
                self.process.wait()


# =========================================================
# AI Review Scraper Agent
# =========================================================

class AIReviewAgent:

    def __init__(self):

        self.prime = PrimeAgentClient()

        self.project_root = (
            Path(__file__).resolve().parent
        )

        self.generated_dir = (
            self.project_root / "generated"
        )

        self.output_dir = (
            self.project_root / "output"
        )

        self.generated_dir.mkdir(
            exist_ok=True
        )

        self.output_dir.mkdir(
            exist_ok=True
        )

    # -----------------------------------------------------
    # Autonomous scraping
    # -----------------------------------------------------

    def scrape(self, url):

        generated_file = (
            self.generated_dir /
            "review_scraper.py"
        )

        output_file = (
            self.output_dir /
            "reviews.json"
        )

        # Remove stale results from a previous run.
        if generated_file.exists():
            generated_file.unlink()

        if output_file.exists():
            output_file.unlink()

        prompt = f"""
Generate a Playwright review scraper for this target:

TARGET: {url}
OUTPUT SCRIPT: {generated_file}
OUTPUT JSON: {output_file}

Use the IPython tool exactly once. In that single IPython call:
1. Open the REAL target with async Playwright.
2. Inspect the DOM and identify the actual review container and fields for review_text, rating, author, and date.
3. Identify how reviews are loaded (pagination, Load More, or infinite scroll).
4. Write a complete standalone Python scraper to {generated_file}.

For the IPython inspection call, use top-level await only. NEVER write asyncio.run(), asyncio.get_event_loop(), or asyncio.run_until_complete() in the IPython call. Start Playwright exactly with: from playwright.async_api import async_playwright; pw = await async_playwright().start(); browser = await pw.chromium.launch(headless=True); page = await browser.new_page(); await page.goto(url, wait_until="domcontentloaded"). The generated standalone scraper may use asyncio.run(main()) because it runs as a separate Python process. It must save a JSON list to {output_file}. Do not guess selectors or invent review data.

Playwright and Chromium are already installed. Do NOT install packages. Do NOT execute the generated scraper. Do NOT create reviews.json yourself. After writing {generated_file}, finish.
"""

        return self.prime.send_prompt(
            prompt
        )

    def execute_generated_scraper(self):

        generated_file = self.generated_dir / "review_scraper.py"

        if not generated_file.exists():
            print("[EXECUTOR] Generated scraper not found")
            return False

        print("[EXECUTOR] Running generated scraper...")

        result = subprocess.run(
            [sys.executable, str(generated_file)],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.stdout:
            print("[SCRAPER STDOUT]")
            print(result.stdout)

        if result.stderr:
            print("[SCRAPER STDERR]")
            print(result.stderr)

        if result.returncode != 0:
            print(f"[EXECUTOR] Scraper failed with exit code {result.returncode}")
            return False

        print("[EXECUTOR] Generated scraper completed successfully")
        return True

    # -----------------------------------------------------
    # Close
    # -----------------------------------------------------

    def close(self):

        self.prime.close()


# =========================================================
# Validation
# =========================================================

def validate_output(project_root):

    generated_file = (
        project_root /
        "generated" /
        "review_scraper.py"
    )

    output_file = (
        project_root /
        "output" /
        "reviews.json"
    )

    print()
    print("=" * 50)
    print("              CHECKING RESULT")
    print("=" * 50)

    # -----------------------------------------------------
    # Generated scraper
    # -----------------------------------------------------

    print()

    if generated_file.exists():

        print(
            "Ã¢Å“â€œ Generated scraper found:"
        )

        print(
            generated_file
        )

    else:

        print(
            "Ã¢Å“â€” Generated scraper NOT found"
        )

    # -----------------------------------------------------
    # JSON output
    # -----------------------------------------------------

    print()

    if not output_file.exists():

        print(
            "Ã¢Å“â€” output/reviews.json NOT found"
        )

        return False

    print(
        "Ã¢Å“â€œ Review output found:"
    )

    print(
        output_file
    )

    try:

        with open(
            output_file,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

    except Exception as e:

        print(
            "Ã¢Å“â€” Could not parse reviews.json:"
        )

        print(e)

        return False

    if not isinstance(data, list):

        print(
            "Ã¢Å“â€” reviews.json top level "
            "must be a JSON list"
        )

        return False

    print()

    print(
        f"Ã¢Å“â€œ Reviews extracted: {len(data)}"
    )

    if len(data) == 0:

        print(
            "Ã¢Å¡Â  JSON is valid but contains "
            "zero reviews"
        )

        return False

    # -----------------------------------------------------
    # Basic schema validation
    # -----------------------------------------------------

    required_fields = {
        "author",
        "rating",
        "review_text",
        "date",
    }

    valid_count = 0

    for review in data:

        if not isinstance(review, dict):
            continue

        review_text = review.get("review_text")

        if (
            isinstance(review_text, str)
            and review_text.strip()
        ):

            valid_count += 1

    if valid_count == 0:

        print(
            "Ã¢Å“â€” No review objects contain "
            "expected fields"
        )

        return False

    print(
        f"Ã¢Å“â€œ Review objects validated: "
        f"{valid_count}/{len(data)}"
    )

    return True


# =========================================================
# CLI
# =========================================================

def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python agent.py <url>"
        )

        sys.exit(1)

    url = sys.argv[1]

    print()
    print("=" * 50)
    print("        AI REVIEW SCRAPER AGENT")
    print("=" * 50)

    print()
    print("Target:")
    print(url)

    print()
    print("Starting autonomous scraping...")

    agent = AIReviewAgent()

    project_root = (
        Path(__file__).resolve().parent
    )

    try:

        events = agent.scrape(url)

        scraper_ok = agent.execute_generated_scraper()

        if not scraper_ok:
            success = False
        else:
            success = validate_output(
                project_root
            )

        print()

        if success:

            print(
                "Ã¢Å“â€œ SCRAPING COMPLETED SUCCESSFULLY"
            )

        else:

            print(
                "Ã¢Å“â€” SCRAPING DID NOT PRODUCE "
                "A VALID RESULT"
            )

        print()
        print("=" * 50)

        if not success:
            sys.exit(2)

    finally:

        agent.close()


if __name__ == "__main__":
    main()