# Text to CSV Converter for Religion Data

This project contains a Python script that converts a text file containing religion information into a CSV (Comma-Separated Values) file. The script is specifically designed to handle the format of the "CG5 Major religions .txt" file.

## Files

- `CG5 Major religions .txt`: The original text file containing religion information.
- `txt_to_csv_converter_improved.py`: The Python script that converts the text file to CSV.
- `religions.csv`: The output CSV file containing the structured religion data.

## How to Use

1. Ensure you have Python installed on your system.
2. Place the `CG5 Major religions .txt` file in the same directory as the script.
3. Run the script using the following command:

```
python txt_to_csv_converter_improved.py
```

4. The script will generate a file named `religions.csv` in the same directory.

## CSV Format

The generated CSV file has the following columns:

1. **Religion Name**: The name of the religion or deity.
2. **Abbreviation**: The abbreviation of the religion, if available (e.g., "Pr" for "Primean Faith").
3. **Description**: A description of the religion or deity.

## Features

- Handles multi-line entries in the text file.
- Extracts abbreviations from parentheses in the religion names.
- Properly formats descriptions with quotation marks.
- Removes header lines and empty entries.
- Special handling for entries with unique formatting.

## Example

Original text entry:
```
Primean Faith (Pr) - Devoted to Primus, a monotheistic faith that has echoes of medieval Christianity...
```

Converted CSV entry:
```
Primean Faith,Pr,"Devoted to Primus, a monotheistic faith that has echoes of medieval Christianity..."
```

## Notes

- The script is designed to handle the specific format of the "CG5 Major religions .txt" file. It may need modifications to work with other text files.
- The script uses regular expressions to parse the text file, which may need adjustments if the format of the text file changes.