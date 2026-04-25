from pydantic.dataclasses import dataclass
import requests
from .posts import Post
from pathlib import Path
import magic
import time
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

logger = logging.getLogger("safebooru-client")
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

def _get_with_retry(url: str, params: dict | None = None, headers: dict | None = None, stream: bool = False, max_retries: int = 3) -> requests.Response:
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


def list_posts(tags: str | set[str], limit: int = 1000, pid: int | None = None) -> list[Post]:
    """
    List posts from safebooru.org.

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
    response = _get_with_retry("https://safebooru.org/index.php", params=params)
    if response.content.decode("utf-8") == "":
        return []
    return Post.from_multiple_json(response.content.decode("utf-8"))


def get_post(post_id: int) -> Post:
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
        "fields": "tag_info",
        "id": post_id,
        "json": "1"
    }
    response = _get_with_retry("https://safebooru.org/index.php", params=params)
    return Post.from_json(response.content.decode("utf-8"))


def download_post(post: Post, destination: Path, file_name: str | None = None, file_url: str | None = None) -> None:
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
        response = _get_with_retry(post.file_url, stream=True)
    else:
        response = _get_with_retry(file_url, stream=True)

    file_name2: str = str(post.post_id)
    if file_name:
        file_name2 = str(file_name)
    elif destination.suffix:  # A way to check if it leads to a file or not
        file_name2 = destination.name

    destination2 = destination
    if destination.suffix:  # A way to check if it leads to a file or not
        destination2 = destination.parent
    else:
        destination2 = destination
    if not destination2.exists():
        raise FileNotFoundError(f"{destination2} does NOT exist!")

    with Path(destination2 / file_name2).open("wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    _add_extension(Path(destination2 / file_name2))


def _autocomplete(query: str) -> list[Autocompletion]:
    """
    Gets autocompletions from an incomplete tag.

    # Parameters
    ---
    query : str
        Any incomplete tag. Works even if blank.
    """
    raise NotImplementedError
    params = {
        "q": query,
    }
    response = requests.get("https://api.rule34.xxx/autocomplete.php", params=params)
    d = response.json()
    completions: list[Autocompletion] = []
    for completion in d:
        completions.append(Autocompletion(completion.get("label"), completion.get("value")))
    return completions