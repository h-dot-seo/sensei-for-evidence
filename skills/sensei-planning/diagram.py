"""Render work packages from evidence_workflow.py JSON as Mermaid on stdout."""
import argparse
import json
import sys


def label(value):
    # Encode syntax characters and whitespace controls within quoted Mermaid labels.
    return "".join(char if char.isalnum() or char in " ._-" else f"#{ord(char)};"
                   for char in " ".join(value.splitlines()))


def render(packages, view):
    nodes = {row["work_package_id"]: f"w{index}" for index, row in enumerate(packages)}
    lines = ["flowchart TD"]
    if view == "wbs":
        lines.append('    project["Project"]')
    for row in packages:
        key = row["work_package_id"]
        node = nodes[key]
        lines.append(f'    {node}["{label(key)}"]')
        if view == "wbs":
            lines.append(f"    project --> {node}")
            if row.get("deliverable"):
                lines.append(f'    {node} --> {node}d["{label(row["deliverable"])}"]')
        else:
            for prerequisite in row["depends_on"]:
                lines.append(f"    {nodes[prerequisite]} --> {node}")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("view", choices=["wbs", "dependencies"])
    args = parser.parse_args()
    try:
        print(render(json.load(sys.stdin)["work_packages"], args.view))
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Invalid workflow output: {error}\n")
