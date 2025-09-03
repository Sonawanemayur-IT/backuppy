#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

def create_parser():
    # Main description with ASCII art banner for visual appeal
    description = """
╔═══════════════════════════════════════════════════════════════════╗
║                    FAST PROJECT BACKUP TOOL                      ║
╚═══════════════════════════════════════════════════════════════════╝

Create lightning-fast ZIP backups of your projects with real-time progress.
Optimized for multi-GB codebases using no-compression storage and ZIP64 support.

Perfect for developers who need quick, reliable backups before deployments,
system updates, or major code changes.
    """

    # Epilog with examples and additional info
    epilog = """
EXAMPLES:
  Basic GUI mode:
    %(prog)s

  Fast backup (no compression):
    %(prog)s --source "/path/to/project" --dest "/backup/drive"

  Web development project:
    %(prog)s --source "/home/user/webapp" --dest "/backups" \\
             --exclude ".git,node_modules,dist,.next,coverage"

  Python project with light compression:
    %(prog)s --source "/home/user/myapp" --dest "/backups" \\
             --compression deflate --level 1 \\
             --exclude ".git,venv,__pycache__,.pytest_cache"

  Force GUI with arguments present:
    %(prog)s --source "/path" --dest "/backups" --gui

PERFORMANCE TIPS:
  • Use --compression store (default) for maximum speed
  • Exclude heavy folders: node_modules, .git, venv, build
  • Backup to fast storage (SSD/NVMe) when possible
  • Typical speed: 50-200+ MB/s depending on storage

SUPPORTED FORMATS:
  • ZIP (default) - Universal compatibility
  • ZIP64 enabled - Supports files > 4GB and 65k+ entries

DEFAULT EXCLUDES:
  .git, node_modules, venv, __pycache__, dist, build

For more info: https://github.com/yourusername/fast-project-backup
Report issues: https://github.com/yourusername/fast-project-backup/issues

Thanks for using %(prog)s! 🚀
    """

    parser = argparse.ArgumentParser(
        prog='backup_app.py',
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,  # Preserves formatting
        add_help=True
    )

    # Positional arguments (none for this tool)
    
    # Optional arguments with detailed help
    parser.add_argument(
        '--source', '-s',
        type=str,
        metavar='PATH',
        help='Source project directory to backup (required for CLI mode)'
    )

    parser.add_argument(
        '--dest', '-d', 
        type=str,
        metavar='PATH',
        help='Destination directory for backup archive (required for CLI mode)'
    )

    parser.add_argument(
        '--compression', '-c',
        choices=['store', 'deflate'],
        default='store',
        help='Compression method: "store" = no compression (fastest), "deflate" = compress (default: %(default)s)'
    )

    parser.add_argument(
        '--level', '-l',
        type=int,
        choices=range(1, 10),
        metavar='1-9',
        help='Deflate compression level 1-9 (only with --compression deflate). 1=fastest, 9=smallest (default: 1)'
    )

    parser.add_argument(
        '--exclude', '-e',
        type=str,
        default='.git,node_modules,venv,__pycache__,dist,build',
        metavar='FOLDERS',
        help='Comma-separated folder names to exclude at any depth (default: %(default)s)'
    )

    parser.add_argument(
        '--gui', '-g',
        action='store_true',
        help='Force GUI mode even if --source and --dest are provided'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version='%(prog)s 1.0 - Fast Project Backup Tool'
    )

    return parser

def main():
    parser = create_parser()
    
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        try:
            import tkinter
            # GUI mode if tkinter available and no args
            from backup_gui import run_gui
            run_gui()
        except ImportError:
            parser.print_help()
            sys.exit(1)
    else:
        args = parser.parse_args()
        # Handle CLI mode logic here
        print(f"Source: {args.source}")
        print(f"Dest: {args.dest}")
        # ... rest of CLI logic

if __name__ == "__main__":
    main()
