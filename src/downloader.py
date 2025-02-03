import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from tqdm import tqdm

class TelegramDownloader:
    """
    TIMID (Telegram IMage & vIDeo downloader)
    A high-performance Telegram media downloader with concurrent download support.
    """
    
    def __init__(self):
        # Load configuration
        load_dotenv(os.path.join('config', '.env'))
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.channel_id = int(os.getenv('CHANNEL_ID'))
        
        # Initialize directories
        self.channel_dir = os.path.join('downloads', str(self.channel_id))
        self.video_dir = self.channel_dir
        self.image_dir = os.path.join(self.channel_dir, 'img')
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)

        # Initialize Telegram client
        self.client = TelegramClient(
            os.path.join('config', f'session_{self.channel_id}'),
            self.api_id,
            self.api_hash
        )
        
        # Progress management
        self.image_progress_file = os.path.join('config', f'image_progress_{self.channel_id}.json')
        self.video_progress_file = os.path.join('config', f'video_progress_{self.channel_id}.json')
        self.image_progress = self.load_progress(self.image_progress_file)
        self.video_progress = self.load_progress(self.video_progress_file)
        self.progress_bar = None
        self.semaphore = asyncio.Semaphore(4)  # Limit concurrent downloads
        self.retry_count = 3  # Maximum retry attempts

    def load_progress(self, progress_file):
        """Load download progress from file"""
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'last_message_id': 0, 'downloaded_files': []}

    def save_progress(self, progress_file, progress_data, message_id, file_id):
        """Save download progress to file"""
        progress_data['last_message_id'] = message_id
        if file_id not in progress_data['downloaded_files']:
            progress_data['downloaded_files'].append(file_id)
            if len(progress_data['downloaded_files']) > 1000:
                progress_data['downloaded_files'] = progress_data['downloaded_files'][-1000:]
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

    def log_error(self, error_msg):
        """Log error messages to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(os.path.join('logs', 'error.log'), 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {error_msg}\n")
        print(f"❌ {error_msg}")

    def log_info(self, message):
        """Log info messages to console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] ℹ️ {message}")

    def update_progress(self, current, total):
        """Update progress bar during download"""
        if self.progress_bar:
            self.progress_bar.update(current - self.progress_bar.n)

    async def download_image(self, message):
        """Download image from Telegram message"""
        if not message.photo:
            return

        file_id = str(message.photo.id)
        if file_id in self.image_progress['downloaded_files']:
            self.log_info(f"Image already downloaded: {file_id}")
            return

        filename = f"{message.date.strftime('%Y%m%d_%H%M%S')}_{message.id}.jpg"
        filepath = os.path.join(self.image_dir, filename)

        # Check if file already exists
        if os.path.exists(filepath):
            self.log_info(f"File already exists: {filename}")
            return

        try:
            async with self.semaphore:
                with tqdm(
                    total=max(message.photo.sizes[-1].sizes),
                    unit='B',
                    unit_scale=True,
                    desc=filename
                ) as self.progress_bar:
                    await message.download_media(
                        file=filepath,
                        progress_callback=self.update_progress
                    )
                self.save_progress(self.image_progress_file, self.image_progress, message.id, file_id)
                self.log_info(f"✅ Image download completed: {filename}")

        except FloodWaitError as e:
            wait_time = e.seconds + 5
            self.log_error(f"FloodWait occurred: waiting {wait_time}s (file: {filename})")
            await asyncio.sleep(wait_time)
        except Exception as e:
            self.log_error(f"Image download failed ({filename}): {str(e)}")

    async def download_video_chunk(self, message, chunk_number, total_chunks):
        """Download a specific chunk of video using iter_download"""
        try:
            chunk_filename = f"chunk_{message.id}_{chunk_number}_{total_chunks}.part"
            temp_dir = os.path.join(self.video_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            chunk_path = os.path.join(temp_dir, chunk_filename)
            
            total_size = message.video.size
            chunk_size = total_size // total_chunks
            
            # Log file size information
            self.log_info(f"Total file size: {total_size:,} bytes ({total_size/1024/1024:.2f}MB)")
            self.log_info(f"Chunk size: {chunk_size:,} bytes ({chunk_size/1024/1024:.2f}MB)")
            
            with tqdm(
                total=chunk_size,
                unit='B',
                unit_scale=True,
                desc=f"Chunk {chunk_number + 1}/{total_chunks}"
            ) as progress:
                with open(chunk_path, 'wb') as f:
                    async for chunk in message.client.iter_download(
                        message.media
                    ):
                        f.write(chunk)
                        progress.update(len(chunk))
                        
            return chunk_path
        except Exception as e:
            self.log_error(f"Chunk {chunk_number + 1} download failed: {str(e)}")
            return None

    async def download_video(self, message):        
        if not message.video:
            return

        file_id = str(message.video.id)
        if file_id in self.video_progress['downloaded_files']:
            self.log_info(f"Video already downloaded: {file_id}")
            return

        filename = f"{message.date.strftime('%Y%m%d_%H%M%S')}_{message.id}.mp4"
        filepath = os.path.join(self.video_dir, filename)

        if os.path.exists(filepath):
            self.log_info(f"File already exists: {filename}")
            return

        self.log_info(f"Total file size: ({message.video.size/1024/1024:.2f}MB)")
        try:
            with tqdm(
                total=message.video.size,
                unit='B',
                unit_scale=True,
                desc=filename
            ) as progress:
                await message.download_media(
                    file=filepath,
                    progress_callback=lambda c, t: progress.update(c - progress.n)
                )

            self.save_progress(self.video_progress_file, self.video_progress, message.id, file_id)
            self.log_info(f"✅ Video download completed: {filename}")

        except FloodWaitError as e:
            wait_time = e.seconds + 5
            self.log_error(f"FloodWait occurred: waiting {wait_time}s (file: {filename})")
            await asyncio.sleep(wait_time)
        except Exception as e:
            self.log_error(f"Video download failed ({filename}): {str(e)}")


    async def start(self):
        await self.client.start()
        self.log_info("Connected to Telegram")
        
        try:
            channel = await self.client.get_entity(self.channel_id)
            if not channel:
                self.log_error("Channel not found")
                return

            self.log_info(f"Connected to channel {self.channel_id}")

            # Total amount of messages
            total_messages = await self.client.get_messages(
                channel,
                limit=1,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                search=None,
                filter=None
            )
            
            if not total_messages:
                self.log_error("No messages")
                return
                
            total_count = total_messages[0].id
            self.log_info(f"Total messages: {total_count}")
            
            # Image downloads (10 concurrent)
            self.log_info("\n📸 Starting image downloads...")
            active_image_downloads = set()
            
            async for message in self.client.iter_messages(
                channel,
                min_id=self.image_progress['last_message_id'],
                reverse=True
            ):
                if message.photo:
                    self.log_info(f"Image Downloading: {message.id} / {total_count}")
                    if len(active_image_downloads) >= 10:
                        done, pending = await asyncio.wait(
                            active_image_downloads, 
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        active_image_downloads = pending
                    
                    task = asyncio.create_task(self.download_image(message))
                    active_image_downloads.add(task)
            
            if active_image_downloads:
                await asyncio.wait(active_image_downloads)
            
            # Video downloads (4 concurrent)
            self.log_info("\n🎥 Starting video downloads...")
            active_video_downloads = set()
            
            async for message in self.client.iter_messages(
                channel,
                min_id=self.video_progress['last_message_id'],
                reverse=True
            ):
                if message.video:
                    self.log_info(f"Viedo Downloading: {message.id} / {total_count}")
                    if len(active_video_downloads) >= 4:
                        done, pending = await asyncio.wait(
                            active_video_downloads, 
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        active_video_downloads = pending
                    
                    task = asyncio.create_task(self.download_video(message))
                    active_video_downloads.add(task)
            
            if active_video_downloads:
                await asyncio.wait(active_video_downloads)

        except Exception as e:
            self.log_error(f"Global error: {str(e)}")
        finally:
            await self.client.disconnect()
            self.log_info("✅ All downloads completed")


    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.disconnect()


async def main():
    """Main execution function"""
    downloader = TelegramDownloader()
    await downloader.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
