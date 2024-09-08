import requests
from google.cloud import storage
from airtable import Airtable
from historic.config import settings
from historic.bot import airtable_utils
from historic.config.params import (
    GOOGLE_BUCKET_NAME, MEDIA_FIELDS_MISSIONS, MEDIA_FIELDS_INSTRUCTIONS
)

'''
Main utils function to write full table media to bucket
'''
async def upload_table_media_on_bucket(bucket, game_id,
    hunt_name, table_name, media_fields_list, overwrite):

    table_with_media = Airtable(game_id, table_name, api_key=settings.AIRTABLE_ACCESS_TOKEN)
    table_rows = airtable_utils.get_rows(table_with_media)

    await upload_rows_media_on_bucket(
        bucket,
        hunt_name,
        table_rows,
        media_fields_list,
        overwrite
    )

'''
Main utils function to write to bucket table rows to bucket
This is actually replacing the media_field airtable url to bucket
'''
async def upload_rows_media_on_bucket(bucket, hunt_name, table_rows,
    media_fields_list, overwrite):

    for row in table_rows:
        for field in media_fields_list:
            if field in row:
                media_field = row[field][0]
                url = media_field['url']
                filename = media_field['filename']
                blob = bucket.blob(f'{hunt_name}/{filename}')

                # this is where url is updated on local data structure
                # even if overwrite is False
                media_field['url'] = blob.public_url

                # if overwrite is False do not overwrite bucket data
                if blob.exists() and not overwrite:
                    continue

                request_response = requests.get(url, stream=True)
                content_type = request_response.headers['content-type']
                media_content = request_response.content
                blob.upload_from_string(media_content, content_type=content_type)


'''
This is called manually via the Admin interface
This is useful to do when enforcing rewriting of files with the same name
In fact, the method `upload_missions_media_to_bucket` which runs every time a mission is built, does not rewrite files on bucket which already exist (by default).
'''
async def update_all_hunt_media_to_bucket(hunt_name, hunt_pw, overwrite):

    from historic.bot.game import get_game_id_from_pw, get_hunt_languages

    storage_client = storage.Client()
    bucket = storage_client.bucket(GOOGLE_BUCKET_NAME)
    game_id = get_game_id_from_pw(hunt_pw)
    hunt_languages = get_hunt_languages(hunt_pw)

    # upload to bucket media in Misioni_LANG
    for l in hunt_languages:
        await upload_table_media_on_bucket(
            bucket=bucket,
            game_id=game_id,
            hunt_name=hunt_name,
            table_name = f'Missioni_{l}',
            media_fields_list = MEDIA_FIELDS_MISSIONS,
            overwrite=overwrite
        )

    # upload to bucket media in Instructions_LANG
    for l in hunt_languages:
        await upload_table_media_on_bucket(
            bucket=bucket,
            game_id=game_id,
            hunt_name=hunt_name,
            table_name = f'Instructions_{l}',
            media_fields_list = MEDIA_FIELDS_INSTRUCTIONS,
            overwrite=overwrite
        )

    return True

'''
This is called every time a mission is built
'''
async def upload_missions_media_to_bucket(hunt_name, missions, overwrite):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GOOGLE_BUCKET_NAME)

    await upload_rows_media_on_bucket(
        bucket=bucket,
        hunt_name=hunt_name,
        table_rows=missions,
        media_fields_list=MEDIA_FIELDS_MISSIONS,
        overwrite=overwrite
    )

    return True

'''
This is called every time a mission is built
'''
async def upload_instructions_media_to_bucket(game_id, hunt_name, lang, overwrite):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GOOGLE_BUCKET_NAME)

    await upload_table_media_on_bucket(
        bucket=bucket,
        game_id=game_id,
        hunt_name=hunt_name,
        table_name = f'Instructions_{lang}',
        media_fields_list = MEDIA_FIELDS_INSTRUCTIONS,
        overwrite=overwrite
    )

    return True