from pydantic.dataclasses import dataclass
import shlex
import requests
from .posts import Post
from pathlib import Path
import magic
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

class Formatter(logging.Formatter):
    format_str = "[%(levelname)s] %(level_symbol)s %(name)s: %(message)s"

    symbols = {
        logging.DEBUG: "\x1b[37m.\x1b[0m",
        logging.INFO: "\x1b[32m-\x1b[0m",
        logging.WARNING: "\x1b[33m!\x1b[0m",
        logging.ERROR: "\x1b[31m!!\x1b[0m",
        logging.CRITICAL: "\x1b[41m!!!\x1b[0m"
    }

    def format(self, record):
        record.level_symbol = self.symbols.get(record.levelno, "?")
        formatter = logging.Formatter(self.format_str)
        return formatter.format(record)

logger = logging.getLogger("rule34-client")
handler = logging.StreamHandler()
handler.setFormatter(Formatter())
logger.addHandler(handler)
logger.setLevel(logging.WARNING)

def _add_extension(filepath: Path) -> Path:
        mime = magic.from_file(filepath, mime=True)
        mimetoext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/svg+xml": ".svg",
            "image/avif": ".avif",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "video/x-matroska": ".mkv",
            "video/webm": ".webm",
            "video/mpeg": ".mpeg",
            "video/3gpp": ".3gp",
        }
        ext = mimetoext.get(mime)
        if not ext:
            raise ValueError(f"Unsupported or unrecognized MIME type: {mime}")
        new_path = filepath.with_suffix(filepath.suffix + ext)
        filepath.rename(new_path)
        return new_path

@dataclass
class Autocompletion:
    """
    A single autocompletion.

    # Attributes
    ---
    label : str
        What should be shown to the user in the frontend. It follows the format `{tag} ({count})`.
    value : str
        The actual tag.
    """
    label: str
    value: str

    def __str__(self):
        return self.label
    
    def __repr__(self):
        return self.value

