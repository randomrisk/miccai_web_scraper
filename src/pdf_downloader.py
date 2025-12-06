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
        self.skipped_count = 0
        
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

    def is_pdf_already_downloaded(self, filename):
        """Check if PDF file already exists"""
        output_path = os.path.join(self.pdf_dir, filename)
        exists = os.path.exists(output_path)
        
        # Also check if file size is reasonable (not empty or corrupted)
        if exists:
            file_size = os.path.getsize(output_path)
            if file_size < 1024:  # Less than 1KB, likely corrupted
                logging.warning(f"File {filename} exists but is too small ({file_size} bytes), will re-download")
                return False
        
        return exists

    async def download_pdf(self, pdf_url, filename):
        """Download a single PDF file"""
        output_path = os.path.join(self.pdf_dir, filename)
        
        # Skip if file already exists and is valid
        if self.is_pdf_already_downloaded(filename):
            logging.info(f"Skipping {filename} - already exists")
            self.skipped_count += 1
            self.progress_bar.update(1)
            return "skipped"

        try:
            async with self.session.get(pdf_url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(output_path, 'wb') as f:
                        f.write(content)
                    logging.info(f"Successfully downloaded {filename}")
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
            print(f"Found {len(pdf_links)} PDFs to process")
            
            # Check how many are already downloaded
            already_downloaded = sum(1 for _, filename in pdf_links if self.is_pdf_already_downloaded(filename))
            print(f"Already downloaded: {already_downloaded} PDFs")
            print(f"Need to download: {len(pdf_links) - already_downloaded} PDFs")
            
            # Create progress bar
            self.progress_bar = tqdm(total=len(pdf_links), desc="Processing PDFs")
            
            # Create download tasks
            tasks = []
            for pdf_url, paper_id in pdf_links:
                task = self.download_pdf(pdf_url, paper_id)
                tasks.append(task)
            
            # Download PDFs concurrently with semaphore to limit concurrent downloads
            semaphore = asyncio.Semaphore(self.max_concurrent)
            async with semaphore:
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            successful = sum(1 for r in results if r is True)
            skipped = sum(1 for r in results if r == "skipped")
            failed = len(results) - successful - skipped
            
            print(f"\nResults:")
            print(f"  Successfully downloaded: {successful} PDFs")
            print(f"  Skipped (already exists): {skipped} PDFs") 
            print(f"  Failed: {failed} PDFs")
            print(f"  Total processed: {len(pdf_links)} PDFs")
            
        finally:
            await self.close_session()
            if self.progress_bar:
                self.progress_bar.close()

async def main():
    # Configuration
    json_dir = "/Users/joshua_liu/Documents/github_repo/miccai_web_scraper/data/2025json"
    pdf_dir = "/Users/joshua_liu/Documents/github_repo/miccai_web_scraper/data/2025pdf"
    max_concurrent = 10  # Maximum number of concurrent downloads
    
    downloader = PDFDownloader(json_dir, pdf_dir, max_concurrent)
    await downloader.download_all()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())