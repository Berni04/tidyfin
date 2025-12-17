# TidyFin 🎬

**Automatically organize your media files for Jellyfin servers.**

TidyFin scans your media directories, identifies movies and TV shows using TMDB, and organizes them into Jellyfin's preferred folder structure.

## Features

- 🔍 **Smart Identification** - Uses TMDB API for accurate movie/show detection
- 📂 **Jellyfin-Compatible** - Organizes files into proper naming convention
- 👁️ **Preview Mode** - See changes before they happen
- 🖥️ **Dual Interface** - CLI for automation, Web UI for visual workflow
- ⚠️ **Manual Review** - Low-confidence files are separated for review

## Installation

```bash
# Clone or download to your preferred location
cd tidyfin

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Get a free TMDB API key from [themoviedb.org](https://www.themoviedb.org/settings/api)
2. Add your key to `config.json`:

```json
{
  "tmdb_api_key": "your_api_key_here"
}
```

## Usage

### CLI Mode

```bash
# Preview changes (dry run)
python cli.py --source "D:/Downloads" --movies "D:/Jellyfin/Movies" --shows "D:/Jellyfin/Shows" --dry-run

# Execute organization
python cli.py --source "D:/Downloads" --movies "D:/Jellyfin/Movies" --shows "D:/Jellyfin/Shows"

# With manual review folder
python cli.py -s "D:/Downloads" -m "D:/Movies" -t "D:/Shows" -r "D:/Review"
```

**CLI Options:**
| Option | Description |
|--------|-------------|
| `-s, --source` | Source directory with media files |
| `-m, --movies` | Destination for movies |
| `-t, --shows` | Destination for TV shows |
| `-r, --review` | Folder for files needing manual review |
| `--dry-run` | Preview without moving files |
| `--api-key` | TMDB API key (or set in config.json) |
| `--no-tmdb` | Skip TMDB lookup, use filename parsing only |
| `-q, --quiet` | Minimal output |

### Web UI Mode

```bash
# Start the web server
python web/server.py

# Opens at http://localhost:8080
```

The Web UI provides a step-by-step wizard:
1. **Scan** - Select source folder and find media files
2. **Configure** - Set destination folders for Movies/Shows
3. **Preview** - Review proposed organization
4. **Execute** - Apply changes

## Folder Structure

TidyFin organizes files following Jellyfin's recommended structure:

**Movies:**
```
/Movies
  /Movie Name (Year)
    Movie Name (Year).mkv
```

**TV Shows:**
```
/Shows
  /Show Name
    /Season 01
      Show Name - S01E01 - Episode Title.mkv
      Show Name - S01E02 - Episode Title.mkv
```

## Supported Formats

`.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.ts`, `.mpg`, `.mpeg`

## How It Works

1. **Scan** - Finds all video files in source directory
2. **Parse** - Extracts title, year, season/episode from filename
3. **Identify** - Queries TMDB to verify and get accurate metadata
4. **Score** - Assigns confidence based on match quality
5. **Organize** - Moves high-confidence files, reviews low-confidence

## Confidence Levels

| Level | Score | Action |
|-------|-------|--------|
| 🟢 High | 80-100% | Auto-organize |
| 🟡 Medium | 50-79% | Auto-organize with match info |
| 🔴 Low | 0-49% | Sent to manual review |

## License

MIT
