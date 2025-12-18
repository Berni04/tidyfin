"""TidyFin Web Server - Flask-based web interface for media organization."""

import json
import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tidyfin.scanner import FileScanner
from tidyfin.organizer import FileOrganizer
from tidyfin.tmdb_client import TMDBClient
from tidyfin.models import MediaType, Confidence


app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Global state (in production, use proper session management)
app_state = {
    'tmdb_client': None,
    'config': {},
    'scanned_files': [],
    'previews': [],
    'files_to_organize': []  # Files filtered from preview step
}


def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent / 'config.json'
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """Save configuration to config.json."""
    config_path = Path(__file__).parent.parent / 'config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def init_tmdb():
    """Initialize TMDB client from config."""
    config = load_config()
    app_state['config'] = config
    api_key = config.get('tmdb_api_key', '')
    if api_key:
        app_state['tmdb_client'] = TMDBClient(api_key)
        return True
    return False


# Initialize on startup
init_tmdb()


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration."""
    if request.method == 'GET':
        config = load_config()
        # Don't expose full API key
        if config.get('tmdb_api_key'):
            config['tmdb_api_key_set'] = True
            config['tmdb_api_key'] = '***' + config['tmdb_api_key'][-4:] if len(config['tmdb_api_key']) > 4 else '****'
        return jsonify(config)
    
    elif request.method == 'POST':
        data = request.json
        config = load_config()
        
        # Update API key if provided
        if 'tmdb_api_key' in data and not data['tmdb_api_key'].startswith('***'):
            config['tmdb_api_key'] = data['tmdb_api_key']
        
        # Update other settings
        for key in ['default_movies_dir', 'default_shows_dir', 'default_review_dir']:
            if key in data:
                config[key] = data[key]
        
        save_config(config)
        init_tmdb()
        
        return jsonify({'success': True, 'message': 'Configuration saved'})


@app.route('/api/test-tmdb', methods=['POST'])
def test_tmdb():
    """Test TMDB API connection."""
    if app_state['tmdb_client']:
        if app_state['tmdb_client'].test_connection():
            return jsonify({'success': True, 'message': 'TMDB API connected successfully'})
        else:
            return jsonify({'success': False, 'message': 'TMDB API connection failed'})
    return jsonify({'success': False, 'message': 'No API key configured'})


@app.route('/api/scan', methods=['POST'])
def scan_directory():
    """Scan a directory for media files."""
    data = request.json
    source_dir = data.get('source_dir', '')
    
    if not source_dir:
        return jsonify({'error': 'Source directory required'}), 400
    
    source_path = Path(source_dir)
    if not source_path.exists():
        return jsonify({'error': f'Directory not found: {source_dir}'}), 404
    
    if not source_path.is_dir():
        return jsonify({'error': f'Not a directory: {source_dir}'}), 400
    
    try:
        scanner = FileScanner()
        files = scanner.scan(source_path, recursive=True)
        app_state['scanned_files'] = files
        
        # Convert to JSON-serializable format
        results = []
        for f in files:
            results.append({
                'filename': f.filename,
                'path': str(f.source_path),
                'extension': f.extension,
                'parsed_title': f.parsed_info.title if f.parsed_info else None,
                'parsed_year': f.parsed_info.year if f.parsed_info else None,
                'parsed_season': f.parsed_info.season if f.parsed_info else None,
                'parsed_episode': f.parsed_info.episode if f.parsed_info else None,
                'media_type': f.parsed_info.media_type.value if f.parsed_info else 'unknown',
                'confidence': f.confidence.value,
                'confidence_score': f.confidence_score
            })
        
        return jsonify({
            'success': True,
            'count': len(files),
            'files': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview', methods=['POST'])
def preview_organization():
    """Preview organization without moving files."""
    data = request.json
    movies_dir = data.get('movies_dir', '')
    shows_dir = data.get('shows_dir', '')
    review_dir = data.get('review_dir', '')
    selected_indices = data.get('selected_indices', None)  # Optional: list of file indices
    
    if not movies_dir or not shows_dir:
        return jsonify({'error': 'Movies and Shows directories required'}), 400
    
    if not app_state['scanned_files']:
        return jsonify({'error': 'No files scanned. Run scan first.'}), 400
    
    # Filter files by selected indices if provided
    files_to_process = app_state['scanned_files']
    if selected_indices and len(selected_indices) > 0:
        files_to_process = [app_state['scanned_files'][i] for i in selected_indices 
                           if i < len(app_state['scanned_files'])]
    
    try:
        organizer = FileOrganizer(
            movies_dir=Path(movies_dir),
            shows_dir=Path(shows_dir),
            review_dir=Path(review_dir) if review_dir else None,
            tmdb_client=app_state['tmdb_client'],
            dry_run=True
        )
        
        previews = organizer.preview(files_to_process)
        app_state['previews'] = previews
        app_state['files_to_organize'] = files_to_process  # Store for execute
        
        # Convert to JSON-serializable format
        results = []
        for media_file, dest_path in previews:
            match_info = None
            if media_file.tmdb_match:
                match = media_file.tmdb_match
                poster_url = None
                if match.poster_path:
                    poster_url = f"https://image.tmdb.org/t/p/w185{match.poster_path}"
                match_info = {
                    'title': match.title,
                    'year': match.year,
                    'tmdb_id': match.tmdb_id,
                    'season': match.season_number,
                    'episode': match.episode_number,
                    'episode_title': match.episode_title,
                    'poster_url': poster_url
                }
            
            results.append({
                'filename': media_file.filename,
                'source_path': str(media_file.source_path),
                'destination_path': str(dest_path) if dest_path else None,
                'media_type': media_file.get_media_type().value,
                'confidence': media_file.confidence.value,
                'confidence_score': media_file.confidence_score,
                'tmdb_match': match_info,
                'action': 'move' if dest_path and 'review' not in str(dest_path).lower() else 'manual_review'
            })
        
        # Summary stats
        movies = sum(1 for r in results if r['media_type'] == 'movie' and r['action'] == 'move')
        shows = sum(1 for r in results if r['media_type'] == 'tv_show' and r['action'] == 'move')
        review = sum(1 for r in results if r['action'] == 'manual_review')
        
        return jsonify({
            'success': True,
            'previews': results,
            'summary': {
                'total': len(results),
                'movies': movies,
                'shows': shows,
                'manual_review': review
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/execute', methods=['POST'])
def execute_organization():
    """Execute the organization (move files)."""
    data = request.json
    movies_dir = data.get('movies_dir', '')
    shows_dir = data.get('shows_dir', '')
    review_dir = data.get('review_dir', '')
    
    if not movies_dir or not shows_dir:
        return jsonify({'error': 'Movies and Shows directories required'}), 400
    
    # Use files from preview step (must run preview first)
    files_to_organize = app_state.get('files_to_organize', [])
    if not files_to_organize:
        return jsonify({'error': 'No files to organize. Run preview first.'}), 400
    
    try:
        organizer = FileOrganizer(
            movies_dir=Path(movies_dir),
            shows_dir=Path(shows_dir),
            review_dir=Path(review_dir) if review_dir else None,
            tmdb_client=app_state['tmdb_client'],
            dry_run=False
        )
        
        summary = organizer.organize(files_to_organize)
        
        # Clear state after successful organization
        app_state['scanned_files'] = []
        app_state['previews'] = []
        app_state['files_to_organize'] = []
        
        # Convert results
        results = []
        for r in summary.results:
            results.append({
                'filename': r.media_file.filename,
                'source_path': str(r.source_path),
                'destination_path': str(r.destination_path) if r.destination_path else None,
                'action': r.action,
                'success': r.success,
                'error': r.error_message
            })
        
        return jsonify({
            'success': True,
            'summary': {
                'total': summary.total_files,
                'movies_organized': summary.movies_organized,
                'shows_organized': summary.shows_organized,
                'manual_review': summary.manual_review,
                'skipped': summary.skipped,
                'errors': summary.errors
            },
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/browse', methods=['POST'])
def browse_directory():
    """Browse directory structure for folder picker."""
    data = request.json
    path = data.get('path', '')
    
    # Default to user's home or common locations
    if not path:
        if os.name == 'nt':  # Windows
            path = os.path.expanduser('~')
        else:
            path = '/'
    
    try:
        p = Path(path)
        if not p.exists():
            return jsonify({'error': f'Path not found: {path}'}), 404
        
        if not p.is_dir():
            p = p.parent
        
        # List directories only
        dirs = []
        try:
            for item in sorted(p.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    dirs.append({
                        'name': item.name,
                        'path': str(item)
                    })
        except PermissionError:
            pass
        
        # Get parent
        parent = str(p.parent) if p.parent != p else None
        
        return jsonify({
            'current': str(p),
            'parent': parent,
            'directories': dirs
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_server(host='127.0.0.1', port=8080, debug=False):
    """Run the Flask development server."""
    print(f"\n🎬 TidyFin Web UI starting at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='TidyFin Web Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, debug=args.debug)
