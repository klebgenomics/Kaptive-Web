import argparse

from kaptive_web._version import __version__


def main():
    """Entry point for the command line."""

    # Define args ------------------------------------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description='Graph-aware contextual annotation of targeted genomic features',
        usage="%(prog)s -i genome.gfa -d targets.fasta [options]", add_help=False, prog=__package__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    uvicorn_args = parser.add_argument_group('🛜', 'uvicorn arguments')
    uvicorn_args.add_argument('--host', default='127.0.0.1', metavar='')
    uvicorn_args.add_argument('--port', type=int, default=8000, metavar='')
    uvicorn_args.add_argument('--reload', action='store_true', default=False, metavar='')

    opts = parser.add_argument_group("🛠️", "Other options")
    opts.add_argument("-q", "--quiet", action="store_true", help="Suppress console logging output")
    opts.add_argument("-v", "--version", action="version", version=__version__, help="Show version number and exit")
    opts.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    # Parse args -------------------------------------------------------------------------------------------------------
    args = parser.parse_args()

    # Run app ===-------------------------------------------------------------------------------------------------------
    import uvicorn

    from kaptive_web import app

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)