from services import vk_upload


def enabled() -> bool:
    return vk_upload.enabled()


def get(filepath: str) -> str:
    return vk_upload.get(filepath)


def store(filepath: str, attachment: str) -> None:
    vk_upload.store(filepath, attachment)


def invalidate_by_attachment(attachment: str):
    return vk_upload.invalidate_by_attachment(attachment)


def attachment_rejected(err) -> bool:
    return vk_upload.attachment_rejected(err)


def clear() -> None:
    vk_upload.clear()
