from .posts import Post as Post
from _typeshed import Incomplete
from pathlib import Path

logger: Incomplete
formatter: Incomplete
handler: Incomplete

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

class Client:
    API_KEY: Incomplete
    USER_ID: Incomplete
    def __init__(self, api_key: str, user_id: str) -> None: ...
    def list_posts(self, tags: str | set[str], limit: int = 1000, pid: int | None = None) -> list[Post]:
        '''
        List posts.

        # Parameters
        ---
        tags : str | set[str]
            The tags you want to search for while listing.
            This supports everything you could put in rule34.xxx\'s search, like "sort:score", "-ai_generated", and whatever else.
            Pass in an empty string or empty set to get everything.
        limit : int
            The limit of posts that will be returned. There is a hard limit of 1000 posts per request.
        pid : int | None
            The page number.
        '''
    def get_post(self, post_id: int) -> Post:
        """
        Get a post from its ID.

        # Parameters
        ---
        post_id : int
            The ID of the post you want to get.
        """
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
    def list_posts_from_pool(self, pool_id: int) -> list[Post]:
        """
        Lists `Post` objects from a pool.

        NOTE: This is slow!! For every single ID in a pool, we get a post from it. If you just want to get the post IDs, use `list_post_ids_from_pool`.

        # Parameters
        ---
        pool_id : int
            The ID of the pool you're getting the posts from.
        """
    def list_posts_from_favorites(self, user: int) -> list[Post]:
        """
        Lists `Post` objects from a user's favorites.

        NOTE: This is slow!! For every single ID in their favorites, we get a post from it. If you just want to get the post IDs, use `list_post_ids_from_favorites`.

        # Parameters
        ---
        user : int
            User ID of the user you're getting favorites from.
        """
    def list_post_ids_from_pool(self, pool_id: int) -> list[int]:
        """
        Lists IDs of posts from a pool.

        # Parameters
        ---
        pool_id : int
            The ID of the pool you're getting the post IDs from.
        """
    def list_post_ids_from_favorites(self, user: int) -> list[int]:
        """
        Lists IDs of posts from a user's favorites.

        # Parameters
        ---
        user : int
            The ID of the user you're getting the favorites from.
        """
    def autocomplete(self, query: str) -> list[Autocompletion]:
        """
        Gets autocompletions from an incomplete tag.

        # Parameters
        ---
        query : str
            Any incomplete tag. Works even if blank.
        """