class Client:
    def __init__(self, api_key: str, user_id: str):
        self.API_KEY = api_key
        self.USER_ID = user_id

    def _get_post_ids_from_html(self, html: str, base_url: str, params: dict) -> list[int]:
        def extract_ids(h: str) -> list[int]:
            soup = BeautifulSoup(h, "lxml")
            post_ids = []
            for tag in soup.find_all(["span", "a"], id=lambda v: v and v.startswith("p")):
                try:
                    post_ids.append(int(tag["id"][1:]))
                except ValueError:
                    continue
            return post_ids

        def get_page_pids(h: str) -> list[int]:
            soup = BeautifulSoup(h, "lxml")
            paginator = soup.find("div", id="paginator")
            if not paginator:
                return []

            last_pid = None

            # <a alt="last page">
            last_a = paginator.find("a", alt="last page")
            if last_a:
                for part in last_a.get("href", "").split("&"):
                    if part.startswith("pid="):
                        try:
                            last_pid = int(part[4:])
                        except ValueError:
                            pass

            # <a name="lastpage">
            if last_pid is None:
                last_a = paginator.find("a", attrs={"name": "lastpage"})
                if last_a:
                    for part in last_a.get("onclick", "").replace("&amp;", "&").split("&"):
                        if part.startswith("pid="):
                            try:
                                #last_pid = int(part.split(";")[0].split(" ")[0][4:])
                                last_pid = int(part.split(";")[0].replace("'", "")[4:])
                            except ValueError:
                                pass

            if last_pid is None:
                return []

            return list(range(50, last_pid + 50, 50))

        post_ids = extract_ids(html)
        for pid in get_page_pids(html):
            paged_params = {**params, "pid": pid}
            response = self._get_with_retry(base_url, params=paged_params, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            })
            post_ids.extend(extract_ids(response.text))

        return post_ids

    def _get_with_retry(self, url: str, params: dict | None = None, headers: dict | None = None, stream: bool = False, max_retries: int = 3) -> requests.Response:
        for attempt in range(max_retries):
            try:
                start = time.perf_counter()
                logger.debug(f"- Attempting request to {url} (attempt {attempt + 1}/{max_retries})")
                response = requests.get(url, params=params, headers=headers, stream=stream)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited!!! (429), retrying after {retry_after}s")
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                logger.debug(f"Request to {url} succeeded, and the request took {round(time.perf_counter()-start, 2)} seconds")
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Request to {url} failed after {max_retries} attempts")
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("ERROR !!!!!!!!!!!!! 😭😭😭")

    def list_posts(self, tags: str | set[str], limit: int = 1000, pid: int | None = None) -> list[Post]:
        """
        List posts from rule34.xxx.

        # Parameters
        ---
        tags : str | set[str]
            The tags you want to search for while listing.
            This supports everything you could put in rule34.xxx's search, like "sort:score", "-ai_generated", and whatever else.
            Pass in an empty string or empty set to get everything.
        limit : int
            The limit of posts that will be returned. There is a hard limit of 1000 posts per request.
        pid : int | None
            The page number.
        """
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "api_key": self.API_KEY,
            "user_id": self.USER_ID,
            "fields": "tag_info",
            "json": "1",
            "limit": str(limit),
        }
        if pid is not None:
            params["pid"] = str(pid)
        if isinstance(tags, set):
            params["tags"] = " ".join(tags)
        else:
            params["tags"] = tags
        response = self._get_with_retry("https://api.rule34.xxx/index.php", params=params)
        if response.content.decode("utf-8") == "":
            return []
        return Post.from_multiple_json(response.content.decode("utf-8"))

    def get_post(self, post_id: int) -> Post:
        """
        Get a post from its ID.

        # Parameters
        ---
        post_id : int
            The ID of the post you want to get.
        """
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "api_key": self.API_KEY,
            "user_id": self.USER_ID,
            "fields": "tag_info",
            "id": post_id,
            "json": "1"
        }
        response = self._get_with_retry("https://api.rule34.xxx/index.php", params=params)
        return Post.from_json(response.content.decode("utf-8"))
    
    def download_post(self, post: Post, destination: Path, file_name: str | None = None, file_url: str | None = None) -> None:
        """
        Download a post's media.

        # Parameters
        ---
        post : Post
            Post to download.
        destination : Path
            Directory to where the file will be saved.
        file_name : str | None
            Name for the file.
        file_url : str | None
            URL to download from. `None` will default to `post.file_url`.
            You can use stuff like `post.file_url`, `post.preview_url`, & `post.sample_url`.
        """
        if not file_url:
            response = self._get_with_retry(post.file_url, stream=True)
        else: 
            response = self._get_with_retry(file_url, stream=True)

        file_name2: str = str(post.post_id)
        if file_name:
            file_name2: str = str(file_name)
        elif destination.suffix: # A way to check if it leads to a file or not
            file_name2: str = destination.name
        
        destination2 = destination
        if destination.suffix: # A way to check if it leads to a file or not
            destination2 = destination.parent
        else:
            destination2 = destination
        if not destination2.exists():
            raise FileNotFoundError(f"{destination2} does NOT exist!")

        with Path(destination2 / file_name2).open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        _add_extension(Path(destination2 / file_name2))

    def list_posts_from_pool(self, pool_id: int) -> list[Post]:
        """
        Lists `Post` objects from a pool.

        NOTE: This is slow!! For every single ID in a pool, we get a post from it. If you just want to get the post IDs, use `list_post_ids_from_pool`.

        # Parameters
        ---
        pool_id : int
            The ID of the pool you're getting the posts from.
        """
        params = {
            "page": "pool",
            "s": "show",
            "id": pool_id
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        response = self._get_with_retry("https://rule34.xxx/index.php", params=params, headers=headers)
        html = str(response.content.decode("utf-8"))

        start = time.perf_counter()
        post_ids = self._get_post_ids_from_html(html=html, base_url="https://rule34.xxx/index.php", params=params)
        logger.debug(f"Took {round(time.perf_counter()-start, 2)} seconds to get post ids from html")
        
        start = time.perf_counter()
        posts = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.get_post, post_id=post): post for post in post_ids}
            for future in as_completed(futures):
                posts.append(future.result())
        logger.debug(f"Took {round(time.perf_counter()-start, 2)} seconds to get all Post objects")

        return posts

    def list_posts_from_favorites(self, user: int) -> list[Post]:
        """
        Lists `Post` objects from a user's favorites.

        NOTE: This is slow!! For every single ID in their favorites, we get a post from it. If you just want to get the post IDs, use `list_post_ids_from_favorites`.

        # Parameters
        ---
        user : int
            User ID of the user you're getting favorites from.
        """
        params = {
            "page": "favorites",
            "s": "view",
            "id": user
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        response = self._get_with_retry("https://rule34.xxx/index.php", params=params, headers=headers)
        html = str(response.content.decode("utf-8"))

        start = time.perf_counter()
        post_ids = self._get_post_ids_from_html(html=html, base_url="https://rule34.xxx/index.php", params=params)
        logger.debug(f"Took {round(time.perf_counter()-start, 2)} seconds to get post ids from html")

        start = time.perf_counter()
        posts = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.get_post, post_id=post): post for post in post_ids}
            for future in as_completed(futures):
                posts.append(future.result())
        logger.debug(f"Took {round(time.perf_counter()-start, 2)} seconds to get all Post objects")

        return posts

    def list_post_ids_from_pool(self, pool_id: int) -> list[int]:
        """
        Lists IDs of posts from a pool.

        # Parameters
        ---
        pool_id : int
            The ID of the pool you're getting the post IDs from.
        """
        params = {
            "page": "pool",
            "s": "show",
            "id": pool_id
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        response = self._get_with_retry("https://rule34.xxx/index.php", params=params, headers=headers)
        return self._get_post_ids_from_html(html=response.content.decode("utf-8"), base_url="https://rule34.xxx/index.php", params=params)

    def list_post_ids_from_favorites(self, user: int) -> list[int]:
        """
        Lists IDs of posts from a user's favorites.

        # Parameters
        ---
        user : int
            The ID of the user you're getting the favorites from.
        """
        params = {
            "page": "favorites",
            "s": "view",
            "id": user
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        response = self._get_with_retry("https://rule34.xxx/index.php", params=params, headers=headers)
        return self._get_post_ids_from_html(html=response.content.decode("utf-8"), base_url="https://rule34.xxx/index.php", params=params)

    def autocomplete(self, query: str) -> list[Autocompletion]:
        """
        Gets autocompletions from an incomplete tag.

        # Parameters
        ---
        query : str
            Any incomplete tag. Works even if blank.
        """
        params = {
            "q": query,
            "api_key": self.API_KEY,
            "user_id": self.USER_ID
        }
        response = self._get_with_retry("https://api.rule34.xxx/autocomplete.php", params=params)
        d = response.json()
        completions: list[Autocompletion] = []
        for completion in d:
            completions.append(Autocompletion(completion.get("label"), completion.get("value")))
        return completions