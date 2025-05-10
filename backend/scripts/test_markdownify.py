import os
import sys
import django
# Remove markdownify and BeautifulSoup imports related to conversion
# from markdownify import markdownify as md
# from bs4 import BeautifulSoup, Comment
import html2text # Import html2text
import re # Import re for post-processing
import logging
import warnings # Import warnings module

# Add the project root directory ('/app' in the container) to the Python path
# This ensures that Django can find the 'config' module
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

# Set the DJANGO_SETTINGS_MODULE environment variable
# --- Adjust 'mailmind.settings' if your settings file is located differently ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    print("Please ensure DJANGO_SETTINGS_MODULE is set correctly and django.setup() can run.")
    exit(1)

# --- Suppress unnecessary warnings and logs --- 
# Suppress the django-q UserWarning
warnings.filterwarnings("ignore", message=r".*Retry and timeout are misconfigured.*", category=UserWarning)
# Set idle_manager logger level to ERROR to hide INFO/DEBUG messages
logging.getLogger('mailmind.imap.idle_manager').setLevel(logging.ERROR)
logging.getLogger('mailmind.imap.apps').setLevel(logging.ERROR) # Also suppress the ImapConfig starting message
# --------------------------------------------- 

# --- Adjust 'core.models' and 'Email' if your model location/name is different ---
try:
    from mailmind.core.models import Email
except ImportError:
    print("Error: Could not import Email model from mailmind.core.models.")
    print("Please adjust the import path in the script if necessary.")
    exit(1)


EMAIL_ID = 1330

try:
    email = Email.objects.get(pk=EMAIL_ID)

    # --- Adjust 'body_html' if the HTML content field has a different name ---
    html_content = getattr(email, 'body_html', None)

    if html_content is None or not isinstance(html_content, str):
        # Try 'body' as an alternative field name (second fallback)
        print("Info: Field 'body_html' not found or not string, trying 'body'...")
        html_content = getattr(email, 'body', None)
        if html_content is None or not isinstance(html_content, str):
             print(f"Error: Could not find suitable HTML content field ('body_html' or 'body') for Email {EMAIL_ID}.")
             exit(1)
        else:
            print("Info: Using field 'body' for HTML content.")
    elif not html_content:
         print(f"Info: Email {EMAIL_ID} has an empty body_html/body field.")
         # Proceeding to show empty markdown is fine.

    # Convert to string to ensure it's not None
    html_content_str = str(html_content)

    print(f"--- Original HTML (first 500 chars) for Email {EMAIL_ID} ---")
    print(html_content_str[:500])
    print("\n...\n")

    # --- Remove BeautifulSoup Pre-processing ---
    # soup = BeautifulSoup(html_content_str, 'html.parser')
    # ... (previous BS logic removed) ...
    # cleaned_html = str(soup)
    # -------------------------------------------

    # --- Remove markdownify call --- 
    # markdown_content_raw = md(cleaned_html, heading_style="ATX", escape_asterisks=False, newline_style="DOUBLE", wrap=False)
    # --------------------------------------

    # --- Convert HTML to Markdown using html2text ---
    h = html2text.HTML2Text()
    # Configuration options:
    h.ignore_images = True  # Ignore images
    h.body_width = 0        # Disable line wrapping (keep original line breaks)
    h.ignore_emphasis = False # Keep emphasis (bold/italic) if possible
    h.ignore_links = False    # Keep links
    # You might experiment with other options like h.ignore_tables = True if needed

    markdown_content = h.handle(html_content_str)
    # -----------------------------------------------

    # --- Remove old Post-processing ---
    # processed_lines = []
    # ... (previous post-processing logic removed) ...
    # markdown_content_final = "\n".join(l.strip() for l in markdown_content_final.splitlines())
    # ---------------------------

    # --- Minimal Post-processing for html2text output ---
    # REMOVED: Remove excessive blank lines that might still occur
    # markdown_content_final = re.sub(r'\n{3,}', '\n\n', markdown_content).strip()
    markdown_content_final = markdown_content.strip() # Just strip leading/trailing whitespace
    # Optional: Remove leading/trailing whitespace from each line if desired
    # markdown_content_final = "\n".join(l.strip() for l in markdown_content_final.splitlines())
    # ----------------------------------------------------

    print(f"--- Converted Markdown (Using html2text) for Email {EMAIL_ID} ---")
    print(markdown_content_final) # Print the final markdown
    print("---------------------------------------------------------------------------")

    # Optional: Save to file
    try:
        # Ensure the 'backend' directory exists relative to the script location if saving there
        save_dir = os.path.dirname(os.path.abspath(__file__)) # Save in the same dir as the script
        save_path = os.path.join(save_dir, f"email_{EMAIL_ID}_markdown.md")
        with open(save_path, "w", encoding='utf-8') as f:
            f.write(markdown_content_final)
        print(f"Markdown content saved to {save_path}")
    except Exception as e:
        print(f"Error saving markdown to file: {e}")


except Email.DoesNotExist:
    print(f"Error: Email with ID {EMAIL_ID} not found.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    import traceback
    traceback.print_exc() 