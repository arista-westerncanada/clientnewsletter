import re
import urllib.request
import sys

FEDERAL_URL = "https://raw.githubusercontent.com/aristafederal/Newsletter/main/docs/index.md"

SECTIONS_TO_PULL = [
    "Software Updates",
    "Security Advisories and Field Notices",
    "Product Updates",
    "Don't Forget",
]

def fetch_federal():
    print(f"Fetching Federal newsletter from {FEDERAL_URL}...")
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

def update_local(path, federal_sections):
    with open(path, "r") as f:
        content = f.read()

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
        print("Make sure your docs/index.md has headings that match:")
        for t in SECTIONS_TO_PULL:
            print(f"  - {t}")
        sys.exit(1)

    replacements.sort(key=lambda x: x[0], reverse=True)
    for start, end, new_content in replacements:
        content = content[:start] + new_content + content[end:]

    with open(path, "w") as f:
        f.write(content)

    print(f"Updated {len(replacements)} sections in {path}")

if __name__ == "__main__":
    federal_md = fetch_federal()
    print("Extracting sections...")
    sections = extract_sections(federal_md, SECTIONS_TO_PULL)

    if not sections:
        print("ERROR: Could not find any target sections in Federal newsletter.")
        sys.exit(1)

    print("Updating local newsletter...")
    update_local("docs/index.md", sections)
    print("Done.")
