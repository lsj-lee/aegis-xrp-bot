import os
import sys
import datetime
import argparse

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
    and generates a briefing and a code proposal file.
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

        if briefing_start != -1 and briefing_end != -1:
            briefing_content = text[briefing_start + len("[BRIEFING_START]"):briefing_end].strip()
            with open("aegis_briefing.md", "w", encoding="utf-8") as f:
                f.write(briefing_content)
            print("✅ Generated: aegis_briefing.md")
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

            with open("aegis_skeleton_proposal.py", "w", encoding="utf-8") as f:
                f.write(f"# TARGET: {target_file}\n")
                f.write(code_content)
            print("✅ Generated: aegis_skeleton_proposal.py")
        else:
            print("⚠️ Failed to parse Code section from Gemini response.")

    except Exception as e:
        print(f"⚠️ Error during Gemini generation: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AEGIS System Skeleton Evolver")
    parser.add_argument("file", nargs="?", default="aegis_main_system.py", help="The system file to evolve (default: aegis_main_system.py)")
    args = parser.parse_args()

    evolve_system_file(args.file)
