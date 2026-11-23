import base64
import os
import requests
import configparser

config = configparser.ConfigParser()
config.read(os.path.join(f"{os.path.dirname(__file__)}", "..", "config_info", "config.ini"))
token = config["GITHUB.INTERACTION"]["token"]

headers = {"Authorization": "token " + token, "Content-Type": "application/json"}


def open_graph_ql_query_file(filename: str):
    with open(os.path.join(f"{os.path.dirname(__file__)}", "graph_ql_queries", filename), "r") as f:
        output = f.read()
    return output


def run_query(
    query: str,
):  # A simple function to use requests.post to make the API call. Note the json= section.
    request = requests.post(
        "https://api.github.com/graphql", json={"query": query}, headers=headers
    )
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(
            "Query failed to run by returning code of {}. {}".format(request.status_code, query)
        )


def get_contents_of_file_in_repo(
    repo_owner: str,
    repo_name: str,
    file_path: str,
    branch: str = "main",
):
    # Use this to just get the text content of a file in the code area of a repo, based on
    # https://stackoverflow.com/questions/51239168/how-to-download-single-file-from-a-git-repository-using-python
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}?ref={branch}"
    response = requests.get(url, headers=headers)
    content = f"No PRs found in {repo_owner}/{repo_name}"
    # Check if the request was successful
    if response.status_code == 200:
        # Get the content data from the response
        content_data = response.json()
        # Extract the content and decode it from base64
        content_base64 = content_data.get("content")
        content_bytes = base64.b64decode(content_base64)
        content = content_bytes.decode("utf-8")
    return content
