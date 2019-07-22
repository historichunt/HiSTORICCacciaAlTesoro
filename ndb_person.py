from google.cloud import datastore
import datetime
from google.cloud import ndb #https://googleapis.github.io/python-ndb/latest/
from ndb_utils import client_context
import utility

class Person(ndb.Model):
    chat_id = ndb.StringProperty()
    name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    application = ndb.StringProperty() # 'telegram', 'messenger'
    username = ndb.StringProperty()
    last_mod = ndb.DateTimeProperty(auto_now=True)
    state = ndb.StringProperty()
    enabled = ndb.BooleanProperty(default=True)
    current_hunt = ndb.StringProperty()
    latitude = ndb.FloatProperty()
    longitude = ndb.FloatProperty()
    tmp_variables = ndb.JsonProperty(indexed=False)
  
    def update_info(self, name, last_name, username):
        modified, was_disabled = False, False
        if self.get_first_name() != name:
            self.name = name
            modified = True
        if self.get_last_name() != last_name:
            self.last_name = last_name
            modified = True
        if self.username != username:
            self.username = username
            modified = True
        if not self.enabled:
            self.enabled = True
            modified = True
            was_disabled = True
        if modified:
            self.put()
        return modified, was_disabled

    def get_id(self):
        return self.key.id()

    def is_admin(self):
        import key
        return self.get_id() in key.ADMIN_IDS

    def is_tester(self):
        import key
        return self.get_id() in key.TESTER_IDS

    def get_first_name(self, escape_markdown=True):
        return utility.escape_markdown(self.name) if escape_markdown else self.name

    def get_last_name(self, escape_markdown=True):
        if self.last_name is None:
            return None
        return utility.escape_markdown(self.last_name) if escape_markdown else self.name

    def get_username(self, escape_markdown=True):
        if self.username is None:
            return None
        return utility.escape_markdown(self.username) if escape_markdown else self.name

    def get_first_last_name(self, escape_markdown=True):
        if self.last_name is None:
            return self.get_first_name(escape_markdown)
        return self.get_first_name(escape_markdown) + ' ' + self.get_last_name(escape_markdown)

    def get_first_last_username(self, escape_markdown=True):
        result = self.get_first_last_name(escape_markdown)
        if self.username:
            result += ' @' + self.get_username(escape_markdown)
        return result

    def get_state(self):
        return self.state

    def set_enabled(self, enabled, put=False):
        self.enabled = enabled
        if put:
            self.put()

    def set_state(self, newstate, put=True):
        self.state = newstate
        if put:
            self.put()

    def set_location(self, lat, lon, put=True):
        self.latitude = lat
        self.longitude = lon
        if put: self.put()

    def set_keyboard(self, kb, put=True):
        self.set_tmp_variable("keyboard", value=kb, put=put)

    def get_keyboard(self):
        return self.get_tmp_variable("keyboard")

    def reset_tmp_variables(self):
        self.tmp_variables = {}

    def set_tmp_variable(self, var_name, value, put=False):
        self.tmp_variables[var_name] = value
        if put: self.put()

    def get_tmp_variable(self, var_name, initValue=None):
        if var_name in self.tmp_variables:
            return self.tmp_variables[var_name]
        self.tmp_variables[var_name] = initValue
        return initValue

    def switch_notifications(self):
        self.enabled = not self.enabled
        self.put()

def make_id(chat_id, application):
    return 'F_{}'.format(chat_id) if application=='messenger' else 'T_{}'.format(chat_id)

def get_person_by_id_and_application(chat_id, application):
    uid = make_id(chat_id, application)
    return Person.get_by_id(uid)

def get_person_by_id(uid):
    #k = ndb.Key(Person, uid)
    #return k.get()
    return Person.get_by_id(uid)

def add_person(chat_id, name, last_name, username, application):
    p = Person(
        id=make_id(chat_id, application),
        chat_id=str(chat_id),
        name=name,
        last_name=last_name,
        username=username,
        application=application,
        tmp_variables={}
    )
    p.put()
    return p

@client_context
def get_people_count():
    cursor = None
    more = True
    total = 0
    while more:
        keys, cursor, more = Person.query().fetch_page(1000, start_cursor=cursor, keys_only=True)
        total += len(keys)
    return total

def get_people_on_hunt_stats(hunt):
    import game
    people_on_hunt = Person.query(Person.current_hunt==hunt).fetch()    
    stats = '\n'.join([game.get_game_stats(p) for p in people_on_hunt if p.tmp_variables['GROUP_NAME']])    
    return stats
