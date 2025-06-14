from env_keys import square_appid, square_token
from networks import Network
from square import client

class Squore(Network):
    """ subclass to handle connecting to the Square API """

    async def connect(self):
        C = client.Client(
            access_token=square_token,
            environment='production'
            )

        query = {}
        query['query'] = {}
        query['location_ids'] = ['EF60J7T0T6SJZ',]
        query['return_entries'] = True

        query['query']['filter'] = {'state_filter':{}}
        query['query']['filter']['state_filter']['states'] = ['COMPLETED']

        query['query']['sort'] = {}
        query['query']['sort']['sort_field'] = 'CLOSED_AT' 
        query['query']['sort']['sort_order'] = 'DESC'

        result = C.orders.search_orders(query)
        import pdb;pdb.set_trace()
