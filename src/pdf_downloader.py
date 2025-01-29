import os
import json
import asyncio
import aiohttp #pip3 install aiohttp
import glob 
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(
    filename='pdf_download.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PDFDownloader:
    def __init__(self, json_dir, pdf_dir, max_concurrent=10):
        self.json_dir = json_dir
        self.pdf_dir = pdf_dir
        self.max_concurrent = max_concurrent
        self.session = None
        self.progress_bar = None
        
        # Create PDF directory if it doesn't exist
        os.makedirs(pdf_dir, exist_ok=True)

    async def init_session(self):
        """Initialize aiohttp session with custom settings"""
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    def get_pdf_links(self):
        """Get all PDF links from JSON files"""
        pdf_links = []
        json_files = glob.glob(os.path.join(self.json_dir, "*.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('PDF'):
                        # Get the paper ID from the PDF URL
                        paper_id = data['PDF'].split('/')[-1]
                        pdf_links.append((data['PDF'], paper_id))
            except Exception as e:
                logging.error(f"Error reading {json_file}: {str(e)}")
        
        return pdf_links

    async def download_pdf(self, pdf_url, filename):
        """Download a single PDF file"""
        output_path = os.path.join(self.pdf_dir, filename)
        
        # Skip if file already exists
        if os.path.exists(output_path):
            logging.info(f"Skipping {filename} - already exists")
            self.progress_bar.update(1)
            return True

        try:
            async with self.session.get(pdf_url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(output_path, 'wb') as f:
                        f.write(content)
                    self.progress_bar.update(1)
                    return True
                else:
                    logging.error(f"Error downloading {pdf_url}: Status {response.status}")
                    self.progress_bar.update(1)
                    return False
        except Exception as e:
            logging.error(f"Error downloading {pdf_url}: {str(e)}")
            self.progress_bar.update(1)
            return False

    async def download_all(self):
        """Download all PDFs concurrently"""
        await self.init_session()
        
        try:
            # Get all PDF links
            pdf_links = self.get_pdf_links()
            print(f"Found {len(pdf_links)} PDFs to download")
            
            # Create progress bar
            self.progress_bar = tqdm(total=len(pdf_links), desc="Downloading PDFs")
            
            # Create download tasks
            tasks = []
            for pdf_url, paper_id in pdf_links:
                task = self.download_pdf(pdf_url, paper_id)
                tasks.append(task)
            
            # Download PDFs concurrently with semaphore to limit concurrent downloads
            semaphore = asyncio.Semaphore(self.max_concurrent)
            async with semaphore:
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful downloads
            successful = sum(1 for r in results if r is True)
            print(f"\nDownloaded {successful} out of {len(pdf_links)} PDFs")
            
        finally:
            await self.close_session()
            if self.progress_bar:
                self.progress_bar.close()

async def main():
    # Configuration
    json_dir = "/home/joshua/Documents/GitHub/miccai_web_scraper/data/2024json"
    pdf_dir = "/home/joshua/Documents/GitHub/miccai_web_scraper/data/2024pdf"
    max_concurrent = 10  # Maximum number of concurrent downloads
    
    downloader = PDFDownloader(json_dir, pdf_dir, max_concurrent)
    await downloader.download_all()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())