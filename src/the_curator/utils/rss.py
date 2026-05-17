import os
from datetime import UTC, datetime
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from google.cloud import storage


class RSSFeed:
    def __init__(self, bucket_name: str, file_path: str):
        self.bucket_name = bucket_name
        self.file_path = file_path
        self.tree: ET.ElementTree | None = None

    def _root(self) -> Element:
        if self.tree is None:
            raise ValueError("RSS feed not loaded. Call load() first.")
        root = self.tree.getroot()
        if root is None:
            raise ValueError("RSS feed has no root element.")
        return root

    def load(self) -> None:
        # Initialize the GCS client
        storage_client = storage.Client(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "the-curator-496412")
        )

        # Get the bucket and the specific blob (object)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(self.file_path)

        data = blob.download_as_bytes().decode('utf-8')
        self.tree = ET.ElementTree(ET.fromstring(data))  # noqa: S314

    def save(self) -> None:
        if self.tree is None:
            raise ValueError("RSS feed not loaded. Call load() before saving.")

        # Convert the ElementTree to a byte string
        xml_data = ET.tostring(self._root(), encoding='utf-8', method='xml')

        # Initialize the GCS client
        storage_client = storage.Client(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "the-curator-496412")
        )

        # Get the bucket and the specific blob (object)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(self.file_path)

        # Upload the updated XML data back to GCS
        blob.upload_from_string(xml_data, content_type='application/xml')

    def get_latest_episode_number(self) -> int:
        channel: Element = self._root()[0]
        ITUNES_EPISODE = '{http://www.itunes.com/dtds/podcast-1.0.dtd}episode'
        episode_numbers = []
        for item in channel.findall('item'):
            el = item.find(ITUNES_EPISODE)
            if el is not None and el.text is not None:
                episode_numbers.append(int(el.text))
        return max(episode_numbers) if episode_numbers else 0

    def add_item(
        self,
        title: str,
        sub_title: str,
        summary: str,
        author: str,
        description: str,
        link: str,
        length: int,
    ) -> None:
        ITUNES = 'http://www.itunes.com/dtds/podcast-1.0.dtd'

        ET.register_namespace('itunes', ITUNES)
        ET.register_namespace(
            'content', 'http://purl.org/rss/1.0/modules/content/')

        channel: Element = self._root()[0]

        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = title
        ET.SubElement(item, 'description').text = description
        ET.SubElement(item, 'link').text = link
        now = datetime.now(UTC)
        next_ep = self.get_latest_episode_number() + 1
        ET.SubElement(item, 'guid').text = f"{now.strftime('%Y%m%d')}-episode-{next_ep}"
        ET.SubElement(item, 'pubDate').text = now.strftime('%a, %d %b %Y %H:%M:%S GMT')

        enclosure = ET.SubElement(item, 'enclosure')
        enclosure.set('url', link)
        enclosure.set('type', 'audio/mpeg')
        enclosure.set('length', str(length))

        ET.SubElement(item, f'{{{ITUNES}}}subtitle').text = sub_title
        ET.SubElement(item, f'{{{ITUNES}}}summary').text = summary
        ET.SubElement(item, f'{{{ITUNES}}}author').text = author
        ET.SubElement(item, f'{{{ITUNES}}}episode').text = str(next_ep)

        ET.indent(self._root(), space='  ')
