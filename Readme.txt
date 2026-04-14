File Organizer is a Python-based automation tool designed to simplify file management by organizing files into structured folders based on their types. It helps users maintain a clean and efficient workspace by automatically sorting scattered files into categorized directories such as images, documents, videos, and more.

Features:
Automatically scans a selected directory for files
Categorizes files based on extensions (e.g., .jpg, .pdf, .mp4)
Creates folders dynamically if they do not already exist
Moves files into appropriate folders for better organization
Renames duplicate files to avoid conflicts
Improves file accessibility and reduces manual effort

Tech Stack:
Language: Python
Modules Used:
OS – for file and directory handling
shuttle – for moving files

How It Works:
1.The program scans the target directory.
2.Identifies file types based on their extensions.
3.Matches each file with a predefined category.
4.Creates folders for each category if not present.
5.Moves files into their respective folders.
6.Handles duplicate file names by renaming them uniquely.