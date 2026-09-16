import os, glob, re

files = glob.glob('frontend/src/**/*.jsx', recursive=True)

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # We want to replace all occurrences of '$' that are used as currency
    # like '$45,230' or 'Total Fee Amount ($)'.
    # We must NOT replace '${' which is JS string interpolation!
    
    # Match '$' not followed by '{'
    new_content = re.sub(r'\$(?!\{)', '₹', content)
    
    if new_content != content:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print(f'Updated {f}')
