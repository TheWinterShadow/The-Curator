from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.requests import Request
from the_curator.podcast_generation import PodcastGeneration
from google.cloud import storage
import datetime
import os


mcp = FastMCP("The Curator")
generator = PodcastGeneration()


@mcp.tool()
def create_podcast_transcript(topic: str) -> list[tuple[str, str]]:
    """
    Create a podcast transcript on the given topic.
    """
    return generator.generate_transcript(topic)


@mcp.tool()
def create_podcast_episode(title: str, description: str, transcript: list[tuple[str, str]]) -> dict[str, str]:
    """
    Create a podcast episode with the given title, description, and content.
    """
    audio_file_name = generator.generate_podcast(transcript)

    storage_client = storage.Client()
    bucket_name = os.environ.get("GCS_BUCKET_NAME", "the-curator-podcasts")
    print(f"Uploading {audio_file_name} to bucket {bucket_name}...")
    bucket = storage_client.bucket(bucket_name)
    destination_blob_name = f"episodes/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}/{title.replace(' ', '_')}.wav"
    print(f"Uploading file to {destination_blob_name}...")
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(audio_file_name)

    print(
        f"File {audio_file_name} uploaded to {blob.name}."
    )

    return {"episode_id": audio_file_name, "status": "created"}


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"service": "the-curator", "status": "ok"})

app = Starlette(routes=[Route("/health", health)])
app.mount("/mcp", mcp.streamable_http_app())
app.mount("/", mcp.sse_app())

if __name__ == "__main__":
    mcp.run(transport="stdio")
