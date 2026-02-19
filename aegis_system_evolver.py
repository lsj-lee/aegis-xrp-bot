import os
import sys
import datetime
import argparse
import glob
import subprocess

# Try to import google.genai, handle failure gracefully
try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    genai = None

def load_api_key():
    """Loads the Gemini API key from .env or environment variables."""
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return os.getenv("GEMINI_API_KEY")

def evolve_system_file(target_file):
    """
    Reads the target system file, asks Gemini for improvements,
    and generates a briefing and a code proposal file in the evolution_queue.
    """
    if not HAS_GEMINI:
        print("⚠️ google-genai library not found. Cannot perform system evolution.")
        return

    api_key = load_api_key()
    if not api_key:
        print("⚠️ GEMINI_API_KEY not found. Cannot perform system evolution.")
        return

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Failed to initialize Gemini client: {e}")
        return

    if not os.path.exists(target_file):
        print(f"⚠️ Target file '{target_file}' not found.")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        current_code = f.read()

    print(f"🧬 Evolving system skeleton: {target_file}...")

    prompt = f"""
    You are an expert Python AI Architect. Your task is to analyze and improve the following Python system file: '{target_file}'.

    [Current Code]:
    {current_code}

    [Goal]:
    Refactor and improve the code to enhance readability, performance, error handling, and modularity.
    Strictly maintain the original functionality but optimize the implementation.

    [Output Requirements]:
    1.  **Briefing (Korean Markdown)**: Explain WHY you made changes, WHAT exactly changed, and the EXPECTED EFFECT.
        -   Format:
            ```markdown
            # AEGIS System Evolution Briefing
            ## 1. 사유 (Reason)
            ...
            ## 2. 변경점 (Changes)
            ...
            ## 3. 기대 효과 (Expected Effect)
            ...
            ```
    2.  **Code Proposal (Python)**: Provide the FULL, EXECUTABLE Python code for the new version of the file.
        -   Do not use placeholders.
        -   Ensure all imports are present.
        -   Ensure compatibility with the existing project structure.

    [Response Format]:
    Please strictly use the following delimiters to separate the briefing and the code:

    [BRIEFING_START]
    (Your Markdown Briefing Here)
    [BRIEFING_END]

    [CODE_START]
    (Your Python Code Here)
    [CODE_END]
    """

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        text = response.text

        # Parse the response
        briefing_start = text.find("[BRIEFING_START]")
        briefing_end = text.find("[BRIEFING_END]")
        code_start = text.find("[CODE_START]")
        code_end = text.find("[CODE_END]")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        queue_dir = "evolution_queue"
        os.makedirs(queue_dir, exist_ok=True)

        if briefing_start != -1 and briefing_end != -1:
            briefing_content = text[briefing_start + len("[BRIEFING_START]"):briefing_end].strip()
            briefing_path = os.path.join(queue_dir, f"{timestamp}_briefing.md")
            with open(briefing_path, "w", encoding="utf-8") as f:
                f.write(briefing_content)
            print(f"✅ Queue Added: {briefing_path}")
        else:
            print("⚠️ Failed to parse Briefing section from Gemini response.")

        if code_start != -1 and code_end != -1:
            code_content = text[code_start + len("[CODE_START]"):code_end].strip()

            # Remove markdown code blocks if Gemini included them inside the delimiter
            if code_content.startswith("```python"):
                code_content = code_content.replace("```python", "", 1)
            if code_content.endswith("```"):
                code_content = code_content.rsplit("```", 1)[0]

            code_content = code_content.strip()

            proposal_path = os.path.join(queue_dir, f"{timestamp}_proposal.py")
            with open(proposal_path, "w", encoding="utf-8") as f:
                f.write(f"# TARGET: {target_file}\n")
                f.write(code_content)
            print(f"✅ Queue Added: {proposal_path}")
            print(f"🚀 Proposal queued. Run 'python aegis_system_evolver.py --review' to inspect.")
        else:
            print("⚠️ Failed to parse Code section from Gemini response.")

    except Exception as e:
        print(f"⚠️ Error during Gemini generation: {e}")

