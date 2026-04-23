"""
OASIS Prefill startup script.
Starts the FastAPI server with proper configuration.
"""

import os
import sys
import logging
import uvicorn
from pathlib import Path

# Add parent directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from oasis_prefill.app import app
from oasis_prefill.config import CONFIG
from common.logging_config import setup_logging


def setup_environment():
    """Setup environment variables and logging."""
    # Load .env if exists
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    # Setup logging
    setup_logging(
        __name__,
        log_file=CONFIG["log_file"],
        level=CONFIG["log_level"]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Environment setup complete")
    
    return logger


def print_startup_info():
    """Print startup information."""
    print("\n" + "="*70)
    print("OASIS Prefill API Starting Up")
    print("="*70)
    print(f"Host: {CONFIG['api_host']}")
    print(f"Port: {CONFIG['api_port']}")
    print(f"Form Version: {CONFIG['form_version']}")
    print(f"Enable E2: {CONFIG['enable_e2']}")
    print(f"Debug Mode: {CONFIG['debug']}")
    print(f"Log Level: {CONFIG['log_level']}")
    print(f"Database: {'Enabled' if CONFIG['use_database'] else 'Disabled'}")
    print(f"AWS: {'Enabled' if CONFIG['use_aws'] else 'Disabled'}")
    print("-"*70)
    print(f"API Documentation: http://{CONFIG['api_host']}:{CONFIG['api_port']}/docs")
    print(f"API ReDoc: http://{CONFIG['api_host']}:{CONFIG['api_port']}/redoc")
    print("="*70 + "\n")


def main():
    """Main startup function."""
    logger = setup_environment()
    
    logger.info("Starting OASIS Prefill API")
    logger.info(f"Configuration loaded: {CONFIG}")
    
    print_startup_info()
    
    # Start uvicorn server
    try:
        uvicorn.run(
            app,
            host=CONFIG["api_host"],
            port=CONFIG["api_port"],
            log_level=CONFIG["log_level"].lower(),
            reload=CONFIG["debug"],
            reload_dirs=[str(Path(__file__).parent)],
        )
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
