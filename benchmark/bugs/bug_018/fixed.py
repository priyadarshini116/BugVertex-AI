def fetch(client, url):
    return client.get(url, timeout=5)
