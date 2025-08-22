# Test script to verify imports work correctly
print("Starting import test...")

try:
    from flask import Flask
    print("✓ Successfully imported Flask")
    
    from flask_bootstrap import Bootstrap5
    print("✓ Successfully imported Bootstrap5 from flask_bootstrap")
    
    # Create a simple Flask app and initialize Bootstrap5
    app = Flask(__name__)
    bootstrap = Bootstrap5(app)
    print("✓ Successfully initialized Bootstrap5")
    
    print("All imports successful! The fix worked.")
except Exception as e:
    print(f"❌ Error: {e}")