import logging
import traceback
import telegram
import time
from bot.bot_telegram import report_master

def exception_reporter(func, *args, **kwargs):    
    def exception_reporter_wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:            
            report_string = '❗️ Exception {}'.format(traceback.format_exc()) #.splitlines()
            logging.error(report_string) 
            try:  
                report_master(report_string)
            except Exception:
                report_string = '❗️ Exception {}'.format(traceback.format_exc())
                logging.error(report_string)          
    return exception_reporter_wrapper

def run_new_thread_and_report_exception(func, *args, **kwargs):
    import threading   

    @exception_reporter
    def report_exception_in_thread(func, *args, **kwargs):
        func(*args,  **kwargs)

    args= list(args)
    args.insert(0, func)
    threading.Thread(target=report_exception_in_thread, args=args, kwargs=kwargs).start()

# see https://github.com/python-telegram-bot/python-telegram-bot/wiki/Exception-Handling

def retry_on_network_error(func):
    def retry_on_network_error_wrapper(*args, **kwargs):
        for retry_num in range(1, 5):
            try:
                return func(*args, **kwargs)
            except telegram.error.NetworkError:
                sleep_secs = pow(2,retry_num)
                report_string = '⚠️️ Caught network error, on {} attemp. Retrying after {} secs...'.format(retry_num,sleep_secs)
                logging.warning(report_string)                 
                report_master(report_string)
                time.sleep(sleep_secs)
        report_string = '❗️ Exception: persistent network error'
        logging.error(report_string)            
        report_master(report_string)            
    return retry_on_network_error_wrapper