# coding=utf-8
import logging
import webapp2
import requests
import key
import jsonUtil

def prepareAndGetPhotoTelegramUrl(file_id):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(60)
    r = requests.post(key.TELEGRAM_API_URL + 'getFile', data={'file_id': file_id})
    r_json = jsonUtil.json_loads_byteified(r.content)
    r_result = r_json['result']
    file_path = r_result['file_path']
    url = key.TELEGRAM_BASE_URL_FILE + file_path
    return url


class DownloadPhotoHandler(webapp2.RequestHandler):
    def get(self, file_id):
        from google.appengine.api import urlfetch
        urlfetch.set_default_fetch_deadline(60)
        logging.debug("retrieving picture with file id: " + file_id)
        r = requests.post(key.TELEGRAM_API_URL + 'getFile', data={'file_id': file_id})
        r_json = jsonUtil.json_loads_byteified(r.content)
        logging.debug("r_json: {}".format(r_json))
        r_result = r_json['result']
        file_path = r_result['file_path']
        extension = file_path[-3:]
        file_size = r_result['file_size']
        urlFile = key.TELEGRAM_BASE_URL_FILE + file_path
        logging.debug("Url file: " + urlFile)
        photo_data = requests.get(urlFile).content
        self.response.headers['Content-Type'] = 'image / ' + extension
        self.response.headers['Content-Length'] = str(file_size)
        self.response.out.write(photo_data)
