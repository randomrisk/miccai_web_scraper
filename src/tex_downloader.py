import os
import json
import glob
import arxiv
import tarfile
import asyncio
import aiohttp
import logging
from pathlib import Path
from tqdm import tqdm
from urllib.parse import quote
import time

# Configure logging
logging.basicConfig(
    filename='arxiv_download.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ArXivSourceDownloader:
    def __init__(self, json_dir, output_dir):
        self.json_dir = json_dir
        self.output_dir = output_dir
        self.source_dir = os.path.join(output_dir, "tex_sources")
        self.client = arxiv.Client()
        
        # Create directories
        os.makedirs(self.source_dir, exist_ok=True)
        
        # Configure arxiv client
        self.client = arxiv.Client(
            page_size=1,
            delay_seconds=3,  # Be nice to arXiv API
            num_retries=3
        )

    def clean_title(self, title):
        """Clean the title for better search results"""
        # Remove common special characters and extra whitespace
        title = title.lower()
        title = title.replace(":", " ")
        title = title.replace("-", " ")
        title = " ".join(title.split())
        return title

    def get_titles_from_json(self):
        """Get all paper titles from JSON files"""
        papers = []
        json_files = glob.glob(os.path.join(self.json_dir, "*.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('Title'):
                        # Store both original title and filename
                        papers.append({
                            'title': data['Title'],
                            'file': os.path.basename(json_file)
                        })
            except Exception as e:
                logging.error(f"Error reading {json_file}: {str(e)}")
        
        return papers

    async def search_and_download(self, paper):
        """Search for a paper on arXiv and download its source if available"""
        try:
            # Clean the title for search
            clean_title = self.clean_title(paper['title'])
            
            # Search arXiv
            search = arxiv.Search(
                query=f'ti:"{clean_title}"',
                max_results=1
            )
            
            results = list(self.client.results(search))
            
            if not results:
                logging.info(f"No arXiv match found for: {paper['title']}")
                return False
            
            result = results[0]
            
            # Create directory for this paper
            paper_dir = os.path.join(self.source_dir, paper['file'].replace('.json', ''))
            os.makedirs(paper_dir, exist_ok=True)
            
            # Download source files
            source_path = os.path.join(paper_dir, 'source.tar.gz')
            if not os.path.exists(source_path):
                # Get the paper ID from the entry ID
                paper_id = result.entry_id.split('/')[-1]
                source_url = f"https://arxiv.org/e-print/{paper_id}"
                
                # Download the source files
                async with aiohttp.ClientSession() as session:
                    async with session.get(source_url) as response:
                        if response.status == 200:
                            content = await response.read()
                            with open(source_path, 'wb') as f:
                                f.write(content)
                            
                            # Extract the tar.gz file
                            try:
                                with tarfile.open(source_path, 'r:gz') as tar:
                                    tar.extractall(path=paper_dir)
                                logging.info(f"Successfully downloaded and extracted source for: {paper['title']}")
                                return True
                            except Exception as e:
                                logging.error(f"Error extracting source for {paper['title']}: {str(e)}")
                                return False
                        else:
                            logging.error(f"Error downloading source for {paper['title']}: Status {response.status}")
                            return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error processing {paper['title']}: {str(e)}")
            return False

    async def process_all_papers(self):
        """Process all papers concurrently"""
        papers = self.get_titles_from_json()
        print(f"Found {len(papers)} papers to process")
        
        # Create progress bar
        progress_bar = tqdm(total=len(papers), desc="Processing papers")
        
        # Process papers with rate limiting
        results = []
        for paper in papers:
            result = await self.search_and_download(paper)
            results.append(result)
            progress_bar.update(1)
            # Be nice to arXiv API
            await asyncio.sleep(3)
        
        progress_bar.close()
        
        # Print summary
        successful = sum(1 for r in results if r)
        print(f"\nFound and processed {successful} out of {len(papers)} papers on arXiv")

async def main():
    # Configuration
    json_dir = "/home/joshua/Documents/GitHub/miccai_web_scraper/data/2024json"
    output_dir = "/home/joshua/Documents/GitHub/miccai_web_scraper/data/arxiv_sources"
    
    downloader = ArXivSourceDownloader(json_dir, output_dir)
    await downloader.process_all_papers()

if __name__ == "__main__":
    asyncio.run(main())