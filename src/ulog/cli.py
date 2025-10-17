"""Command-line interface for ULog Normalizer."""

import json
import sys
from typing import Dict, Any, Optional

import click

from .router import DomainRouter
from .normalizer import Normalizer
from .provenance import ProvenanceTracker


@click.group()
def cli():
    """ULog Normalizer CLI - Transform raw logs into standardized JSON events."""
    pass


@cli.command()
@click.option(
    '--domain',
    type=click.Choice(['core_api', 'llm', 'agentic', 'cv']),
    help='Target domain (bypasses auto-detection)'
)
@click.option(
    '--format',
    type=click.Choice(['jsonl', 'json']),
    default='jsonl',
    help='Output format'
)
def parse(domain, format):
    """Parse raw logs from stdin to normalized JSON on stdout.
    
    Reads raw log lines from stdin, parses them using domain-specific parsers,
    normalizes the extracted fields, and outputs JSONL (one JSON object per line)
    to stdout.
    
    Examples:
        cat logs.txt | ulog parse --domain core_api > normalized.jsonl
        cat logs.txt | ulog parse > normalized.jsonl
    """
    # Initialize components
    router = DomainRouter()
    normalizer = Normalizer()
    provenance_tracker = ProvenanceTracker()
    
    # Track multi-line logs by timestamp
    current_timestamp: Optional[str] = None
    current_messages: list[str] = []
    
    def process_log_entry(timestamp: str, message: str):
        """Process a complete log entry (potentially multi-line)."""
        try:
            # Route to appropriate parser
            parser = router.route(message, domain_hint=domain)
            
            # Parse the message
            parse_result = parser.parse(message)
            
            if parse_result.success:
                # Normalize extracted fields
                normalized_data = normalizer.normalize(parse_result.data, parser.parser_name.replace('_parser', ''))
                
                # Add provenance metadata
                enriched_data = provenance_tracker.enrich(
                    normalized_data,
                    message,
                    parse_result,
                    parser
                )
                
                # Add timestamp to output
                enriched_data['timestamp'] = timestamp
                
                # Output as JSONL
                output_json(enriched_data, format)
            else:
                # Handle parse failure
                failure_output = {
                    'timestamp': timestamp,
                    'unparsed_reason': parse_result.error or 'no_pattern_match',
                    'meta': {
                        'raw_message': message,
                        'parse': {
                            'parser_name': parser.parser_name,
                            'parser_version': parser.parser_version,
                            'ok': False,
                            'error': parse_result.error or 'no_pattern_match'
                        }
                    }
                }
                output_json(failure_output, format)
                
        except Exception as e:
            # Handle unexpected errors
            error_output = {
                'timestamp': timestamp,
                'unparsed_reason': 'processing_error',
                'meta': {
                    'raw_message': message,
                    'parse': {
                        'ok': False,
                        'error': str(e)
                    }
                }
            }
            output_json(error_output, format)
    
    try:
        # Read JSONL from stdin
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse JSONL input
                log_entry = json.loads(line)
                timestamp = log_entry.get('@timestamp')
                message = log_entry.get('@message')
                
                if not timestamp or message is None:
                    # Skip malformed entries
                    continue
                
                # Check if this is a continuation of the previous log (multi-line)
                if current_timestamp == timestamp:
                    # Same timestamp = continuation line
                    current_messages.append(message)
                else:
                    # Different timestamp = new log entry
                    # Process the previous accumulated log if any
                    if current_timestamp and current_messages:
                        joined_message = '\n'.join(current_messages)
                        process_log_entry(current_timestamp, joined_message)
                    
                    # Start new log entry
                    current_timestamp = timestamp
                    current_messages = [message]
                    
            except json.JSONDecodeError:
                # Skip invalid JSON lines
                continue
        
        # Process the last accumulated log entry
        if current_timestamp and current_messages:
            joined_message = '\n'.join(current_messages)
            process_log_entry(current_timestamp, joined_message)
            
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def output_json(data: Dict[str, Any], output_format: str):
    """Output data in the specified format.
    
    Args:
        data: Dictionary to output
        output_format: 'jsonl' or 'json'
    """
    if output_format == 'jsonl':
        # Output as single-line JSON
        print(json.dumps(data, ensure_ascii=False))
    else:
        # Output as pretty-printed JSON
        print(json.dumps(data, indent=2, ensure_ascii=False))


