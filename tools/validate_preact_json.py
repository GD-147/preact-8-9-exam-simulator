#!/usr/bin/env python3

import json
import sys
from pathlib import Path

BAD_SEQUENCES = [
    "\ufffd",
    "ÔøΩ",
    "ï¿½",
    "Ã",
    "Â",
    "â€",
]

MATH_SYMBOLS = [
    "−",
    "×",
    "÷",
    "²",
    "³",
    "√",
    "π",
    "θ",
    "≤",
    "≥",
    "°",
]

EXPECTED = {
    "english": {
        "questions": 40,
        "choices": 4,
    },
    "math": {
        "questions": 35,
        "choices": 5,
    },
    "reading": {
        "questions": 25,
        "choices": 4,
    },
    "science": {
        "questions": 30,
        "choices": 4,
    },
    "full_length": {
        "questions": 130,
        "choices": None,
    },
}

def fail(msg):
    print("ERROR:", msg)
    return 1

def scan_strings(obj, path="root"):
    problems = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            problems.extend(scan_strings(v, f"{path}.{k}"))

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            problems.extend(scan_strings(v, f"{path}[{i}]"))

    elif isinstance(obj, str):
        for bad in BAD_SEQUENCES:
            if bad in obj:
                problems.append(
                    f"{path}: suspicious encoding sequence {bad!r}"
                )

    return problems

def main():
    if len(sys.argv) != 3:
        print(
            "Usage: validate_preact_json.py "
            "<section> <json_file>"
        )
        sys.exit(2)

    section = sys.argv[1].lower()
    path = Path(sys.argv[2])

    if section not in EXPECTED:
        sys.exit(fail(f"unknown section: {section}"))

    if not path.exists():
        sys.exit(fail(f"file not found: {path}"))

    print("=" * 60)
    print("PREACT 8/9 JSON VALIDATOR")
    print("=" * 60)

    # UTF-8 strict read
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        sys.exit(fail(f"file is not valid UTF-8: {e}"))

    print("OK: UTF-8")

    # JSON syntax
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(fail(f"invalid JSON: {e}"))

    print("OK: valid JSON")

    if isinstance(data, dict) and "questions" in data:
        questions = data["questions"]
    elif isinstance(data, list):
        questions = data
    else:
        sys.exit(
            fail(
                'expected a JSON array or object with "questions"'
            )
        )

    if not isinstance(questions, list):
        sys.exit(fail('"questions" must be an array'))

    expected_count = EXPECTED[section]["questions"]

    print(f"Questions found: {len(questions)}")
    print(f"Questions expected: {expected_count}")

    if len(questions) != expected_count:
        sys.exit(
            fail(
                f"question count mismatch: "
                f"{len(questions)} != {expected_count}"
            )
        )

    ids = []
    errors = []

    for i, q in enumerate(questions, 1):
        prefix = f"Question {i}"

        if not isinstance(q, dict):
            errors.append(f"{prefix}: not an object")
            continue

        qid = q.get("id")
        if not qid:
            errors.append(f"{prefix}: missing id")
        else:
            ids.append(str(qid))

        prompt = q.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{prefix}: missing/empty prompt")

        explanation = q.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            errors.append(f"{prefix}: missing/empty explanation")

        choices = q.get("choices")

        if not isinstance(choices, dict):
            errors.append(f"{prefix}: choices must be an object")
            continue

        expected_choices = EXPECTED[section]["choices"]

        if expected_choices is not None:
            expected_letters = (
                ["A", "B", "C", "D"]
                if expected_choices == 4
                else ["A", "B", "C", "D", "E"]
            )

            actual_letters = list(choices.keys())

            if actual_letters != expected_letters:
                errors.append(
                    f"{prefix}: choices are "
                    f"{actual_letters}, expected {expected_letters}"
                )

        for letter, text in choices.items():
            if not isinstance(text, str) or not text.strip():
                errors.append(
                    f"{prefix}: empty choice {letter}"
                )

        correct = q.get("correct")

        if correct is None:
            errors.append(
                f"{prefix}: missing correct answer"
            )
        elif correct not in choices:
            errors.append(
                f"{prefix}: correct={correct!r} "
                f"is not one of the available choices"
            )

    # duplicate IDs
    duplicates = sorted(
        {x for x in ids if ids.count(x) > 1}
    )

    if duplicates:
        errors.append(
            "Duplicate IDs: " + ", ".join(duplicates)
        )

    # Encoding / mojibake audit
    encoding_problems = scan_strings(data)

    if encoding_problems:
        errors.extend(encoding_problems)

    print()
    print("=== STRUCTURE AUDIT ===")

    if errors:
        for e in errors:
            print("ERROR:", e)

        print()
        print(
            f"FAILED: {len(errors)} problem(s) found"
        )
        sys.exit(1)

    print("OK: IDs present and unique")
    print("OK: prompts present")
    print("OK: choices valid")
    print("OK: correct answers valid")
    print("OK: explanations present")
    print("OK: no known mojibake sequences")

    if section == "math":
        print()
        print("=== MATH SYMBOL AUDIT ===")

        found = [s for s in MATH_SYMBOLS if s in raw]

        if found:
            print(
                "Unicode math symbols preserved:",
                " ".join(found)
            )
        else:
            print(
                "INFO: none of the monitored math symbols "
                "occur in this file"
            )

    print()
    print("VALIDATION PASSED")
    print("=" * 60)

if __name__ == "__main__":
    main()
