from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageOps, UnidentifiedImageError
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import AzureError, ResourceExistsError
from fastapi import HTTPException
from backend.config import settings


def sanitize(data):
    if len(data) > settings().max_photo_bytes:
        raise HTTPException(413, 'La foto no debe exceder 8 MB.')
    try:
        with Image.open(BytesIO(data)) as source:
            if source.format not in ('JPEG', 'PNG', 'WEBP') or source.width * source.height > 24_000_000:
                raise ValueError()
            image = ImageOps.exif_transpose(source).convert('RGB')
            image.thumbnail((1600, 1600))
            # Una imagen nueva elimina EXIF, perfiles y metadatos de posicion.
            clean = Image.new('RGB', image.size)
            clean.paste(image)
            output = BytesIO()
            clean.save(output, format='JPEG', quality=85)
            return output.getvalue()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, 'Imagen inválida. Usa JPEG, PNG o WebP de hasta 24 megapíxeles.')


def container():
    if not settings().azure_blob_connection_string:
        raise HTTPException(503, 'El almacenamiento de fotografías no está disponible. Puedes continuar sin foto o reintentar después.')
    return BlobServiceClient.from_connection_string(settings().azure_blob_connection_string).get_container_client(settings().azure_blob_container)


def upload(data):
    name = str(uuid4()) + '.jpg'
    try:
        client = container()
        try:
            client.create_container()
        except ResourceExistsError:
            pass
        client.upload_blob(name, data, content_settings=ContentSettings(content_type='image/jpeg'), overwrite=False)
        return name
    except AzureError:
        raise HTTPException(502, 'No se pudo guardar la fotografía. El reporte permanece registrado.')


def download(name):
    try:
        return container().download_blob(name).readall()
    except AzureError:
        raise HTTPException(502, 'No se pudo consultar la fotografía.')
