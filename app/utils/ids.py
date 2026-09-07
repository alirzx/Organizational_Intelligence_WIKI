from uuid import uuid4


def new_request_id() -> str:
    return f"req_{uuid4().hex}"


def new_object_id(prefix: str = "obj") -> str:
    return f"{prefix}_{uuid4().hex}"


def default_page_id(document_id: str, page_number: int) -> str:
    return f"{document_id}:p{page_number}"
