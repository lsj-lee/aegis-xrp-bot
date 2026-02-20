import os
import sys
import datetime
import argparse
import glob
import subprocess
import json
import requests

# Try to import google.genai, handle failure gracefully
try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    genai = None

CONFIG_FILE = ".aegis_config.json"
USER_REQUESTS_FILE = "user_requests.txt"

def load_github_config():
    """Loads GitHub config from .aegis_config.json."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def read_user_requests():
    """Reads content from user_requests.txt."""
    if not os.path.exists(USER_REQUESTS_FILE):
        return ""
    try:
        with open(USER_REQUESTS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""

def clear_user_requests():
    """Clears the content of user_requests.txt."""
    try:
        with open(USER_REQUESTS_FILE, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass

def create_pr_for_evolution(owner, repo, token, target_file, new_code, request_content):
    """
    Creates a new branch, commits the evolved code, pushes it, and opens a PR.
    """
    if not token or not owner or not repo:
        print("⚠️ GitHub configuration missing. Skipping PR creation.")
        return False

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"evolution/auto-{timestamp}"
    original_branch = "main"

    # Shorten request for title
    title_suffix = request_content.split('\n')[0][:40] if request_content else "Routine Evolution"
    pr_title = f"🧬 AEGIS Evolution: {title_suffix}"
    pr_body = f"## Autonomous Evolution Proposal\n\n### Commander's Orders:\n{request_content}\n\n### Changes:\nApplied automated evolution to `{target_file}`."

    try:
        # Get current branch
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
        if res.returncode == 0:
            original_branch = res.stdout.strip()

        print(f"🔄 Initiating PR sequence: {branch_name}")

        # 1. Create and switch to new branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True)

        # 2. Overwrite target file with new code
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_code)

        # 3. Git Add & Commit
        subprocess.run(["git", "add", target_file], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Evolve {target_file}: {title_suffix}"], check=True, capture_output=True)

        # 4. Push
        print(f"⬆️ Pushing branch {branch_name}...")
        subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True)

        # 5. Create PR via API
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Determine base branch (default to main)
        base_branch = "main"
        try:
             repo_info = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers).json()
             base_branch = repo_info.get("default_branch", "main")
        except:
             pass

        payload = {
            "title": pr_title,
            "body": pr_body,
            "head": branch_name,
            "base": base_branch
        }

        resp = requests.post(url, headers=headers, json=payload)

        # 6. Restore original branch
        subprocess.run(["git", "checkout", original_branch], check=True, capture_output=True)

        if resp.status_code == 201:
            data = resp.json()
            print(f"✅ PR Created Successfully: {data['html_url']}")
            return True
        else:
            print(f"⚠️ PR Creation Failed ({resp.status_code}): {resp.text}")
            return False

    except Exception as e:
        print(f"❌ Error during PR creation: {e}")
        # Attempt to restore
        subprocess.run(["git", "checkout", original_branch], capture_output=True)
        return False

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

    # Load User Requests early to determine target file
    user_request_content = read_user_requests()

    # [Smart Target Detection]
    # If the default target is main_system but the user asks for dashboard/evolver, switch target.
    if target_file == "aegis_main_system.py" and user_request_content:
        content_lower = user_request_content.lower()
        if "dashboard" in content_lower or "대시보드" in content_lower:
            target_file = "aegis_dashboard.py"
            print(f"🔄 Target switched to '{target_file}' based on user request.")
        elif "evolver" in content_lower or "시스템 진화" in content_lower:
            target_file = "aegis_system_evolver.py"
            print(f"🔄 Target switched to '{target_file}' based on user request.")
        elif "automation" in content_lower or "오토메이션" in content_lower:
            target_file = "aegis_automation.py"
            print(f"🔄 Target switched to '{target_file}' based on user request.")

    if not os.path.exists(target_file):
        print(f"⚠️ Target file '{target_file}' not found.")
        return

    print(f"🧬 Evolving system skeleton: {target_file}...")

    user_context = ""
    if user_request_content:
        print(f"📝 User Requests Found: {user_request_content}")
        user_context = f"\n[CRITICAL USER REQUESTS]:\n{user_request_content}\n\nYou MUST address the above user requests in your code evolution."

    with open(target_file, "r", encoding="utf-8") as f:
        current_code = f.read()

    prompt = f"""
    You are an expert Python AI Architect. Your task is to analyze and improve the following Python system file: '{target_file}'.

    [Current Code]:
    {current_code}

    {user_context}

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

            # Automatic PR Creation (If user requests exist)
            if user_request_content:
                print("🤖 Auto-executing PR creation based on User Requests...")
                gh_config = load_github_config()

                # Check for valid config
                if gh_config and gh_config.get("github_token"):
                    success = create_pr_for_evolution(
                        gh_config.get("github_owner"),
                        gh_config.get("github_repo"),
                        gh_config.get("github_token"),
                        target_file,
                        code_content,
                        user_request_content
                    )
                    if success:
                        clear_user_requests()
                        print("🧹 User requests cleared.")
                else:
                    print("⚠️ GitHub config invalid or missing token. Skipping Auto-PR.")

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
