import csv
import re

def convert_txt_to_csv(input_file, output_file):
    """
    Convert a text file containing religion information to a CSV file.
    
    Args:
        input_file (str): Path to the input text file
        output_file (str): Path to the output CSV file
    """
    # Read the text file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skip the header line
    if content.startswith("Major religions are as follows:"):
        content = content[len("Major religions are as follows:"):].strip()
    
    # Split by double newlines to separate entries
    entries = [entry.strip() for entry in content.split("\n\n") if entry.strip()]
    
    # Process each entry to get individual lines
    lines = []
    for entry in entries:
        entry_lines = [line.strip() for line in entry.split("\n") if line.strip()]
        lines.extend(entry_lines)
        
    # Remove any remaining header line that might have been parsed as a separate line
    lines = [line for line in lines if line != "Major religions are as follows:"]
    
    # Prepare data for CSV
    religions_data = []
    
    # Process each line to extract religion information
    for line in lines:
        # Special cases for entries that don't follow the standard format
        if "G'k'r-lek'non" in line or line.startswith("G'k'r"):
            religions_data.append(["G'k'r-lek'non", "", "lord of the Qlippoth, master of demons"])
            continue
            
        # Try to match "Name (Abbr) - Description" pattern
        pattern = r'^(.*?)(?:\s*\((.*?)\))?\s*-\s*(.*?)$'
        match = re.match(pattern, line)
        
        if match:
            # Line has the format "Name (Abbr) - Description"
            name = match.group(1).strip()
            abbreviation = match.group(2).strip() if match.group(2) else ""
            description = match.group(3).strip()
            religions_data.append([name, abbreviation, description])
        else:
            # Check if the line contains a dash anywhere
            if ' - ' in line:
                parts = line.split(' - ', 1)
                name_part = parts[0].strip()
                description = parts[1].strip()
                
                # Check if name part has abbreviation in parentheses
                abbr_match = re.search(r'(.*?)\s*\((.*?)\)', name_part)
                if abbr_match:
                    name = abbr_match.group(1).strip()
                    abbreviation = abbr_match.group(2).strip()
                else:
                    name = name_part
                    abbreviation = ""
                
                religions_data.append([name, abbreviation, description])
            else:
                # No dash found, check if it's a name with a description after a comma
                comma_parts = line.split(', ', 1)
                if len(comma_parts) > 1 and not comma_parts[0].endswith(('the Just', 'the Builder', 'the Delver', 'the Rememberer', 'the Keeper of Families')):
                    name = comma_parts[0].strip()
                    description = comma_parts[1].strip()
                    religions_data.append([name, "", description])
                else:
                    # Treat the whole line as a name with no description
                    name_part = line.strip()
                    
                    # Check if name part has abbreviation in parentheses
                    abbr_match = re.search(r'(.*?)\s*\((.*?)\)', name_part)
                    if abbr_match:
                        name = abbr_match.group(1).strip()
                        abbreviation = abbr_match.group(2).strip()
                    else:
                        name = name_part
                        abbreviation = ""
                    
                    religions_data.append([name, abbreviation, ""])
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(['Religion Name', 'Abbreviation', 'Description'])
        # Write data
        writer.writerows(religions_data)
    
    print(f"Conversion complete. CSV file saved to {output_file}")

if __name__ == "__main__":
    input_file = "CG5 Major religions .txt"
    output_file = "country_game_utilites/religions.csv"
    convert_txt_to_csv(input_file, output_file)