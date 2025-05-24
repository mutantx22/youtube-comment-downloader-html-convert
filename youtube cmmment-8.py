import os
import subprocess
import json
from jinja2 import Template
import urllib.parse
import yt_dlp
import re



def get_video_title(youtube_url):
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return info['title']
    except Exception as e:
        print(f"Error retrieving video title: {e}")
        return None


def sanitize_filename(title):
    # Remove characters that are invalid in filenames
    return re.sub(r'[\\/*?:"<>|]', '', title)

def download_comments(youtube_id, output_file):
    try:
        # Run youtube-comment-downloader command to download comments
        command = ["youtube-comment-downloader", "--youtubeid", youtube_id, "--output", output_file]
        result = subprocess.run(command, shell=True, check=True, text=True)
        if result.returncode != 0:
            print(f"Error downloading comments: {result.stderr}")
    except Exception as e:
        print(f"Failed to download comments: {e}")

def convert_votes_to_number(votes):
    # Convert 'K' notation in votes to numeric value
    if 'K' in votes:
        return int(float(votes.replace('K', '')) * 1000)
    else:
        return int(votes)

def build_comment_hierarchy(comments):
    comment_dict = {}
    top_level_comments = []

    for comment in comments:
        comment['replies'] = []
        comment_dict[comment['cid']] = comment

        # Determine if this comment is a reply by checking if it contains a period
        if '.' in comment['cid']:
            parent_id = comment['cid'].split('.')[0]
            if parent_id in comment_dict:
                comment_dict[parent_id]['replies'].append(comment)
        else:
            top_level_comments.append(comment)

    return top_level_comments

def convert_json_to_html(input_file, output_file, youtube_id, video_title):
    try:
        # Read the JSON data from the input file
        with open(input_file, 'r', encoding='utf-8') as file:
            json_data = file.readlines()

        comments = []

        # Process each JSON comment and append it to the list
        for line in json_data:
            try:
                comment = json.loads(line.strip())
                comment['votes'] = convert_votes_to_number(comment['votes'])
                comments.append(comment)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid JSON line: {e}")

        # Build the hierarchical comment structure
        all_comments = build_comment_hierarchy(comments)

        # Sort only the top-level comments by votes in descending order
        all_comments.sort(key=lambda x: x['votes'], reverse=True)

        # Define the HTML template
        template_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ video_title }} - YouTube Comments</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #1c1c1c;
                    color: #fff;
                    margin: 0;
                    padding: 20px;
                }

                h1 {
                    color: #fff;
                    margin-top: 0;
                    padding-bottom: 20px;
                    border-bottom: 1px solid #666;
                }

                .comment {
                    margin-bottom: 20px;
                    padding: 10px;
                    background-color: #333;
                    border-radius: 5px;
                }

                .comment h3 {
                    font-size: 18px;
                    margin-bottom: 5px;
                    color: #fff;
                }

                .comment p {
                    font-size: 14px;
                    margin-bottom: 10px;
                    color: #fff;
                }

                .comment .time, .comment .votes {
                    font-size: 12px;
                    color: #999999;
                }

                .reply {
                    margin-left: 20px;
                    border-left: 2px solid #444;
                    padding-left: 10px;
                    margin-top: 10px;
                }

                a {
                    color: #1e90ff;
                    text-decoration: none;
                }

                a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <h1>{{ video_title }} - YouTube Comments</h1>
            {% for comment in comments %}
                {{ render_comment(comment) }}
            {% endfor %}
        </body>
        </html>
        """

        # Function to recursively render comments and replies
        def render_comment(comment):
            return f"""
            <div class="comment">
                <h3>{comment['author']}</h3>
                <p>{comment['text']}</p>
                <p class="votes">Upvotes: {comment['votes']}</p>
                <p class="time">Posted {comment['time']}</p>
                <p><a href="https://www.youtube.com/watch?v={youtube_id}&lc={comment['cid']}" target="_blank">View on YouTube</a></p>
                <div class="reply">
                    {"".join([render_comment(reply) for reply in comment['replies']])}
                </div>
            </div>
            """

        # Create a Jinja2 template object
        template = Template(template_content)
        template.globals['render_comment'] = render_comment

        # Render the template with the comment data
        rendered_html = template.render(comments=all_comments, video_title=video_title)

        # Write the rendered HTML to the output file
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(rendered_html)

    except Exception as e:
        print(f"Failed to convert JSON to HTML: {e}")

# Prompt the user to enter the YouTube URL
youtube_url = input("Enter the YouTube URL: ")

try:
    # Parse the query parameters from the URL
    parsed_url = urllib.parse.urlparse(youtube_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Extract the YouTube video ID
    youtube_id = query_params.get("v", [None])[0]

    if not youtube_id:
        raise ValueError("Missing 'v' parameter.")

except Exception as e:
    print(f"Invalid YouTube URL. {e}")
    exit(1)
	
# Set the output file names
title = get_video_title(youtube_url)
if not title:
    exit(1)

safe_title = sanitize_filename(title)

json_file = f"{safe_title}.json"
html_file = f"{safe_title}.html"

# Download comments using youtube-comment-downloader
download_comments(youtube_id, json_file)

# Convert the JSON file to HTML
convert_json_to_html(json_file, html_file, youtube_id, title)

# Print the file names for reference
print(f"JSON file: {json_file}")
print(f"HTML file: {html_file}")
