import unittest
from src.scraper import fetch_html, parse_html

class TestScraper(unittest.TestCase):

    def test_fetch_html(self):
        url = 'https://conferences.miccai.org/2023/papers/001-Paper0829.html'
        html = fetch_html(url)
        self.assertIsNotNone(html)
        self.assertIn('<html', html)

    def test_parse_html(self):
        url = 'https://conferences.miccai.org/2023/papers/001-Paper0829.html'
        html = fetch_html(url)
        data = parse_html(html)
        self.assertIn('Title', data)
        self.assertIn('Authors', data)
        self.assertIn('Abstract', data)
        self.assertIn('Topics', data)
        self.assertIn('Reviews', data)
        self.assertIn('Meta-review', data)
        self.assertIn('Author Feedback', data)
        self.assertIn('Post-rebuttal Meta-Reviews', data)
        self.assertIn('Code Repository', data)
        self.assertIn('Dataset', data)

if __name__ == '__main__':
    unittest.main()
