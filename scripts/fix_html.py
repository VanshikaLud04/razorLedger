import pathlib

count = 0
for f in pathlib.Path('frontend').rglob('*.html'):
    content = f.read_text()
    if '\\"' in content:
        content = content.replace('\\"', '"')
        f.write_text(content)
        count += 1
        print(f"Fixed {f}")
print(f"Total files fixed: {count}")
