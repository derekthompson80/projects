import mysql.connector
import os

# Database name
DATABASE_NAME = 'county_game_local'

config = {
    'user': 'root',
    'password': 'Beholder30',
    'host': '127.0.0.1',
    'port': 3306,
    'database': DATABASE_NAME,
    'raise_on_warnings': True
}

def import_religions():
    """Import religions data from the text file"""
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Clear existing data for testing
        cursor.execute("DELETE FROM religion_entities")
        cursor.execute("DELETE FROM religions")
        
        print("Importing religions data...")
        try:
            with open('CG5 Major religions .txt', 'r', encoding='utf-8', errors='replace') as file:
                lines = file.readlines()
                
                religion_name = ""
                religion_code = ""
                religion_description = ""
                current_religion_id = None
                
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    # Check if this is a religion header line (contains name and code in parentheses)
                    if line and "(" in line and ")" in line and not line.startswith("*"):
                        # Save previous religion if exists
                        if religion_name:
                            cursor.execute("""
                            INSERT INTO religions (name, code, description, parent_religion_id)
                            VALUES (%s, %s, %s, %s)
                            """, (religion_name, religion_code, religion_description, None))
                            current_religion_id = cursor.lastrowid
                            religion_description = ""
                        
                        # Parse new religion
                        parts = line.split("(")
                        religion_name = parts[0].strip()
                        religion_code = parts[1].split(")")[0].strip()
                        print(f"Found religion: {religion_name} ({religion_code})")
                        
                        # Collect description from following lines
                        i += 1
                        while i < len(lines) and not (lines[i].strip() and "(" in lines[i] and ")" in lines[i] and not lines[i].strip().startswith("*")):
                            if lines[i].strip() and not lines[i].strip().startswith("*"):
                                religion_description += lines[i].strip() + " "
                            # Check if this is an entity line
                            elif lines[i].strip().startswith("*") and current_religion_id:
                                entity_line = lines[i].strip()[1:].strip()  # Remove the * and leading/trailing whitespace
                                
                                # Parse entity name and description
                                if "-" in entity_line:
                                    entity_parts = entity_line.split("-", 1)
                                    entity_name = entity_parts[0].strip()
                                    entity_description = entity_parts[1].strip() if len(entity_parts) > 1 else ""
                                    
                                    print(f"  Found entity: {entity_name}")
                                    cursor.execute("""
                                    INSERT INTO religion_entities (religion_id, name, description)
                                    VALUES (%s, %s, %s)
                                    """, (current_religion_id, entity_name, entity_description))
                            
                            i += 1
                        
                        # Adjust counter since we're using a while loop
                        i -= 1
                    else:
                        i += 1
                
                # Save the last religion if exists
                if religion_name:
                    cursor.execute("""
                    INSERT INTO religions (name, code, description, parent_religion_id)
                    VALUES (%s, %s, %s, %s)
                    """, (religion_name, religion_code, religion_description, None))
                    current_religion_id = cursor.lastrowid
        
        except FileNotFoundError:
            print("Warning: CG5 Major religions .txt not found. Skipping religions import.")
            
        # Verify the import
        cursor.execute("SELECT COUNT(*) as count FROM religions")
        result = cursor.fetchone()
        religion_count = result[0]
        
        print(f"Number of religions imported: {religion_count}")
        
        if religion_count > 0:
            # Display some sample religions
            cursor.execute("SELECT id, name, code, description FROM religions LIMIT 5")
            religions = cursor.fetchall()
            
            print("\nSample religions:")
            for religion in religions:
                print(f"ID: {religion[0]}, Name: {religion[1]}, Code: {religion[2]}")
                print(f"Description: {religion[3][:100]}...")
                
                # Get entities for this religion
                cursor.execute("SELECT name, description FROM religion_entities WHERE religion_id = %s LIMIT 3", (religion[0],))
                entities = cursor.fetchall()
                
                if entities:
                    print("Entities:")
                    for entity in entities:
                        print(f"  - {entity[0]}: {entity[1][:50]}...")
                print()
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Religion import completed")
        
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import_religions()