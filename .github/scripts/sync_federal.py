import re
import urllib.request
import sys
import os
from datetime import datetime

FEDERAL_URL = "https://raw.githubusercontent.com/aristafederal/Newsletter/main/docs/index.md"

SECTIONS_TO_PULL = [
    "Software Updates",
    "Security Advisories and Field Notices",
    "Product Updates",
    "Don't Forget",
]

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def fetch_federal():
    print(f"Fetching Federal newsletter...")
    with urllib.request.urlopen(FEDERAL_URL) as r:
        content = r.read().decode("utf-8")
    print(f"Fetched {len(content)} characters")
    return content

def clean_heading(text):
    return re.sub(r"[#*!]", "", text).strip().lower()

def extract_sections(markdown, targets):
    heading_re = re.compile(r"^(#{1,3} .+)$", re.MULTILINE)
    matches = list(heading_re.finditer(markdown))
    sections = {}
    for i, match in enumerate(matches):
        raw_heading = match.group(1)
        clean = clean_heading(raw_heading)
        level = len(re.match(r"^(#+)", raw_heading).group(1))
        for target in targets:
            t = target.lower().rstrip("!")
            if t in clean:
                start = match.start()
                end = len(markdown)
                for j in range(i + 1, len(matches)):
                    next_raw = matches[j].group(1)
                    next_level = len(re.match(r"^(#+)", next_raw).group(1))
                    if next_level <= level:
                        end = matches[j].start()
                        break
                sections[target] = markdown[start:end].rstrip()
                print(f"  Found section: {target}")
                break
    return sections

def get_current_month_label(content):
    match = re.search(r"#\s+Arista Western Canada.*?·\s+(\w+ \d{4})", content)
    if match:
        return match.group(1)
    match = re.search(r"#\s+Arista Western Canada.*?(\w+ \d{4})", content)
    if match:
        return match.group(1)
    now = datetime.now()
    return f"{MONTHS[now.month - 2]} {now.year}" if now.month > 1 else f"December {now.year - 1}"

def get_next_month_label():
    now = datetime.now()
    return f"{MONTHS[now.month - 1]} {now.year}"

def label_to_folder(label):
    return label.replace(" ", "")

def archive_current(current_label):
    folder = label_to_folder(current_label)
    archive_dir = f"docs/{folder}"
    archive_path = f"{archive_dir}/index.md"
    os.makedirs(archive_dir, exist_ok=True)
    with open("docs/index.md", "r") as f:
        content = f.read()
    with open(archive_path, "w") as f:
        f.write(content)
    print(f"Archived current newsletter to {archive_path}")
    return folder

def update_mkdocs(current_label, archive_folder):
    next_label = get_next_month_label()
    with open("mkdocs.yml", "r") as f:
        content = f.read()

    existing_archives = re.findall(r"  - .+?: \w+/index\.md\n", content)
    new_nav = f"nav:\n  - {next_label}: index.md\n  - {current_label}: {archive_folder}/index.md\n"
    for archive in existing_archives:
        if archive_folder not in archive:
            new_nav += archive

    content = re.sub(r"nav:[\s\S]+?(?=\n\w|\Z)", new_nav, content)

    with open("mkdocs.yml", "w") as f:
        f.write(content)
    print(f"Updated mkdocs.yml: {next_label} current, {current_label} archived")

def update_local(federal_sections, next_label):
    with open("docs/index.md", "r") as f:
        content = f.read()

    content = re.sub(
        r"(#\s+Arista Western Canada[^\n]*·\s+)\w+ \d{4}",
        f"\\g<1>{next_label}",
        content
    )

    heading_re = re.compile(r"^(#{1,3} .+)$", re.MULTILINE)
    matches = list(heading_re.finditer(content))
    replacements = []

    for i, match in enumerate(matches):
        raw_heading = match.group(1)
        clean = clean_heading(raw_heading)
        level = len(re.match(r"^(#+)", raw_heading).group(1))
        for target, federal_content in federal_sections.items():
            t = target.lower().rstrip("!")
            if t in clean:
                start = match.start()
                end = len(content)
                for j in range(i + 1, len(matches)):
                    next_raw = matches[j].group(1)
                    next_level = len(re.match(r"^(#+)", next_raw).group(1))
                    if next_level <= level:
                        end = matches[j].start()
                        break
                replacements.append((start, end, federal_content + "\n\n"))
                print(f"  Replacing section: {target}")
                break

    if not replacements:
        print("WARNING: No matching sections found in local file.")
        sys.exit(1)

    replacements.sort(key=lambda x: x[0], reverse=True)
    for start, end, new_content in replacements:
        content = content[:start] + new_content + content[end:]

    with open("docs/index.md", "w") as f:
        f.write(content)
    print(f"Updated {len(replacements)} sections in docs/index.md")

if __name__ == "__main__":
    with open("docs/index.md", "r") as f:
        current_content = f.read()

    current_label = get_current_month_label(current_content)
    next_label = get_next_month_label()
    print(f"Current edition: {current_label}")
    print(f"New edition: {next_label}")

    print("Archiving current newsletter...")
    archive_folder = archive_current(current_label)

    print("Updating mkdocs.yml...")
    update_mkdocs(current_label, archive_folder)

    print("Fetching Federal newsletter...")
    federal_md = fetch_federal()

    print("Extracting sections...")
    sections = extract_sections(federal_md, SECTIONS_TO_PULL)

    if not sections:
        print("ERROR: Could not find any target sections in Federal newsletter.")
        sys.exit(1)

    print("Updating local newsletter...")
    update_local(sections, next_label)
    print("Done.")
