<img width="1151" height="1765" alt="image" src="https://github.com/user-attachments/assets/620a5690-d3a2-4783-b368-42ad013b62ea" /># LLAMA.CPP JSON to Word Converter

A Flask-based web application that converts JSON chat conversations into formatted Microsoft Word documents.

## Features

- Drag & drop JSON file upload
- Customizable output options:
  - Date & time display
  - Horizontal dividers
  - AI model information
  - Prompt data (tokens/timing)
  - Message numbering
  - Custom user/assistant names
- Multi-language support (UI and document)
- Automatic formatting with colors and styles

## Requirements

- Python 3.8+
- Flask
- python-docx

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/json-to-word-converter.git
cd json-to-word-converter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
