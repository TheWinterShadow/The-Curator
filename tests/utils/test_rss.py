import xml.etree.ElementTree as ET

import pytest

from the_curator.utils.rss import RSSFeed

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"

_SAMPLE_RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="{ITUNES}">
  <channel>
    <title>Test Podcast</title>
  </channel>
</rss>"""

_SAMPLE_RSS_WITH_EPISODES = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="{ITUNES}">
  <channel>
    <title>Test Podcast</title>
    <item>
      <title>Episode 1</title>
      <itunes:episode>1</itunes:episode>
    </item>
    <item>
      <title>Episode 3</title>
      <itunes:episode>3</itunes:episode>
    </item>
  </channel>
</rss>"""


def _make_feed(xml: str = _SAMPLE_RSS) -> RSSFeed:
    feed = RSSFeed.__new__(RSSFeed)
    feed.bucket_name = "test-bucket"
    feed.file_path = "feed.xml"
    feed.tree = ET.ElementTree(ET.fromstring(xml))  # noqa: S314
    return feed


def test_root_raises_when_tree_not_loaded() -> None:
    feed = RSSFeed("bucket", "feed.xml")
    with pytest.raises(ValueError, match="not loaded"):
        feed._root()


def test_get_latest_episode_number_empty_channel() -> None:
    feed = _make_feed()
    assert feed.get_latest_episode_number() == 0


def test_get_latest_episode_number_returns_max() -> None:
    feed = _make_feed(_SAMPLE_RSS_WITH_EPISODES)
    assert feed.get_latest_episode_number() == 3


def test_add_item_appends_to_channel() -> None:
    feed = _make_feed()
    feed.add_item(
        title="New Episode",
        sub_title="A subtitle",
        summary="A summary",
        author="Test Author",
        description="A description",
        link="https://example.com/ep1.mp3",
        length=12345,
    )

    channel = feed._root()[0]
    items = channel.findall("item")
    assert len(items) == 1

    item = items[0]
    assert item.findtext("title") == "New Episode"
    assert item.findtext("description") == "A description"
    assert item.findtext("link") == "https://example.com/ep1.mp3"
    assert item.findtext(f"{{{ITUNES}}}subtitle") == "A subtitle"
    assert item.findtext(f"{{{ITUNES}}}summary") == "A summary"
    assert item.findtext(f"{{{ITUNES}}}author") == "Test Author"
    assert item.findtext(f"{{{ITUNES}}}episode") == "1"

    enclosure = item.find("enclosure")
    assert enclosure is not None
    assert enclosure.get("url") == "https://example.com/ep1.mp3"
    assert enclosure.get("type") == "audio/mpeg"
    assert enclosure.get("length") == "12345"


def test_add_item_increments_episode_number() -> None:
    feed = _make_feed(_SAMPLE_RSS_WITH_EPISODES)
    feed.add_item(
        title="Episode 4",
        sub_title="",
        summary="",
        author="",
        description="",
        link="https://example.com/ep4.mp3",
        length=0,
    )

    channel = feed._root()[0]
    new_item = channel.findall("item")[-1]
    assert new_item.findtext(f"{{{ITUNES}}}episode") == "4"
    guid = new_item.findtext("guid") or ""
    assert guid.endswith("-episode-4")
