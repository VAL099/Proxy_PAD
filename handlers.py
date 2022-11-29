import string, random, base64
import const
import requests

def generate_token():
    ch = (string.ascii_letters + string.digits + string.punctuation)*10
    return base64.b64encode( ''.join(random.choice(ch) for x in range(100)).encode() ).decode()

def caching(**kwargs):
    if kwargs.get('op') == 'load':
        kwargs.get('cs').set(kwargs.get('k'), kwargs.get('v'))
        kwargs.get('cs').expire(kwargs.get('k'), 3600) # expiration time = 1 hour
        return 'Cached!'
    elif kwargs.get('op') == 'req':
        return kwargs.get('cs').get(kwargs.get('k'))

def bd_sync(**kwargs):

    master = kwargs.get('master')
    payload = kwargs.get('payload')
    rt = kwargs.get('rt') 
    
    m_s = {const.S1:const.S2, const.S2:const.S1} # master-slave relation

    if rt == 'POST':
        r = requests.post(url = f'http://host.docker.internal:{m_s.get(master)}/adv/post',
                            headers = {'authorisation-token':const.AUTH_TOKEN}, json = payload)
    elif rt == 'PATCH':
        r = requests.patch(url = f'http://host.docker.internal:{m_s.get(master)}/adv/patch', headers = {'authorisation-token':const.AUTH_TOKEN}, 
                                json = payload, params = {'adv_id':payload['id']})
    elif rt == 'DELETE':
        r = requests.delete(url = f'http://host.docker.internal:{m_s.get(master)}/adv/rm',
                                headers = {'authorisation-token':const.AUTH_TOKEN}, params = {'adv_id':payload})