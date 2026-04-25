from _typeshed import Incomplete
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field as Field, model_validator as model_validator

class Rating(Enum):
    EXPLICIT = 0
    QUESTIONABLE = 1
    SAFE = 2
    @classmethod
    def from_string(cls, value: str): ...

@dataclass
class TagInfo:
    '''
    Catagorizes tags.

    # Attributes
    ---
    general : set[str]
        General tags that don\'t belong in any other catagory. Most tags *(like "futanari")* fall under this.
    meta : set[str]
        Tags that describe special properties of a post, like if they have sound, or their resolution.
        Examples include:
            - sound
            - mp4
            - video
            - large_filesize
            - 3d
    artists : set[str]
        Tags that identify the original creator of a post\'s media.
    characters : set[str]
        Tags that identify named characters within a post.
    copyrights : set[str]
        Tags that identify the source franchise, series, or original work that the post\'s media is derived from, or associated with.
        Examples include:
            - vocaloid
            - utau
            - doki_doki_literature_club
            - monitoring_(deco*27)
    '''
    count: dict[str, int] = field(default_factory=dict)
    general: set[str] = field(default_factory=set)
    meta: set[str] = field(default_factory=set)
    artists: set[str] = field(default_factory=set)
    characters: set[str] = field(default_factory=set)
    copyrights: set[str] = field(default_factory=set)
    @classmethod
    def from_json(cls, tag_info: list[dict]) -> TagInfo: ...

class Post(BaseModel):
    '''
    Represents a post on rule34.xxx.

    # Properties
    ---
    height : int
        Height of the post\'s media.
    score : int
        Defined by how many people voted "up" on the post.
    file_url : str
        URL to the post\'s media.
    parent_id : int
        Unique ID to a parent post *(if any)*.
        If `0`, then it is a top level post *(no parent)*.
    sample_url : str
        URL to a compressed version of the post\'s media. 
        Identical to the post\'s `file_url` if the media is small.
        If the post\'s media is a video, then this is a still image from that video.
    sample_width : int
        Defined by the width of the sample image *(the image from `sample_url`)*.
    sample_height : int
        Defined by the height of the sample image *(the image from `sample_url`)*.
    preview_url : str
        URL to a super small image of the media.
    rating : Rating
        The post\'s rating.
    tags : set[str]
        The post\'s tags.
    post_id : int
        The unique ID to identify the post.
    width : int
        Width of the post\'s media.
    change : int
        Unix timestamp to when was the last change to the post.
    hash : str
        I have no clue what defines this. I tried the md5 of the post\'s media, but it doesn\'t match up with the hash given to us by the API.
    owner : str
        Defined by the username of the uploader.
    status : str
        The post\'s status.
        This can be "active", "deleted", or something else. I have not found anything other than the two in my testing, but the fact it\'s a string and not a boolean leads me to believe there are more possible values.
    source : str
        URL to a source.
    has_notes : bool
        Weather if notes are attached to the post.
        Notes are things that get overlayed on top of a post\'s media, shown as transparent white boxes on the site.
    comment_count : int
        Defined by how many comments are on the post.
    post_json : str | None
        Raw JSON from the response used to get information about the post.
    tag_info : TagInfo | None
        Tags represented by a TagInfo object.
    '''
    height: int
    score: int
    file_url: str
    parent_id: int
    sample_url: str
    sample_width: int
    sample_height: int
    preview_url: str
    rating: Rating
    tags: set[str]
    post_id: int
    width: int
    change: int
    post_hash: str
    owner: str
    status: str
    source: str
    has_notes: bool
    comment_count: int
    post_json: str | None
    tag_info: TagInfo | None
    model_config: Incomplete
    @classmethod
    def from_json(cls, post_json: str) -> Post: ...
    @classmethod
    def from_multiple_json(cls, posts_json: str) -> list['Post']: ...
