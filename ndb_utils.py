from google.cloud import ndb #https://googleapis.github.io/python-ndb/latest/

client = ndb.Client()

def client_context(func, *args, **kwargs):
    def client_context_wrapper(*args, **kwargs):
        with client.context():
            return func(*args, **kwargs)
    return client_context_wrapper
