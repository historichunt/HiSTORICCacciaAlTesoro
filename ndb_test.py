from google.cloud import ndb

client = ndb.Client()

class Test(ndb.Model):
    name = ndb.StringProperty()
  

def test(input_name):    
    print('Adding {}'.format(input_name))
    with client.context():
        t = Test(
            name=input_name,             
        )        
        t.put()        
    print('Added {}'.format(input_name))

if __name__ == "__main__":
    import threading
    threading.Thread(target=test, args=['John']).start()
    threading.Thread(target=test, args=['Bob']).start()