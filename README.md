# noods-qobuz

CLI tool that scrapes [Noods Radio](https://noodsradio.com) show tracklists and creates playlists on [Qobuz](https://www.qobuz.com).

## Requirements

- Python 3.10+
- A Qobuz account (free tier works)

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your Qobuz credentials:

```
QOBUZ_EMAIL=your@email.com
QOBUZ_PASSWORD=yourpassword
```

## Usage

### Single episode

```bash
# By URL
python main.py --url "https://noodsradio.com/shows/spooky-toxin-19th-march-26"

# By slug
python main.py --slug spooky-toxin-19th-march-26
```

### Browse recent shows

```bash
# List recent shows
python main.py --list

# Interactively pick a show from the list
python main.py --pick
```

### All episodes for a resident

Creates a mega-playlist of unique tracks across every episode:

```bash
python main.py --url "https://noodsradio.com/residents/tell-me-i-m-dreaming" --all-episodes
```

### Add to an existing playlist

```bash
# Append to an existing playlist
python main.py --url "..." --add-to 12345678

# Prepend (new tracks go to the top)
python main.py --url "..." --add-to 12345678 --prepend
```

If adding tracks would exceed Qobuz's 2000-track playlist limit, the overflow is automatically split into a new playlist named after the original (e.g. `My Playlist (2)`).

### Other options

| Flag | Description |
|------|-------------|
| `--playlist-name NAME` | Custom playlist name (auto-generated if not set) |
| `--public` | Make the playlist public (private by default) |
| `--dry-run` | Search Qobuz and show results without creating anything |
| `--no-confirm` | Skip confirmation prompts |
| `--list-count N` | Number of shows to display with `--list` or `--pick` (default: 20) |
