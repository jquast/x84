class BaseServer(object):
    '''
    Base class for server implementations.
    '''

    ## Maximum number of clients
    MAX_CONNECTIONS = 100

    ## Number of clients that can wait to be accepted
    LISTEN_BACKLOG = 5

    ## Dictionary of active clients, (file descriptor, Client, ...)
    clients = {}

    ## Dictionary of environment variables received by negotiation
    env = {}

    ## Factories to be used by the engine
    client_factory = None
    connect_factory = None

    ## The classmethods below can be replaced by a dictionary attribute if
    ## that's more convenient

    @classmethod
    def client_factory_kwargs(cls, instance):
        return dict()

    @classmethod
    def connect_factory_kwargs(cls, instance):
        return dict()

    def client_count(self):
        """
        Returns the number of active connections.
        """
        return len(self.clients)

    def client_list(self):
        """
        Returns a list of connected clients.
        """
        return self.clients.values()
