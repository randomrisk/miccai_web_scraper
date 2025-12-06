from bs4 import BeautifulSoup
import requests
import json
import os
import time
import re
from pathlib import Path
from urllib.parse import urljoin

BASE_URL = "https://papers.miccai.org/miccai-2025/"
# Compute project root and use a project-relative data directory so the script
# works across platforms (macOS, Linux, Windows) instead of hard-coding
# an absolute `/home/...` path which may not exist on the current machine.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAVE_DIR = PROJECT_ROOT / 'data' / '2025json'
os.makedirs(str(SAVE_DIR), exist_ok=True)

def extract_links():
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Build absolute URLs from hrefs. `urljoin` correctly handles relative
    # paths and prevents duplicating path segments like 'miccai-2025/miccai-2025'.
    links = []
    for a in soup.select("a[href*='-Paper']"):
        href = a.get('href', '').strip()
        if not href:
            continue
        if href.startswith('http'):
            full = href
        else:
            full = urljoin(BASE_URL, href)
        links.append(full)

    # Optionally save link list for debugging
    # with open("links.txt", "w") as f:
    #     for link in links:
    #         f.write(link + "\n")

    return links

def safe_find_text(element, selector=None, class_name=None, text_pattern=None, default=""):
    """Safely find and extract text from HTML elements"""
    try:
        if text_pattern:
            found = element.find(string=re.compile(text_pattern))
        elif selector and class_name:
            found = element.find(selector, {'class': class_name})
        elif selector:
            found = element.find(selector)
        else:
            found = element
        
        return found.text.strip() if found else default
    except (AttributeError, TypeError):
        return default

def parse_html(html_content):
    """
    Parse HTML content to extract relevant information about a MICCAI paper.
    
    Args:
        html_content (str): HTML content to parse
        
    Returns:
        dict: Dictionary containing extracted information
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title (with fallback)
        title = safe_find_text(soup.find('h1', {'class': 'post-title'}))
        if not title:
            title = safe_find_text(soup.find('title'))
        if not title:
            raise ValueError("Could not find paper title")
        
        # Extract authors
        authors = []
        authors_div = soup.find('div', {'class': 'post-tags'})
        if authors_div:
            author_links = authors_div.find_all('a', {'class': 'post-category'})
            authors = [author.text.strip() for author in author_links if author and author.text]
        
        # Extract abstract
        abstract = ""
        abstract_section = soup.find('h1', text='Abstract')
        if abstract_section:
            next_p = abstract_section.find_next('p')
            if next_p:
                abstract = next_p.text.strip()
        
        # Extract PDF link
        pdf_link = ""
        links_section = soup.find('h1', {'id': 'link-id'})
        if links_section:
            pdf_link = links_section.find_next('a', href=re.compile(r'\.pdf$'))
            if pdf_link:
                pdf_link = pdf_link['href']

        # Extract BibTeX
        bibtex = ""
        bibtex_section = soup.find('h1', {'id': 'bibtex-id'})
        if bibtex_section:
            code_element = bibtex_section.find_next('code')
            if code_element:
                bibtex = code_element.text.strip()
        
        # Extract topics
        topics = []
        topics_div = soup.find_all('div', {'class': 'post-categories'})
        for div in topics_div:
            topic_links = div.find_all('a', {'class': 'post-category'})
            topics.extend([topic.text.strip() for topic in topic_links if topic and topic.text])
        topics = list(set(topics))  # Remove duplicates
        
        # Extract reviews
        reviews = []
        review_sections = soup.find_all('h3', string=re.compile("Review #"))
        for section in review_sections:
            review_content = {}
            current = section.find_next()
            while current and not (current.name == 'h3' and 'Review #' in current.text):
                if current.name == 'strong':
                    key = current.text.strip()
                    value = current.find_next('blockquote')
                    if value:
                        review_content[key] = value.text.strip()
                current = current.find_next()
            if review_content:  # Only add non-empty reviews
                reviews.append(review_content)
        
        # Extract meta-review
        meta_review_content = []
        meta_review_sections = soup.find_all('h2', string=re.compile("Meta-review #"))
        for section in meta_review_sections:
            meta_review = {}
            current = section.find_next()
            while current and not (current.name == 'h2' and 'Meta-review #' in current.text):
                if current.name == 'strong':
                    key = current.text.strip()
                    value = current.find_next('blockquote')
                    if value:
                        meta_review[key] = value.text.strip()
                current = current.find_next()
            if meta_review:  # Only add non-empty meta-reviews
                meta_review_content.append(meta_review)
        
        # Extract author feedback
        author_feedback = ""
        feedback_section = soup.find('h1', {'id': 'authorFeedback-id'})
        if feedback_section:
            feedback_blockquote = feedback_section.find_next('blockquote')
            if feedback_blockquote:
                author_feedback = feedback_blockquote.text.strip()
        
        # Extract code repository
        code_repository = "N/A"
        code_section = soup.find('h1', {'id': 'code-id'})
        if code_section:
            next_p = code_section.find_next('p')
            if next_p:
                code_repository = next_p.text.strip()
        
        # Extract dataset
        dataset = "N/A"
        dataset_section = soup.find('h1', {'id': 'dataset-id'})
        if dataset_section:
            next_p = dataset_section.find_next('p')
            if next_p:
                dataset = next_p.text.strip()
        
        return {
            'Title': title,
            'Author(s)': authors,
            'Abstract': abstract,
            'PDF': pdf_link,
            'BibTex': bibtex,
            'Topics': topics,
            'Reviews': reviews,
            'Meta-review': meta_review_content,
            'Author Feedback': author_feedback,
            'Code Repository': code_repository,
            'Dataset': dataset
        }
    except Exception as e:
        print(f"Error parsing HTML: {str(e)}")
        raise

def save_json(data, output_dir, filename):
    """Save data as JSON file"""
    # Accept both `str` and `Path` for `output_dir` and ensure directory exists
    output_dir = str(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    # Configuration
    output_dir = PROJECT_ROOT / 'data' / '2024json'
    
    # Read links
    links = extract_links()
    
    # Process each link
    for link in links:
        try:
            # Read the HTML file
            response = requests.get(link)
            response.raise_for_status()
            html_content = response.text
            
            # Parse the HTML
            data = parse_html(html_content)
            
            # Generate filename from paper title
            #safe_title = re.sub(r'[^\w\s-]', '', data['Title'])
            #safe_title = re.sub(r'[-\s]+', '_', safe_title)
            #filename = f"{safe_title[:100]}.json"
            # use the paper ID as filename
            filename = link.split('/')[-1].replace('.html', '.json')
            
            # Save the data
            save_json(data, output_dir, filename)
            print(f"Successfully saved data for: {data['Title']}")
            
            # Add a small delay to be nice to the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing link {link}: {str(e)}")
            continue

if __name__ == "__main__":
    main()