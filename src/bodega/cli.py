import click

@click.group()
@click.version_option()
def main():
    """Bodega - Grocery lists for humans and coding agents"""
    pass

if __name__ == "__main__":
    main()
