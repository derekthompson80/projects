# Required Libraries
import docx
import language_tool_python
import ssl
import requests
import os
import datetime
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Monkey patch requests to disable SSL verification
original_get = requests.get
def patched_get(*args, **kwargs):
    kwargs['verify'] = False
    return original_get(*args, **kwargs)
requests.get = patched_get

# Read text from a .docx file
def read_docx(file_path):
    doc = docx.Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

# Correct grammar and spelling using LanguageTool
def correct_text(text):
    try:
        # Disable SSL certificate verification (not recommended for production)
        ssl._create_default_https_context = ssl._create_unverified_context
        # Use version 6.0 which is compatible with Java 11
        tool = language_tool_python.LanguageTool('en-US', language_tool_download_version='6.0')
        matches = tool.check(text)
        return language_tool_python.utils.correct(text, matches)
    except SystemError as e:
        # Handle Java version compatibility issues
        if "LanguageTool requires Java" in str(e):
            print(f"Java version compatibility issue: {str(e)}")
            print("Grammar checking disabled due to Java version compatibility.")
            return text
        raise
    except Exception as e:
        print(f"Error in grammar correction: {str(e)}")
        # Return original text if correction fails
        return text

# Write corrected text to a .txt file
def write_txt(file_path, text):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)

# Process blog entry text
def process_blog_entry(title, content):
    """
    Process a blog entry by correcting grammar and spelling

    Args:
        title (str): The title of the blog entry
        content (str): The content of the blog entry

    Returns:
        tuple: (corrected_title, corrected_content)
    """
    corrected_title = correct_text(title)
    corrected_content = correct_text(content)
    return corrected_title, corrected_content

# Save blog entry to file system
def save_blog_entry(title, content, author, media=None, blog_dir="blog_entries"):
    """
    Save a blog entry to the file system

    Args:
        title (str): The title of the blog entry
        content (str): The content of the blog entry
        author (str): The author of the blog entry
        media (dict, optional): Media information (photo or video) to include with the entry
        blog_dir (str): Directory to save blog entries

    Returns:
        str: Path to the saved blog entry
    """
    # Create blog directory if it doesn't exist
    if not os.path.exists(blog_dir):
        os.makedirs(blog_dir)

    # Create a filename based on the title and timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    filename = f"{timestamp}_{safe_title}.txt"
    file_path = os.path.join(blog_dir, filename)

    # Format the blog entry
    entry_text = f"Title: {title}\n"
    entry_text += f"Author: {author}\n"
    entry_text += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    # Add media information if provided
    if media and media.get('id'):
        entry_text += f"Media-ID: {media.get('id', '')}\n"
        entry_text += f"Media-Type: {media.get('type', '')}\n"
        entry_text += f"Media-URL: {media.get('url', '')}\n"
        entry_text += f"Media-Thumbnail: {media.get('thumbnail', '')}\n"
        entry_text += f"Media-Width: {media.get('width', '')}\n"
        entry_text += f"Media-Height: {media.get('height', '')}\n"
        entry_text += f"Media-Attribution: {media.get('attribution', '')}\n"

    entry_text += f"\n{content}\n"

    # Write to file
    write_txt(file_path, entry_text)
    return file_path

# Main function
def process_document(input_file, output_file):
    try:
        raw_text = read_docx(input_file)
        corrected = correct_text(raw_text)
        write_txt(output_file, corrected)
        print(f"Corrected text saved to: {output_file}")
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        # Re-raise the exception to be handled by the caller
        raise

# Example usage
if __name__ == "__main__":
    process_document("Derek's journal.docx", "corrected_journal.txt")
