from session import getsession

def delay(n):
    getsession().oflush()
    getsession().read_event([], seconds)

def oflush():
    return getsession().oflush()

def echo(data):
    return getsession().write(data)

