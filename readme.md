# TIMID (Telegram IMage & vIDeo downloader)

TIMID is a high-performance Telegram media downloader that supports concurrent downloads of images and videos from Telegram channels.

## Features

- Separate download tracking for images and videos
- Concurrent download support
- Auto-resume capability
- Progress tracking per channel
- Premium account optimization
- Separate session management per channel

## Requirements

- Python 3.7+
- Telegram API credentials
- (Optional) Telegram Premium account for better performance

## Installation

1. Clone the repository
```

git clone https://github.com/yourusername/TIMID.git
cd TIMID

```

2. Install dependencies
```

pip install -r requirements.txt

```

3. Configure environment variables
```

cp config/.env.example config/.env

# Edit config/.env with your credentials

```


## Configuration

Create `config/.env` file with your Telegram API credentials:

1. Get your API credentials from https://my.telegram.org/apps
2. Get channel ID from Telegram Web URL (e.g., https://web.telegram.org/k/#-1001234567890 → CHANNEL_ID=-1001234567890)
3. Add to your .env file:

```

API_ID=your_api_id
API_HASH=your_api_hash
CHANNEL_ID=-100xxxxxxxxx

```

## Usage

```

python src/downloader.py

```

## Project Structure

```

TIMID/
├── src/ # Source code
├── config/ # Configuration files
├── downloads/ # Downloaded media files
└── logs/ # Error logs

```

## Notes

- For optimal performance, run up to 3 instances with different channel IDs
- Each channel uses its own session file to prevent database locks
- Progress is tracked separately for images and videos

## License

MIT License - see LICENSE file for details
```
