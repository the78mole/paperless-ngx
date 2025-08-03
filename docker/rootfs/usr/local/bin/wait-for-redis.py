#!/usr/bin/env python3
"""
Simple script which attempts to ping the Redis broker as set in the environment for
a certain number of times, waiting a little bit in between

"""

import os
import sys
import time
from urllib.parse import urlparse, urlunparse

import click
from redis import Redis


def normalize_redis_url(url: str) -> str:
    """
    Normalize a Redis URL to ensure compatibility across different Redis library versions.
    
    Some older versions of the Redis library have issues parsing URLs with empty usernames
    in the format redis://:password@host:port. This function normalizes such URLs to 
    ensure they work reliably.
    
    Args:
        url: Redis URL string
        
    Returns:
        Normalized Redis URL string
    """
    if not url or not isinstance(url, str):
        return url
        
    # Only process redis:// and rediss:// URLs
    if not url.lower().startswith(('redis://', 'rediss://')):
        return url
    
    try:
        parsed = urlparse(url)
        
        # Check if we have an empty username with a password or empty auth
        if parsed.username == '':
            if parsed.password:
                # Empty username with password: redis://:password@host:port
                # Convert to: redis://default:password@host:port
                netloc = f"default:{parsed.password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
            else:
                # Empty username and password: redis://:@host:port  
                # Convert to: redis://host:port (remove auth entirely)
                netloc = parsed.hostname
                if parsed.port:
                    netloc += f":{parsed.port}"
            
            # Reconstruct the URL with the normalized netloc
            normalized = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return normalized
            
    except Exception:
        # If parsing fails for any reason, return the original URL
        pass
    
    # Return unchanged if no normalization needed
    return url


@click.command(context_settings={"show_default": True})
@click.option(
    "--retry-count",
    default=5,
    type=int,
    help="Count of times to retry the Redis connection",
)
@click.option(
    "--retry-sleep",
    default=5,
    type=int,
    help="Seconds to wait between Redis connection retries",
)
@click.argument(
    "redis_url",
    type=str,
    envvar="PAPERLESS_REDIS",
    default="redis://localhost:6379",
)
def wait(redis_url: str, retry_count: int, retry_sleep: int) -> None:
    click.echo("Waiting for Redis...")

    # Normalize the Redis URL to ensure compatibility across Redis library versions
    normalized_url = normalize_redis_url(redis_url)

    attempt = 0
    with Redis.from_url(url=normalized_url) as client:
        while attempt < retry_count:
            try:
                client.ping()
                break
            except Exception as e:
                click.echo(
                    f"Redis ping #{attempt} failed.\n"
                    f"Error: {e!s}.\n"
                    f"Waiting {retry_sleep}s",
                )
                time.sleep(retry_sleep)
                attempt += 1

    if attempt >= retry_count:
        click.echo(
            "Failed to connect to redis using environment variable PAPERLESS_REDIS.",
        )
        sys.exit(os.EX_UNAVAILABLE)
    else:
        click.echo("Connected to Redis broker.")
        sys.exit(os.EX_OK)


if __name__ == "__main__":
    wait()
