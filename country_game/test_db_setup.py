"""
Test script to verify that the db_setup.py module works correctly.
This script imports and runs the functions from db_setup.py to ensure
they work without triggering the NoneType error.
"""

import sys
import os

# Import the functions directly from db_setup.py
from db_setup import create_database, import_data

def main():
    """Run the database setup functions and verify they work correctly."""
    print("Testing database setup functions...")
    
    try:
        # Try to create the database and tables
        print("Running create_database()...")
        create_database()
        
        # Try to import data
        print("Running import_data()...")
        import_data()
        
        print("Test completed successfully!")
        return True
    except Exception as e:
        print(f"Error during test: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print(f"Test {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)