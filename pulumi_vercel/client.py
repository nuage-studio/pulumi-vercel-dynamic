from urllib.parse import urlencode
import requests

VERCEL_API = "https://api.vercel.com"


class VercelError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return f"{self.code}: {self.message}"


def query(
    route: str,
    method: str,
    api_token: str,
    query_parameters: dict | None = None,
    body_parameters: dict | None = None,
):
    url = f"{VERCEL_API}/{route}"

    if query_parameters:
        querystring = urlencode(query_parameters)
        url = f"{url}?{querystring}"

    response = requests.request(
        url=url,
        method=method,
        json=body_parameters,
        headers={"Authorization": f"Bearer {api_token}"},
    )

    try:
        response_data = response.json()
    except requests.JSONDecodeError as e:
        e.add_note(response.text)
        raise e

    if "error" in response_data:
        raise VercelError(
            code=response_data["error"]["code"],
            message=response_data["error"]["message"],
        )

    return response_data
