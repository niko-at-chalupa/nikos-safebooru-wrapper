import json
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, model_validator

class Rating(Enum):
    EXPLICIT = 0
    QUESTIONABLE = 1
    SAFE = 2

    @classmethod
    def from_string(cls, value: str):
        if value == "e" or value == "explicit":
            return cls.EXPLICIT
        elif value == "q" or value == "questionable":
            return cls.QUESTIONABLE
        elif value == "s" or value == "safe":
            return cls.SAFE
        else:
            raise ValueError("Value passed into from_string isn't valid!!")

@dataclass
class TagInfo:
    """
    Catagorizes tags.

    # Attributes
    ---
    general : set[str]
        General tags that don't belong in any other catagory. Most tags *(like "futanari")* fall under this.
    meta : set[str]
        Tags that describe special properties of a post, like if they have sound, or their resolution.
        Examples include:
            - sound
            - mp4
            - video
            - large_filesize
            - 3d
    artists : set[str]
        Tags that identify the original creator of a post's media.
    characters : set[str]
        Tags that identify named characters within a post.
    copyrights : set[str]
        Tags that identify the source franchise, series, or original work that the post's media is derived from, or associated with.
        Examples include:
            - vocaloid
            - utau
            - doki_doki_literature_club
            - monitoring_(deco*27)
    """

    count: dict[str, int] = field(default_factory=dict)
    general: set[str] = field(default_factory=set)
    meta: set[str] = field(default_factory=set)
    artists: set[str] = field(default_factory=set)
    characters: set[str] = field(default_factory=set)
    copyrights: set[str] = field(default_factory=set)

    @classmethod
    def from_json(cls, tag_info: list[dict]) -> "TagInfo":
        result = cls()
        for entry in tag_info:
            match entry["type"]:
                case "tag":      result.general.add(entry["tag"])
                case "metadata": result.meta.add(entry["tag"])
                case "artist":   result.artists.add(entry["tag"])
                case "character":result.characters.add(entry["tag"])
                case "copyrights":result.copyrights.add(entry["tag"])
            result.count[entry["tag"]] = int(entry["count"])
        return result
    
    def __str__(self) -> str:
        lines = [f"{self.__class__.__name__}:"]
        for field_name, values in self.__dict__.items():
            if field_name == "count":
                continue
            lines.append(f"  {field_name}:")
            for value in sorted(values):
                lines.append(f"    - {value} ({self.count[value]})")
        return "\n".join(lines)

class Post(BaseModel):
    """
    Represents a post on rule34.xxx.

    # Properties
    ---
    height : int
        Height of the post's media.
    score : int
        Defined by how many people voted "up" on the post.
    file_url : str
        URL to the post's media.
    parent_id : int
        Unique ID to a parent post *(if any)*.
        If `0`, then it is a top level post *(no parent)*.
    sample_url : str
        URL to a compressed version of the post's media. 
        Identical to the post's `file_url` if the media is small.
        If the post's media is a video, then this is a still image from that video.
    sample_width : int
        Defined by the width of the sample image *(the image from `sample_url`)*.
    sample_height : int
        Defined by the height of the sample image *(the image from `sample_url`)*.
    preview_url : str
        URL to a super small image of the media.
    rating : Rating
        The post's rating.
    tags : set[str]
        The post's tags.
    post_id : int
        The unique ID to identify the post.
    width : int
        Width of the post's media.
    change : int
        Unix timestamp to when was the last change to the post.
    hash : str
        I have no clue what defines this. I tried the md5 of the post's media, but it doesn't match up with the hash given to us by the API.
    owner : str
        Defined by the username of the uploader.
    status : str
        The post's status.
        This can be "active", "deleted", or something else. I have not found anything other than the two in my testing, but the fact it's a string and not a boolean leads me to believe there are more possible values.
    source : str
        URL to a source.
    has_notes : bool
        Weather if notes are attached to the post.
        Notes are things that get overlayed on top of a post's media, shown as transparent white boxes on the site.
    comment_count : int
        Defined by how many comments are on the post.
    post_json : str | None
        Raw JSON from the response used to get information about the post.
    tag_info : TagInfo | None
        Tags represented by a TagInfo object.
    """

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
    status: str  # Looks like it's either "active" or "deleted". I haven't seen anything other than that, but I assume there is another value because it is a string and not a bool.
    source: str
    has_notes: bool
    comment_count: int
    post_json: str | None = None
    tag_info: TagInfo | None = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_json(cls, post_json: str) -> "Post":
        d = json.loads(post_json)
        if isinstance(d, list):
            if len(d) != 1:
                raise ValueError(f"Expected a single post object, got a list of {len(d)}. Use Post.many_from_json() instead.")
            d = d[0]
        return cls(
            height=d["height"],
            score=d["score"],
            file_url=d["file_url"],
            parent_id=d["parent_id"],
            sample_url=d["sample_url"],
            sample_width=d["sample_width"],
            sample_height=d["sample_height"],
            preview_url=d["preview_url"],
            rating=Rating.from_string(d["rating"]),
            tags=set(d["tags"].split()),
            post_id=d["id"],
            width=d["width"],
            change=d["change"],
            post_hash=d["hash"],
            owner=d["owner"],
            status=d["status"],
            source=d.get("source", ""),
            has_notes=d["has_notes"],
            comment_count=d["comment_count"],
            post_json=post_json,
            tag_info=TagInfo.from_json(d["tag_info"]) if "tag_info" in d else None,
        )

    @classmethod
    def from_multiple_json(cls, posts_json: str) -> list["Post"]:
        d = json.loads(posts_json)
        if not isinstance(d, list):
            d = [d]
        return [cls.from_json(json.dumps(post)) for post in d]
