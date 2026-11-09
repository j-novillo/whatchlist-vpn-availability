"""Read and replace the plain text of the snapshot Google Doc."""

from watchlist_enricher.textutil import normalize_note_text


def extract_plain_text(document: dict) -> str:
    chunks: list[str] = []
    for element in (document.get("body") or {}).get("content") or []:
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for part in paragraph.get("elements") or []:
            run = part.get("textRun")
            if run and isinstance(run.get("content"), str):
                chunks.append(run["content"])
    return normalize_note_text("".join(chunks))


def document_end_index(document: dict) -> int:
    content = (document.get("body") or {}).get("content") or []
    if not content:
        return 1
    return int(content[-1].get("endIndex") or 1)


def build_replace_requests(end_index: int, new_text: str) -> list[dict]:
    """BatchUpdate requests that replace the document body.

    The Docs API keeps a trailing newline, so the delete range stops one
    before ``end_index``. An empty document (end index 1 or 2) is insert-only.
    """

    requests: list[dict] = []
    delete_end = end_index - 1
    if delete_end > 1:
        requests.append(
            {
                "deleteContentRange": {
                    "range": {"startIndex": 1, "endIndex": delete_end},
                }
            }
        )
    if new_text == "":
        return requests
    payload = new_text if new_text.endswith("\n") else new_text + "\n"
    requests.append({"insertText": {"location": {"index": 1}, "text": payload}})
    return requests


def build_docs_service(credentials):
    from googleapiclient.discovery import build

    return build("docs", "v1", credentials=credentials, cache_discovery=False)


class GoogleDocsSnapshot:
    def __init__(self, service, document_id: str):
        self._service = service
        self._document_id = document_id

    def read(self) -> str:
        document = self._service.documents().get(documentId=self._document_id).execute()
        return extract_plain_text(document)

    def write(self, text: str) -> None:
        document = self._service.documents().get(documentId=self._document_id).execute()
        requests = build_replace_requests(document_end_index(document), text)
        if not requests:
            return
        self._service.documents().batchUpdate(
            documentId=self._document_id,
            body={"requests": requests},
        ).execute()


class FileSnapshot:
    def __init__(self, path):
        from pathlib import Path

        self.path = Path(path)

    def read(self) -> str:
        if not self.path.exists():
            return ""
        return self.path.read_text(encoding="utf-8")

    def write(self, text: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = text if text.endswith("\n") or text == "" else text + "\n"
        self.path.write_text(payload, encoding="utf-8")
