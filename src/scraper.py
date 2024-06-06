import requests
from bs4 import BeautifulSoup
import json
import os

def fetch_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for successful response
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_html(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Extract the title
    title = soup.select_one('h1').text.strip() if soup.select_one('h1') else 'Title not found'

    # Extract the authors
    author_heading = soup.find('h1', id='author-id')
    authors = author_heading.find_next('p').text.strip() if author_heading else 'Authors not found'

    # Extract the abstract
    abstract_div = soup.find('h1', id="abstract-id")
    abstract = abstract_div.find_next('p').text.strip() if abstract_div else 'Abstract not found'

    # Extract Reviews
    reviews = []
    review_sections = soup.find_all('h3', id=lambda x: x and x.startswith('review-'))
    for review_section in review_sections:
        review_title = review_section.text.strip()
        review_content = review_section.find_next('ul').text.strip()
        reviews.append({'Review Title': review_title, 'Review Content': review_content})

    # Extract Primary Meta-Review
    meta_review_header = soup.find('h1', id='metareview-id')
    if meta_review_header:
        meta_review_content = meta_review_header.find_next('ul').text.strip()
    else:
        meta_review_content = 'Meta-review not found'

    # Extract Author Feedback
    author_feedback_header = soup.find('h1', id="authorFeedback-id")
    author_feedback = author_feedback_header.find_next('blockquote').text.strip() if author_feedback_header else 'Author Feedback not found'

    # Extract Post-rebuttal Meta-Reviews
    post_rebuttal_meta_reviews = []
    post_rebuttal_meta_reviews_header = soup.find('h1', id='postrebuttal-id')
    if post_rebuttal_meta_reviews_header:
        meta_review_headers = post_rebuttal_meta_reviews_header.find_all_next('h2', id=lambda x: x and x.startswith('meta-review'))
        for meta_review_header in meta_review_headers:
            meta_review_title = meta_review_header.text.strip()
            meta_review_content = meta_review_header.find_next('ul').text.strip()
            post_rebuttal_meta_reviews.append({
                'Meta-review Title': meta_review_title,
                'Meta-review Content': meta_review_content
            })
    else:
        post_rebuttal_meta_reviews.append({'Meta-review Title': 'Post-rebuttal Meta-Reviews not found', 'Meta-review Content': ''})

    # Extract Topics
    topics_div = soup.find('div', class_='post-categories')
    topics = ''
    if topics_div:
        topics = ' | '.join([a.text.strip() for a in topics_div.find_all('a', class_='post-category')])
    else:
        topics = 'Topics not found'

    # Extract Link to the code repository
    code_repository_header = soup.find('h1', id='code-id')
    code_repository = ''
    if code_repository_header:
        code_repository = code_repository_header.find_next('a').text.strip()

    # Extract Link to the dataset(s)
    dataset_header = soup.find('h1', id='dataset-id')
    dataset = ''
    if dataset_header:
        dataset = dataset_header.find_next('p').text.strip()

    # Prepare the extracted data
    extracted_data = {
        'Title': title,
        'Authors': authors,
        'Abstract': abstract,
        'Topics': topics,
        'Reviews': reviews,
        'Meta-review': meta_review_content,
        'Author Feedback': author_feedback,
        'Post-rebuttal Meta-Reviews': post_rebuttal_meta_reviews,
        'Code Repository': code_repository,
        'Dataset': dataset
    }

    return extracted_data

def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    # Fetch the main page and extract all paper links
    base_url = "https://conferences.miccai.org"
    url = f"{base_url}/2023/papers/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    links = [base_url + a['href'] for a in soup.select("a[href^='/2023/papers/']")]

    # Loop through all links (except the first three)
    for link in links[3:]:
        html = fetch_html(link)
        if html:
            data = parse_html(html)
            filename = f"data/{link.split('/')[-1].replace('.html', '.json')}"
            save_to_json(data, filename)

if __name__ == '__main__':
    if not os.path.exists('data'):
        os.makedirs('data')
    main()


## Store in one json file:
# def main():
#     # Fetch the main page and extract all paper links
#     base_url = "https://conferences.miccai.org"
#     url = f"{base_url}/2023/papers/"
#     response = requests.get(url)
#     soup = BeautifulSoup(response.content, "html.parser")
#     links = [base_url + a['href'] for a in soup.select("a[href^='/2023/papers/']")]

#     # Collect all data in a list
#     all_data = []

#     # Loop through all links (except the first three)
#     for link in links[3:]:
#         html = fetch_html(link)
#         if html:
#             data = parse_html(html)
#             all_data.append(data)

#     # Save all data to a single JSON file
#     save_to_json(all_data, "data/miccai_2023_papers.json")

# if __name__ == '__main__':
#     if not os.path.exists('data'):
#         os.makedirs('data')
#     main()