def review_mode():
    """
    Lists pending proposals in evolution_queue/ and allows the user to review/apply/delete them.
    """
    queue_dir = "evolution_queue"
    if not os.path.exists(queue_dir):
        print(f"⚠️ Queue directory '{queue_dir}' does not exist.")
        return

    while True:
        # Refresh list every iteration to handle deletions/applications correctly
        proposals = sorted(glob.glob(os.path.join(queue_dir, "*_proposal.py")))

        if not proposals:
            print("✅ No pending proposals in queue.")
            return

        print("\n📋 [Pending Evolution Proposals]")
        for idx, prop_path in enumerate(proposals):
            filename = os.path.basename(prop_path)
            timestamp = filename.split("_proposal.py")[0]

            # Read target from file
            target = "Unknown"
            try:
                with open(prop_path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("# TARGET:"):
                        target = first_line.split(":", 1)[1].strip()
            except:
                pass

            print(f"[{idx+1}] {timestamp} (Target: {target})")

        choice = input("\nSelect proposal number (or 'q' to quit): ").strip().lower()
        if choice == 'q':
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(proposals):
                selected_prop = proposals[idx]
                base_name = os.path.basename(selected_prop).split("_proposal.py")[0]
                briefing_path = os.path.join(queue_dir, f"{base_name}_briefing.md")

                print(f"\n📄 Reviewing: {selected_prop}")
                if os.path.exists(briefing_path):
                    print("-" * 50)
                    with open(briefing_path, "r", encoding="utf-8") as f:
                        print(f.read())
                    print("-" * 50)
                else:
                    print("⚠️ Briefing file not found.")

                action = input("\n[A]pply / [D]elete / [C]ancel: ").strip().lower()

                if action == 'a':
                    # Apply
                    try:
                        # Git Backup Logic
                        print("\n🔄 Creating backup before applying changes...")
                        try:
                            subprocess.run(["git", "add", "."], check=False)
                            subprocess.run(["git", "commit", "-m", f"Backup before AEGIS Evolution ({datetime.datetime.now()})"], check=False)
                            print("💾 Git backup complete.")
                        except Exception as e:
                            print(f"⚠️ Git backup failed: {e}")

                        with open(selected_prop, "r", encoding="utf-8") as f:
                            lines = f.readlines()

                        target_file = "aegis_main_system.py" # Default
                        content_start_idx = 0
                        if lines and lines[0].startswith("# TARGET:"):
                            target_file = lines[0].split(":", 1)[1].strip()
                            content_start_idx = 1

                        new_code = "".join(lines[content_start_idx:])

                        with open(target_file, "w", encoding="utf-8") as f:
                            f.write(new_code)

                        print(f"✅ Applied changes to {target_file}.")

                        # Cleanup
                        os.remove(selected_prop)
                        if os.path.exists(briefing_path):
                            os.remove(briefing_path)

                        input("\nPress Enter to continue...")

                    except Exception as e:
                        print(f"❌ Error applying proposal: {e}")
                        input("\nPress Enter to continue...")

                elif action == 'd':
                    confirm = input("🗑️ Are you sure you want to delete this proposal? (y/n): ").strip().lower()
                    if confirm == 'y':
                        os.remove(selected_prop)
                        if os.path.exists(briefing_path):
                            os.remove(briefing_path)
                        print("🗑️ Proposal deleted.")
                        input("\nPress Enter to continue...")

                elif action == 'c':
                    continue

            else:
                print("⚠️ Invalid selection.")
        except ValueError:
            print("⚠️ Invalid input.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AEGIS System Skeleton Evolver")
    parser.add_argument("file", nargs="?", default="aegis_main_system.py", help="The system file to evolve (default: aegis_main_system.py)")
    parser.add_argument("--review", action="store_true", help="Review pending proposals in queue")

    args = parser.parse_args()

    if args.review:
        review_mode()
    else:
        evolve_system_file(args.file)
