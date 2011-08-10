from bbs import *

def main():
  # delete all mail
  #for msg in listmsgs():
  #  delmsg (msg)

  # write everyone mail
  #for u in listusers():
    m = Msg(handle())
    m.recipient = None
    m.subject = 'Welcome!'
    m.body = 'Welcome to the new prsv messaging system, ' \
             'this is the first message ever sent, you are ' \
             'very luck to have recieved it! Regardless, ' \
             'Please enjoy the new upcoming messaging system.\n\n' \
             'I have many new features planned, many of which are ' \
             'implemented fully in the skeleton, but need just a ' \
             'UI for control. Firstly, I have abolished the concept ' \
             'of message areas, confrences, and bases. I never really ' \
             'understood them, and those are for archiac systems with ' \
             'record and memory limits! Phooey!\n\n' \
             'I have implemented the more modern concept of \'tags\' ' \
             'you may be familiar with tags from facebook, flickr, gmail ' \
             'etc. I am most familiar with them as they were implemented in ' \
             'lotus notes, as I was a lotus notes programmer for several ' \
             'years.\n\n' \
             'I look forward to seeing more messages. Thank you for those ' \
             'of you who login regularly, you often help me find bugs (I ' \
             'may or may not be watching you right now!).'
    m.tags = ['general announcements']
    m.send ()
    #addmsg (m)
