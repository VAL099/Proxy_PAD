from fastapi import FastAPI, Response, Header

import redis, roundrobin, requests, json
import const, handlers, models

# redis://default:mcoRxOEHZGjuBsnx7WZVcny9vmqHeAoW@redis-11222.c2.eu-west-1-3.ec2.cloud.redislabs.com:11222
cache_service = redis.Redis(host = 'redis-11222.c2.eu-west-1-3.ec2.cloud.redislabs.com', port = 11222, db = 0, password = 'mcoRxOEHZGjuBsnx7WZVcny9vmqHeAoW')

sessions = {}
attr_server = roundrobin.basic([const.S1, const.S2]) # load balancer using round robin algorithm

gateway = FastAPI()

@gateway.get('/w')
def welcome():
    return {'msg':'Proxy is ALIVE!'}

@gateway.get('/auth')
async def authorization():
    user_token = handlers.generate_token()
    sessions.update({user_token:attr_server()})
    print(sessions)
    return Response(content = user_token, status_code = 200)

@gateway.post('/')
async def solve_request(request_model: models.ProxyRequest, authorisation_token:str = Header()):
    if authorisation_token in sessions:
        ssu = sessions[authorisation_token] # server serving this user

        # handle GET requests
        if request_model.type == 'GET':
            
            # get all adverts
            if request_model.content == 'ALL':
                if request_model.content in cache_service: # means 'ALL'
                    resp = handlers.caching(cs = cache_service, op = 'req', k = request_model.content)
                    print('FROM REDIS!')    
                    return json.loads(resp.decode().replace("'",'"'))  
                else:
                    r = requests.get(url = f'{ssu}/adv/all', headers = {'authorisation-token':const.AUTH_TOKEN} )
                    for record in r.json():
                        handlers.caching(cs = cache_service, op = 'load', k = record['id'], v = json.dumps(record).encode())
                    handlers.caching(cs = cache_service, op = 'load', k = 'ALL', v = str(r.json()))
                    return r.json()
            # get all categories
            elif request_model.content == 'categories':
                if request_model.content in cache_service:
                    resp = handlers.caching(cs = cache_service, op = 'req', k = request_model.content)
                    print('FROM REDIS!')
                    return json.loads(resp.decode().replace("'",'"'))  
                else:
                    r = requests.get(url = f'{ssu}/adv/categories', headers = {'authorisation-token':const.AUTH_TOKEN} )
                    handlers.caching(cs = cache_service, op = 'load', k = 'categories', v = str(r.json()))
                    return r.json()
            
            # get all adverts from a specific category
            if isinstance(request_model.content, dict):
                r = requests.get(url = f'{ssu}/adv/category',
                                headers = {'authorisation-token':const.AUTH_TOKEN}, params = {'c':request_model.content['category']} )
                return r.json()
            
            # get an advert by id
            else:
                if request_model.content in cache_service:
                    resp = handlers.caching(cs = cache_service, op = 'req', k = request_model.content)
                    print('FROM REDIS!')
                    return json.loads(resp.decode().replace("'",'"'))  
                else:
                    r = requests.get(url = f'{ssu}/adv/id',
                                    headers = {'authorisation-token':const.AUTH_TOKEN}, params = {'adv_id':request_model.content})
                    handlers.caching(cs = cache_service, op = 'load', k = request_model.content, v = r.json())
                    return r.json()
        
        # handle POST requests
        elif request_model.type == 'POST':
            r = requests.post(url = f'{ssu}/adv/post',
                            headers = {'authorisation-token':const.AUTH_TOKEN}, json = request_model.content)
            handlers.bd_sync(rt = 'POST', master = ssu, payload = request_model.content) # sync DB
            # cache_service.delete('ALL') # resete caching when request == GET all
            return Response(status_code = r.status_code)

        # handle PATCH requests
        elif request_model.type == 'PATCH':
            r = requests.patch(url = f'{ssu}/adv/patch', headers = {'authorisation-token':const.AUTH_TOKEN}, 
                                json = request_model.content, params = {'adv_id':request_model.content['id']})
            handlers.bd_sync(rt = 'PATCH', master = ssu, payload = request_model.content) # sync DB
            cache_service.delete('ALL') # resete caching when request == GET all
            return Response(status_code = r.status_code)

        # handle DELETE requests
        elif request_model.type == 'DELETE':
            r = requests.delete(url = f'{ssu}/adv/rm',
                                headers = {'authorisation-token':const.AUTH_TOKEN}, params = {'adv_id':request_model.content})
            handlers.bd_sync(rt = 'DELETE', master = ssu, payload = request_model.content) # sync DB
            cache_service.delete('ALL') # resete caching when request == GET all
            cache_service.delete(request_model.content) # resete caching when request == GET all
            return Response(status_code = r.status_code)