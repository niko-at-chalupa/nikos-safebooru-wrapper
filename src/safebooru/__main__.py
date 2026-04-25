from .client import Client
from .posts import Post
from time import perf_counter
import os
import argparse
from pathlib import Path
from platformdirs import user_data_path
import json
import getpass
import logging
import re

logger = logging.getLogger("rule34-client")

user_data = user_data_path("rule34", "niko")
config_path = user_data / "config.json"

def main():
    if not config_path.exists():
        print("Please put in your rule34.xxx credentials!! You'll only need to do this once!")
        api_key = getpass.getpass("API_KEY: ")
        user_id = input("USER_ID: ")
        config = {"API_KEY": api_key, "USER_ID": user_id}
        user_data.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f)
    else:
        with open(config_path) as f:
            config = json.load(f)
        api_key = config["API_KEY"]
        user_id = config["USER_ID"]

    client = Client(api_key, user_id)

    try:
        from rich.console import Console # type:ignore
        from rich import print as rprint # type:ignore
        from rich.progress import Progress, SpinnerColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn # type:ignore
        _rich = True
        console = Console()
    except ImportError:
        print("Install `rich` *(`pip install rich` / `pipx inject nikos-rule34-wrapper rich # if you're on pipx`)* if you'd like a better CLI experience!!")
        _rich = False

    def rrprint(*args, **kwargs):
        if _rich:
            rprint(*args, **kwargs)
        else:
            new_args = []
            for arg in args:
                if isinstance(arg, str):
                    clean_text = re.sub(r"(?<!\\)\[.*?\]", "", arg)
                    new_args.append(clean_text)
                else:
                    new_args.append(arg)
            print(*new_args, **kwargs)

    parser = argparse.ArgumentParser(description="Rule34 API wrapper/downloader, download them here!!")
    parser.add_argument("--tags", help="Search tags")
    parser.add_argument("--pool-id", type=int, help="Pool ID to fetch posts from")
    parser.add_argument("--favorites-user-id", type=int, help="User ID to fetch favorites from")
    parser.add_argument("--limit", type=int, default=200, help="Limit of posts *(0 for unlimited)*")
    parser.add_argument("--download", action="store_true", help="Download posts")
    parser.add_argument("--destination", type=Path, help="Download destination")
    parser.add_argument("--reset-credentials", action="store_true", help="Prompt for API credentials again and overwrite stored config")
    parser.add_argument("--print-posts", action="store_true", help="Weather to print the posts")
    parser.add_argument("--taginfo", action="store_true",help="Print tags and their catagories *(requires --print-posts)*")
    parser.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level *(default: CRITICAL)*")
    args = parser.parse_args()

    if not args.tags and not args.pool_id and not args.favorites_user_id:
        print("Must specify --tags, --pool-id, or --favorites-user-id")
        exit(1)

    logger.setLevel(args.log_level.upper())

    if not config_path.exists() or args.reset_credentials:
        if args.reset_credentials and config_path.exists():
            print("Resetting stored credentials (will overwrite existing config)!!!")
        else:
            print("Please put in your rule34.xxx credentials!! You'll only need to do this once!\nhttps://api.rule34.xxx/ for more info")
        print("""Example input:
        (input here is not shown) API_KEY: dfaivdijasdica1284198hsauasd248192d
        USER_ID: 123456
        """)
        api_key = getpass.getpass("(input here is not shown) API_KEY: ")
        user_id = input("USER_ID: ")

        if any(marker in api_key for marker in ["api_key=", "user_id=", "&", "?"]) or any(marker in user_id for marker in ["api_key=", "user_id=", "&", "?"]):
            print("It looks like you pasted a URL/query string!!! Please provide only the raw API_KEY and USER_ID values.")

        config = {"API_KEY": api_key, "USER_ID": user_id}
        user_data.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f)
    else:
        with open(config_path) as f:
            config = json.load(f)
        api_key = config["API_KEY"]
        user_id = config["USER_ID"]
        print("Credentials loaded!!! Run with --reset-credentials to re-enter credentials if needed.")
        print("Only this script uses this system for credentials. The real wrapper does not!")

    client = Client(api_key, user_id)

    start = perf_counter()
    posts: list[Post] = []
    if args.pool_id:
        print("- Fetching posts from pool...")
        posts = client.list_posts_from_pool(args.pool_id)
    elif args.favorites_user_id:
        print("- Fetching posts from favorites...")
        posts = client.list_posts_from_favorites(args.favorites_user_id)
    else:
        pid = 0
        batch_size = 1000
        if _rich:
            with Progress(SpinnerColumn(), "[progress.description]{task.description}", transient=True, console=console) as progress:
                task = progress.add_task("Fetching posts...", total=None)
                while True:
                    batch = client.list_posts(tags=args.tags, limit=batch_size, pid=pid)
                    if not batch:
                        break
                    posts.extend(batch)
                    pid += 1
                    if args.limit > 0 and len(posts) >= args.limit:
                        posts = posts[:args.limit]
                        break
                    progress.update(task, description=f"Fetching posts... (page {pid})")
        else:
            print("Fetching posts...")
            while True:
                batch = client.list_posts(tags=args.tags, limit=batch_size, pid=pid)
                if not batch:
                    break
                posts.extend(batch)
                pid += 1
                if args.limit > 0 and len(posts) >= args.limit:
                    posts = posts[:args.limit]
                    break
                print(f"Fetched page {pid/50+1}") # Pages are in base 50. Page one is page 0, page two is page 50...

    if args.limit > 0 and len(posts) > args.limit:
        posts = posts[:args.limit]

    if args.print_posts:
        for post in posts:
            print(f"FILE URL: {post.file_url}")
            print(f"ID: {post.post_id}\nPARENT ID: {post.parent_id}")
            if args.taginfo:
                if post.tag_info:
                    print(str(post.tag_info))
                else:
                    print("Doesn't have TagInfo")
            print("---")
    elif args.taginfo:
        rrprint("[yellow]! --taginfo doesn't do anything if not paired with --print-posts")

    print(f"- Took {round(perf_counter() - start, 2)}s")
    print(f"- Found {len(posts)} posts")

    def download_posts(posts: list[Post], destination: Path) -> None:
        if _rich:
            with Progress(
                "[progress.description]{task.description}",
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading...", total=len(posts))
                for post in posts:
                    client.download_post(post=post, destination=destination)
                    progress.advance(task)
                    rprint(f"- Downloaded post {str(post.post_id)}")
        else:
            for post in posts:
                client.download_post(post=post, destination=destination)
                print(f"- Downloaded post {str(post.post_id)}")

    if args.download:
        if not args.destination:
            rrprint("[bold red]!!! --destination required when --download is set")
            exit(1)
        download_posts(posts=posts, destination=args.destination)
        rrprint("[bold green]Finished!!")
    elif not args.print_posts:
        rrprint("[yellow]! You don't have an operation set up to do anything!!")

if __name__ == "__main__":
    main()