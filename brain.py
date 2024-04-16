import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

import instructor
import requests
import streamlit as st
from openai import OpenAI
from pydantic import BaseModel

from constant import API_BASE_URL, BATCH_SIZE, PARALLEL_WORKER_COUNT

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class Snippet(BaseModel):
    id: int
    topics: list[str]


class Categorization(BaseModel):
    snippets: list[Snippet]


client = instructor.from_openai(OpenAI(api_key=st.secrets["OPENAI_API_KEY"]))


def fetch_links(page, user_id):
    """Fetches a single page of links."""
    response = requests.get(f"{API_BASE_URL}/users/{user_id}/links?page={page}")
    if response.status_code == 200:
        data = response.json()["userSaved"]
        if not data:
            return None  # None will signal no more data
        return data
    else:
        logger.error(f"Failed to fetch links for page {page}: {response.status_code}")
        return None


def fetch_links_multiprocessing(user_id):
    """Fetches all links from the API using multiprocessing."""
    result = []
    max_workers = PARALLEL_WORKER_COUNT

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Start with an initial set of pages
        future_to_page = {
            executor.submit(fetch_links, page, user_id): page
            for page in range(max_workers)
        }
        next_page = max_workers  # The next page number to fetch

        while future_to_page:
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    data = future.result()
                    if data is None:
                        # No more data, remove from the map
                        del future_to_page[future]
                        continue
                    result.extend(data)
                    # Submit the next page in sequence
                    future_to_page[executor.submit(fetch_links, next_page, user_id)] = (
                        next_page
                    )
                    next_page += 1
                except Exception as exc:
                    logger.error(f"Page {page} generated an exception: {exc}")
                # Remove the future that has completed
                del future_to_page[future]

    st.toast(f"Fetched {len(result)} links with topics")
    return result


def fetch_links_without_topics(user_id):
    """Fetches all links from the API"""
    response = requests.get(f"{API_BASE_URL}/users/{user_id}/searchLinks")
    if response.status_code == 200:
        result = response.json()["links"]
        logger.info(f"Fetched {len(result)} links")
        return result
    else:
        logger.error(f"Failed to fetch links: {response.status_code}")
        return []


def fetch_topics(user_id):
    """Fetches all topics from the API"""
    response = requests.get(f"{API_BASE_URL}/user/topics?uid={user_id}")
    if response.status_code == 200:
        return response.json()["topics"]
    else:
        logger.error(f"Failed to fetch topics: {response.status_code}")
        return []


def categorize_text(texts, topics) -> Categorization:
    """Uses OpenAI to classify multiple texts in a single API call by comparing with existing topics, expects structured output"""

    prompt = f"""
      You are a very knowledgeable assistant who's an expert at summarizing text into categories based on the context given to you.
      Given the following topics: {topics}, categorize each of the snippet to 1 or multiple tags based on each snippet's details.

      Keep in mind
      - If there are existing topics already provided, retain it in the final result.
      - Favor existing topics if possible as we do not want to create multiple similar ones.
      - You are allowed to create a new topic if and only if existing input topics do not fit.
      - At most 3 topics can be assigned to each snippet.

      Result
      - Each snippet MUST have at least 1 topic.
      - Only return the snippets that have new or updates topics

      Please list the results in a python array format to be used for post-processing:
      [(id, [topic1, topic2]), (id, [topic])]

      Snippets
      `
      {texts}
      `
    """

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        response_model=Categorization,
    )
    return response


def update_link(link_id, topics, token):
    """Updates the topics associated with a specific link."""
    response = requests.put(
        f"{API_BASE_URL}/links/{link_id}/topics",
        json={"topics": topics},
        headers={
            "Content-Type": "application/json",
            "Authorization": token,
        },
    )

    if response.status_code == 200:
        logger.info("Topics updated successfully.")
        return response.json()
    else:
        logger.error(f"Failed to update topics: {response.status_code}")
        return None


def process(user_id, empty_links=True, progress=None):
    links = fetch_links_multiprocessing(user_id)[:50]
    if empty_links:
        links = [link for link in links if not link.get("topics")]

    topics = fetch_topics(user_id)
    existing_topics = [topic["topic"] for topic in topics]
    current_topics = set(existing_topics)

    progress.progress(0.1, text="Calling OpenAI to categorize your links")

    link_details_dict = {}
    hallucination_count = 0
    total_batches = (len(links) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(links), BATCH_SIZE):
        if progress and i != 0:
            progress_value = i // BATCH_SIZE / total_batches
            progress.progress(
                progress_value, text="Calling OpenAI to categorize your links"
            )

        st.toast(
            f"Processing batch {i//BATCH_SIZE + 1} of {len(links)//BATCH_SIZE + 1}"
        )
        batch_links = links[i : i + BATCH_SIZE]
        link_details = [
            {
                "id": link["id"],
                "url": link["link"],
                "title": link["title"],
                "snippet": link["snippet"],
                "topics": link.get("topics", []),
            }
            for link in batch_links
        ]
        for detail in link_details:
            link_details_dict[detail["id"]] = detail

        suggested_topics = categorize_text(link_details, list(current_topics))
        for snippet in suggested_topics.snippets:
            try:
                link_details_dict[snippet.id]["topics"] = snippet.topics
                current_topics.update(snippet.topics)
            except:
                hallucination_count += 1
                logger.error(f"Model hallucinating - total {hallucination_count}")

    if progress:
        progress.progress(1.0)

    result = list(link_details_dict.values())
    return result
