class BaseServer(object):
    '''
    Base class for server implementations.
    '''

    #: Maximum number of clients
    MAX_CONNECTIONS = 100

    #: Number of clients that can wait to be accepted
    LISTEN_BACKLOG = 5

    #: Dictionary of environment variables received by negotiation
    env = {}

    #: Client factory should be a class defining what should be instantiated
    #: for the client instance.
    client_factory = None

    #: Dictionary of active clients, (file descriptor, Client, ...)
    clients = {}

    #: Connect factory should be a class, derived from threading.Thread, that
    #: should be instantiated on-connect to perform negotiation and launch the
    #: bbs session upon success.
    connect_factory = None

    #: List of on-connect negotiating threads.
    threads = []

    @classmethod
    def client_factory_kwargs(cls, instance):
        """
        Keyword arguments for the client_factory.

        A dictionary may be substituted.
        The default return value is an empty dictionary.
        """
        return dict()

    @classmethod
    def connect_factory_kwargs(cls, instance):
        """
        Keyword arguments for the connect_factory.

        A dictionary may be substituted.
        The default return value is an empty dictionary.
        """
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

    def client_fds(self):
        """
        Returns a list of client file descriptors.
        """
        return [client.fileno() for client in self.clients.values()]

    def clients_ready(self, ready_fds=None):
        """
        Return a list of clients with data ready to be receive.

        :type ready_fds: list
        :param ready_fds: file descriptors already known to be ready
        """
        if ready_fds is None:
            # given no file descriptors, we must iterate them all by hand.
            return [client for client in self.clients.values()
                    if client.recv_ready()]

        # given a list of ready_fds pairs, we return only clients with
        # matching file descriptors.
        return [client for client in self.clients.values()
                if client.fileno() in ready_fds]
