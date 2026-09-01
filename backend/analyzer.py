import os
import json
import hashlib
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Cache to avoid calling AI for identical solutions
_cache = {}


def get_solution_hash(code: str) -> str:
    """Generate a hash of the solution code for caching."""
    return hashlib.md5(code.encode()).hexdigest()


def analyze_solution(file_path: str, code: str) -> dict:
    """
    Send the DSA solution to Gemini for analysis.
    Returns structured JSON with topic, pattern, complexity, revision schedule.
    Uses caching — identical code won't trigger a second API call.
    """
    # Check cache first
    code_hash = get_solution_hash(code)
    if code_hash in _cache:
        print(f"Cache hit for {file_path} — skipping AI call")
        return _cache[code_hash]

    # DSA Analyzer Persona — Golden Master Format Prompt
    prompt = f"""
Role:
You are an expert DSA mentor and code analyst specializing in competitive programming patterns.

Context:
A student submitted a C solution to a LeetCode problem. 
File path: {file_path}

Task:
Analyze the code and identify:
1. The DSA topic (e.g. Arrays, Linked List, Trees, DP, Graphs)
2. The algorithm pattern (e.g. Two Pointers, Sliding Window, BFS, Memoization)
3. Time complexity in Big O notation
4. Space complexity in Big O notation
5. A brief approach summary (1-2 sentences)
6. How many days until next revision (use: Easy=7, Medium=3, Hard=1)

Format:
Return ONLY a valid JSON object with these exact keys:
{{
  "topic": "",
  "pattern": "",
  "time_complexity": "",
  "space_complexity": "",
  "approach_summary": "",
  "next_revision_days": 0
}}

Constraints:
- Return ONLY the JSON object, no extra text, no markdown, no backticks
- If you cannot determine something, use "Unknown"
- next_revision_days must be an integer

Code to analyze:
{code}
"""

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    result_text = response.text.strip()

    # Parse JSON response
    result = json.loads(result_text)

    # Store in cache
    _cache[code_hash] = result
    print(f"Analysis complete for {file_path}: {result['pattern']}")

    return result