from flask.cli import with_appcontext
import click
from utils.gpu_data_fetcher import fetch_gpu_data

@click.command('fetch-gpu-data')
@with_appcontext
def fetch_gpu_data_command():
    """Fetch GPU data from providers"""
    try:
        fetch_gpu_data()
        click.echo('Successfully fetched GPU data')
    except Exception as e:
        click.echo(f'Error fetching GPU data: {str(e)}', err=True)
        raise
