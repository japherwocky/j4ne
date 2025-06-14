import os
from dotenv import load_dotenv
from networks import Network
from square import client

# Load environment variables
load_dotenv()

# Get Square API credentials from environment
square_appid = os.getenv('SQUARE_APPID', '')
square_token = os.getenv('SQUARE_TOKEN', '')

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
