from google.cloud import ndb
from historic.bot.ndb_utils import client_context

class EnvVar(ndb.Model):
  name = ndb.StringProperty()
  version = ndb.StringProperty() # test, production
  value = ndb.StringProperty()
  
def get_env_var(name, version):
    NOT_SET_VALUE = "NOT SET"
    retval = EnvVar.query(
        EnvVar.name == name, 
        EnvVar.version == version
    ).get()
    if not retval:
        retval = EnvVar()
        retval.name = name
        retval.value = NOT_SET_VALUE
        retval.put()
    if retval.value == NOT_SET_VALUE:
        raise Exception(('Setting %s not found in the database. A placeholder ' +
        'record has been created. Go to the Developers Console for your app ' +
        'in App Engine, look up the EnvVar record with name=%s and enter ' +
        'its value in that record\'s value field.') % (name, name))
    return retval.value

@client_context
def set_all(versions):
    from dotenv import dotenv_values
    new_envvars = []
    for version in versions:
        dotenv_file = f'.env_{version}'
        vars_values = dotenv_values(dotenv_file)
        for name,value in vars_values.items():
            new_envvars.append(
                EnvVar(
                    name=name, 
                    version=version, 
                    value=value
                )
            )
        ndb.put_multi(new_envvars)

@client_context
def delete_all():
    ndb.delete_multi(
        EnvVar.query().fetch(keys_only=True)
    )

@client_context
def get_all(version):    
    envvars = EnvVar.query(
        EnvVar.version == version
    ).fetch()    
    return {ev.name:ev.value for ev in envvars}
    

def print_all():
    for version in ['test', 'production']:
        print(version)
        envvars = get_all(version)
        for name,value in envvars.items():
            print(f'{name} -> {value}')
        print()

if __name__ == "__main__":
    #TODO use settings.LOCAL_ENV_FILES
    # delete_all()
    set_all(['fede', 'test', 'production', 'oist'])
    # set_all(['fede'])
    # print_all()