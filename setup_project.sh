#!/bin/bash

# Create project directory
mkdir -p assignment-2026
cd assignment-2026

# Create root Python files
touch app.py
touch requirements.txt
touch users.db
touch minidisc.db

# Create static directories
mkdir -p static/images/profile-pictures
mkdir -p static/output
touch static/style.css
touch static/animation.js

# Create templates directory with primary HTML files
mkdir -p templates
html_files=("home.html" "login.html" "register.html" "database.html" 
            "collection-detail.html" "collections.html" "user.html" "search-database.html")
for html in "${html_files[@]}"; do
    touch "templates/${html}"
done

echo "done!"