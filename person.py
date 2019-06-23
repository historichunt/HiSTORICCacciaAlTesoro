# coding=utf-8

from google.appengine.ext import ndb
from geo import geomodel

import utility
from utility import convertToUtfIfNeeded

# ------------------------
# TMP_VARIABLES NAMES
# ------------------------
VAR_LAST_KEYBOARD = 'last_keyboard'
VAR_LAST_STATE = 'last_state'
VAR_CURSOR = 'cursor' # [position (1-based), total]

class Person(geomodel.GeoModel, ndb.Model): #ndb.Expando
    chat_id = ndb.StringProperty()
    name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    application = ndb.StringProperty() # 'telegram', 'messenger'
    username = ndb.StringProperty()
    last_mod = ndb.DateTimeProperty(auto_now=True)
    state = ndb.StringProperty()
    enabled = ndb.BooleanProperty(default=True)
    current_hunt = ndb.StringProperty()

    # location = ndb.GeoPtProperty() # inherited from geomodel.GeoModel
    latitude = ndb.ComputedProperty(lambda self: self.location.lat if self.location else None)
    longitude = ndb.ComputedProperty(lambda self: self.location.lon if self.location else None)

    tmp_variables = ndb.PickleProperty()

    def getId(self):
        return self.key.id()

    def updateUserInfo(self, name, last_name, username):
        modified, was_disabled = False, False
        if self.getFirstName() != name:
            self.name = name
            modified = True
        if self.getLastName() != last_name:
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

    def isAdmin(self):
        import key
        return self.getId() in key.ADMIN_IDS

    def isTester(self):
        import key
        return self.getId() in key.TESTER_IDS

    def isTelegramUser(self):
        return self.application == 'telegram'

    def getPropertyUtfMarkdown(self, property, escapeMarkdown=True):
        if property == None:
            return None
        result = convertToUtfIfNeeded(property)
        if escapeMarkdown:
            result = utility.escapeMarkdown(result)
        return result

    def getFirstName(self, escapeMarkdown=True):
        return self.getPropertyUtfMarkdown(self.name, escapeMarkdown=escapeMarkdown)

    def getLastName(self, escapeMarkdown=True):
        return self.getPropertyUtfMarkdown(self.last_name, escapeMarkdown=escapeMarkdown)

    def getUsername(self, escapeMarkdown=True):
        return self.getPropertyUtfMarkdown(self.username, escapeMarkdown=escapeMarkdown)

    def getFirstNameLastName(self, escapeMarkdown=True):
        if self.last_name == None:
            return self.getFirstName(escapeMarkdown=escapeMarkdown)
        return self.getFirstName(escapeMarkdown=escapeMarkdown) + \
               ' ' + self.getLastName(escapeMarkdown=escapeMarkdown)

    def getState(self):
        return self.getPropertyUtfMarkdown(self.state, escapeMarkdown=False)


    def getFirstNameLastNameUserName(self, escapeMarkdown=True):
        result = self.getFirstName(escapeMarkdown =escapeMarkdown)
        if self.last_name:
            result += ' ' + self.getLastName(escapeMarkdown = escapeMarkdown)
        if self.username:
            result += ' @' + self.getUsername(escapeMarkdown = escapeMarkdown)
        return result

    def setEnabled(self, enabled, put=False):
        self.enabled = enabled
        if put:
            self.put()

    def setState(self, newstate, put=True):
        self.state = newstate
        if put:
            self.put()

    def setLastKeyboard(self, kb, put=True):
        self.setTmpVariable(VAR_LAST_KEYBOARD, value=kb, put=put)

    def getLastKeyboard(self):
        return self.getTmpVariable(VAR_LAST_KEYBOARD)

    def setLastState(self, state, put=False):
        self.setTmpVariable(VAR_LAST_STATE, value=state, put=put)

    def getLastState(self):
        return self.getTmpVariable(VAR_LAST_STATE)

    def resetTmpVariable(self):
        self.tmp_variables = {}

    def setTmpVariable(self, var_name, value, put=False):
        self.tmp_variables[var_name] = value
        if put:
            self.put()

    def getTmpVariable(self, var_name, initValue=None):
        if var_name in self.tmp_variables:
            return self.tmp_variables[var_name]
        self.tmp_variables[var_name] = initValue
        return initValue

    def setLocation(self, lat, lon, put=False):
        self.location = ndb.GeoPt(lat, lon)
        self.update_location()
        if put:
            self.put()

    def decreaseCursor(self):
        cursor = self.getTmpVariable(VAR_CURSOR)
        cursor[0] -= 1
        if cursor[0] == -1:
            cursor[0] = cursor[1] - 1 # restart from end

    def increaseCursor(self):
        cursor = self.getTmpVariable(VAR_CURSOR)
        cursor[0] += 1
        if cursor[0] == cursor[1]:
            cursor[0] = 0 # restart from zero


def getId(chat_id, application):
    return 'F_{}'.format(chat_id) if application=='messenger' else 'T_{}'.format(chat_id)

def getPersonById(id):
    return Person.get_by_id(id)

def getPersonByChatIdAndApplication(chat_id, application):
    id = getId(chat_id, application)
    return Person.get_by_id(id)

def getPeopleOnHuntStats(hunt):
    import game
    people_on_hunt = Person.query(Person.current_hunt==hunt).fetch()    
    stats = '\n'.join([game.get_game_stats(p) for p in people_on_hunt if p.tmp_variables['GROUP_NAME']])    
    return stats


def addPerson(chat_id, name, last_name, username, application):
    p = Person(
        id=getId(chat_id, application),
        chat_id=chat_id,
        name=name,
        last_name=last_name,
        username=username,
        application=application,
        tmp_variables={}
    )
    p.put()
    return p

def addHiStoricGroup():
    import key
    p = Person(
        id = key.HISTORIC_GROUP_ID,
        chat_id = key.HISTORIC_GROUP_CHAT_ID,
        name = 'hiSTORIC Trento Group',
        last_name = '',
        username = '',
        application = 'telegram',
        tmp_variables = {}
    )
    p.put()
    return p

def deletePerson(chat_id, application):
    p = getPersonByChatIdAndApplication(chat_id, application)
    p.key.delete()

def getPeopleCount():
    cursor = None
    more = True
    total = 0
    while more:
        keys, cursor, more = Person.query().fetch_page(1000, start_cursor=cursor, keys_only=True)
        total += len(keys)
    return total

# to remove property change temporaryly the model to ndb.Expando
# see https://cloud.google.com/appengine/articles/update_schema#removing-deleted-properties-from-the-datastore

def deletePeople():
    more, cursor = True, None
    to_delete = []
    while more:
        keys, cursor, more = Person.query().fetch_page(1000, start_cursor=cursor, keys_only=True)
        for k in keys:
            if not k.id().startswith('T'):
                to_delete.append(k)
    if to_delete:
        print('Deleting {} entities'.format(len(to_delete)))
        create_futures = ndb.delete_multi_async(to_delete)
        ndb.Future.wait_all(create_futures)
