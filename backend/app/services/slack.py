import requests


def post_slack_message(webhook_url: str, text: str) -> None:
    response = requests.post(webhook_url, json={"text": text}, timeout=10)
    response.raise_for_status()