@cli.command()
@click.option(
    '--input',
    type=click.File('r'),
    help='Input file (default: stdin)'
)
@click.option(
    '--format',
    type=click.Choice(['table', 'json']),
    default='table',
    help='Output format'
)
@click.option(
    '--threshold',
    type=str,
    help='Thresholds: llm=95,agentic=95,cv=80,core_api=70'
)
def stats(input, format, threshold):
    """Generate parsing statistics and validate against thresholds.
    
    Reads logs from stdin or a file, attempts to parse each log,
    and generates statistics including parse rates per domain and
    top unparsed reasons.
    
    Default thresholds (if --threshold not provided):
    - LLM: 95%
    - Agentic: 95%
    - CV: 80%
    - Core/API: 70%
    
    Exit codes:
    - 0: All domains meet thresholds
    - 1: One or more domains fail to meet thresholds
    
    Examples:
        cat logs.txt | ulog stats
        ulog stats --input logs.txt --threshold llm=95,agentic=95,cv=80,core_api=70
        cat logs.txt | ulog stats --format json
    """
    from collections import defaultdict, Counter
    
    # Default thresholds
    default_thresholds = {
        'llm': 95.0,
        'agentic': 95.0,
        'cv': 80.0,
        'core_api': 70.0,
    }
    
    # Parse custom thresholds if provided
    thresholds = default_thresholds.copy()
    if threshold:
        try:
            for pair in threshold.split(','):
                domain, value = pair.split('=')
                thresholds[domain.strip()] = float(value.strip())
        except (ValueError, KeyError) as e:
            click.echo(f"Error parsing thresholds: {e}", err=True)
            sys.exit(1)
    
    # Initialize components
    router = DomainRouter()
    
    # Statistics tracking per domain
    domain_stats = {
        'core_api': {'total': 0, 'parsed': 0, 'failed': 0, 'unparsed_reasons': Counter()},
        'llm': {'total': 0, 'parsed': 0, 'failed': 0, 'unparsed_reasons': Counter()},
        'agentic': {'total': 0, 'parsed': 0, 'failed': 0, 'unparsed_reasons': Counter()},
        'cv': {'total': 0, 'parsed': 0, 'failed': 0, 'unparsed_reasons': Counter()},
    }
    
    # Track multi-line logs by timestamp
    current_timestamp: Optional[str] = None
    current_messages: list[str] = []
    
    def process_log_entry(message: str):
        """Process a complete log entry and update statistics."""
        # Detect domain
        detected_domain = router.detect_domain(message)
        if not detected_domain:
            detected_domain = 'core_api'  # Default fallback
        
        # Get appropriate parser
        parser = router.route(message, domain_hint=detected_domain)
        
        # Update total count
        domain_stats[detected_domain]['total'] += 1
        
        # Attempt to parse
        parse_result = parser.parse(message)
        
        if parse_result.success:
            domain_stats[detected_domain]['parsed'] += 1
        else:
            domain_stats[detected_domain]['failed'] += 1
            reason = parse_result.unparsed_reason or parse_result.error or 'no_pattern_match'
            domain_stats[detected_domain]['unparsed_reasons'][reason] += 1
    
    # Read logs from input source
    input_source = input if input else sys.stdin
    
    try:
        for line in input_source:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse JSONL input
                log_entry = json.loads(line)
                timestamp = log_entry.get('@timestamp')
                message = log_entry.get('@message')
                
                if not timestamp or message is None:
                    continue
                
                # Check if this is a continuation of the previous log (multi-line)
                if current_timestamp == timestamp:
                    current_messages.append(message)
                else:
                    # Process the previous accumulated log if any
                    if current_timestamp and current_messages:
                        joined_message = '\n'.join(current_messages)
                        process_log_entry(joined_message)
                    
                    # Start new log entry
                    current_timestamp = timestamp
                    current_messages = [message]
                    
            except json.JSONDecodeError:
                continue
        
        # Process the last accumulated log entry
        if current_timestamp and current_messages:
            joined_message = '\n'.join(current_messages)
            process_log_entry(joined_message)
    
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error reading logs: {e}", err=True)
        sys.exit(1)
    
    # Calculate parse rates and prepare output
    results = {}
    overall_total = 0
    overall_parsed = 0
    all_thresholds_met = True
    
    for domain, stats in domain_stats.items():
        total = stats['total']
        parsed = stats['parsed']
        failed = stats['failed']
        
        overall_total += total
        overall_parsed += parsed
        
        parse_rate = (parsed / total * 100) if total > 0 else 0.0
        
        # Get top 3 unparsed reasons
        top_errors = stats['unparsed_reasons'].most_common(3)
        
        # Check threshold
        threshold_met = parse_rate >= thresholds[domain] if total > 0 else True
        if not threshold_met:
            all_thresholds_met = False
        
        results[domain] = {
            'total': total,
            'parsed': parsed,
            'failed': failed,
            'parse_rate': parse_rate,
            'top_errors': top_errors,
            'threshold': thresholds[domain],
            'threshold_met': threshold_met,
        }
    
    # Calculate overall rate
    overall_rate = (overall_parsed / overall_total * 100) if overall_total > 0 else 0.0
    
    # Output results
    if format == 'json':
        output_data = {
            'domains': results,
            'overall': {
                'total': overall_total,
                'parsed': overall_parsed,
                'failed': overall_total - overall_parsed,
                'parse_rate': overall_rate,
            },
            'all_thresholds_met': all_thresholds_met,
        }
        click.echo(json.dumps(output_data, indent=2))
    else:
        # Table format
        click.echo()
        click.echo(f"{'Domain':<12} {'Total':>7} {'Parsed':>7} {'Failed':>7} {'Rate':>7} {'Threshold':>10} {'Status':>8}")
        click.echo("-" * 80)
        
        for domain in ['core_api', 'llm', 'agentic', 'cv']:
            stats = results[domain]
            status = "✓ PASS" if stats['threshold_met'] else "✗ FAIL"
            click.echo(
                f"{domain:<12} {stats['total']:>7} {stats['parsed']:>7} {stats['failed']:>7} "
                f"{stats['parse_rate']:>6.1f}% {stats['threshold']:>9.1f}% {status:>8}"
            )
            
            # Show top errors if any
            if stats['top_errors']:
                for reason, count in stats['top_errors']:
                    click.echo(f"  └─ {reason}: {count}")
        
        click.echo("-" * 80)
        click.echo(
            f"{'OVERALL':<12} {overall_total:>7} {overall_parsed:>7} {overall_total - overall_parsed:>7} "
            f"{overall_rate:>6.1f}%"
        )
        click.echo()
        
        if all_thresholds_met:
            click.echo("✓ All domains meet acceptance thresholds")
        else:
            click.echo("✗ One or more domains failed to meet thresholds", err=True)
        click.echo()
    
    # Exit with appropriate code
    sys.exit(0 if all_thresholds_met else 1)


if __name__ == '__main__':
    cli()
