#!/usr/bin/env python3
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.validation import run_all_validations, print_validation_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    print("Running validation checks on output files...\n")
    
    results = run_all_validations()
    all_passed = print_validation_report(results)
    
    sys.exit(0 if all_passed else 1)
