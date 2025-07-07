"""
Country Game Code Suggestions Module

This module provides functions to load and access code update suggestions
from the JSON file without modifying the existing codebase.
"""

import json
import os

def get_code_suggestions():
    """
    Returns a list of code update suggestions from the JSON file.
    
    Returns:
        list: A list of dictionaries containing code update suggestions.
              Each dictionary has the following keys:
              - title: The title of the suggestion
              - description: A detailed description of the suggestion
              - rule_reference: The game rule that the suggestion is based on
              - implementation_hint: A hint for how to implement the suggestion
    """
    try:
        # Get the path to the JSON file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'code_update_suggestions.json')
        
        # Load the suggestions from the JSON file
        with open(file_path, 'r') as file:
            suggestions = json.load(file)
        
        return suggestions
    except Exception as e:
        print(f"Error loading code suggestions: {str(e)}")
        return []

def get_suggestion_by_title(title):
    """
    Returns a specific suggestion by its title.
    
    Args:
        title (str): The title of the suggestion to retrieve
        
    Returns:
        dict or None: The suggestion dictionary if found, None otherwise
    """
    suggestions = get_code_suggestions()
    
    for suggestion in suggestions:
        if suggestion['title'] == title:
            return suggestion
    
    return None

def get_suggestions_by_category(category):
    """
    Returns suggestions filtered by a category keyword in the title or description.
    
    Args:
        category (str): The category keyword to filter by
        
    Returns:
        list: A list of suggestion dictionaries matching the category
    """
    suggestions = get_code_suggestions()
    filtered_suggestions = []
    
    for suggestion in suggestions:
        if (category.lower() in suggestion['title'].lower() or 
            category.lower() in suggestion['description'].lower()):
            filtered_suggestions.append(suggestion)
    
    return filtered_suggestions

# Example usage:
if __name__ == "__main__":
    # Print all suggestions
    suggestions = get_code_suggestions()
    print(f"Found {len(suggestions)} code update suggestions:")
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion['title']}")
        print(f"   Description: {suggestion['description']}")
        print(f"   Rule Reference: {suggestion['rule_reference']}")
        print(f"   Implementation Hint: {suggestion['implementation_hint']}")
    
    # Example of getting a specific suggestion
    print("\nExample of getting a specific suggestion:")
    free_actions = get_suggestion_by_title("Free Actions Implementation")
    if free_actions:
        print(f"Found: {free_actions['title']}")
        print(f"Description: {free_actions['description']}")
    
    # Example of filtering suggestions by category
    print("\nExample of filtering suggestions by category:")
    country_suggestions = get_suggestions_by_category("Country")
    print(f"Found {len(country_suggestions)} suggestions related to 'Country':")
    for suggestion in country_suggestions:
        print(f"- {suggestion['title']}")