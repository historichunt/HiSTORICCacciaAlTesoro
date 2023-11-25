import logging
import traceback
import telegram
import time
from historic.bot.bot_telegram import report_admins

def exception_reporter(func, *args, **kwargs):    
    async def exception_reporter_wrapper(*args, **kwargs):
        try:
            await func(*args, **kwargs)
        except Exception:            
            report_string = '❗️ Exception {}'.format(traceback.format_exc()) #.splitlines()
            logging.error(report_string) 
            try:  
                await report_admins(report_string)
            except Exception:
                report_string = '❗️ Exception {}'.format(traceback.format_exc())
                logging.error(report_string)          
    return exception_reporter_wrapper

# see https://github.com/python-telegram-bot/python-telegram-bot/wiki/Exception-Handling

def retry_on_network_error(func):
    async def retry_on_network_error_wrapper(*args, **kwargs):
        for retry_num in range(1, 5):
            try:
                return func(*args, **kwargs)
            except telegram.error.NetworkError:
                sleep_secs = pow(2,retry_num)
                report_string = '⚠️️ Caught network error, on {} attemp. Retrying after {} secs...'.format(retry_num,sleep_secs)
                logging.warning(report_string)                 
                await report_admins(report_string)
                time.sleep(sleep_secs)
        report_string = '❗️ Exception: persistent network error'
        logging.error(report_string)            
        await report_admins(report_string)            
    return retry_on_network_error_wrapper