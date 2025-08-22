import subprocess

# Test with sample HTML
test_html = """9
<head>
<title>HTML Parser - I</title>
</head>
<object type="application/x-flash" 
  data="your-file.swf" 
  width="0" height="0">
  <!-- <param name="movie" value="your-file.swf" /> -->
  <param name="quality" value="high"/>
</object>"""

print("Testing with sample HTML:")
result = subprocess.run(['python', 'html_parser.py'], 
                        input=test_html, 
                        text=True, 
                        capture_output=True)
print(f"Output:\n{result.stdout}")

# Expected output:
expected = """head
title
object
-> type > application/x-flash
-> data > your-file.swf
-> width > 0
-> height > 0
param
-> name > quality
-> value > high
"""

print("\nExpected output:")
print(expected)

if result.stdout.strip() == expected.strip():
    print("\nTest PASSED! ✓")
else:
    print("\nTest FAILED! ✗")
    print("Differences:")
    for i, (actual_line, expected_line) in enumerate(zip(result.stdout.strip().split('\n'), expected.strip().split('\n'))):
        if actual_line != expected_line:
            print(f"Line {i+1}:")
            print(f"  Actual:   '{actual_line}'")
            print(f"  Expected: '{expected_line}'")