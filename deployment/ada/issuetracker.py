# -*- coding: utf-8 -*-

def ticket(command=None, resource=None, value=None, comment=None, verbose=False):
    ''' update a ticket via cmdline, see fab ticket:help
    
usage: fab ticket:command [,resource [,value [,comment [,verbose]]]]
    
commands:
 * <empty>|my          # "fab ticket" show all tickets where you are the owner
 * get|show,ticketid   # "fab ticket:show,123" shows ticket 123 
 * ed[it],ticketid     # "fab ticket:ed,123" edits ticket 123

 * eta|rt|remain,ticketid,3  
   # "fab ticket:eta,123,3" set the remaining time(estimated arival) to 3 hours
 
 * ack|accept,ticketid   
   # eg. fab ticket:ack,123 accepts ticket 123, which sets owner to user
   
 * cl[ose],ticketid[,fixed|invalid|wontfix|duplicate|worksforme]
   # User Stories & Bugs are set to 'testing' automagically,
   # override with resolution='fixed|invalid|wontfix|duplicate|worksforme'
   # default resolution for everything else is fixed
   # "fab ticket:cl,123,invalid" closes ticket 123, sets resolution to invalid
   
 * rop|reopen,ticketid  # "fab ticket:rop,123" reopen ticket 123 if possible
 
resource, value, comment, verbose can be used via named variables, 
    eg. "fab ticket:eta,23,3,verbose=True"
    '''
    import sys, os
    
    from fabric.utils import abort
    from deployment.utils import get_homedir, fabdir, import_from
    from deployment.utils import strbool as _strb
    
    from auth import ADAauth
    
    # FIXME it seems without a PYTHON_PATH set we cant import from ecs...
    sys.path.append(fabdir())
    from ecs.utils import tracrpc

    if command in ['help']:
        print(ticket.__doc__)
        return
    
    verbose = _strb(verbose)
    tracauth = ADAauth()
    tracauth.search_paths.append(get_homedir())
    tracauth.search_paths.append(os.path.join(fabdir(), ".hg"))
    tracauth.get_credentials()
    bot = tracrpc.TracRpc(tracauth.credentials[0]['username'], tracauth.credentials[0]['password'], "https", "ecsdev.ep3.at", "/project/ecs")
    
    if command in [None, 'my']:
        bot.show_ticket_report(tracauth.credentials[0]['username'], verbose)
    elif command in ['get', 'show']:
        bot.show_ticket(int(resource), verbose)
    elif command in ['ed', 'edit']:
        bot.edit_ticket(int(resource), comment)
    elif command in ['eta', 'rt', 'remain']:
        bot.update_remaining_time(int(resource), value, comment)
    elif command in ['ack', 'accept']:
        bot.accept_ticket(int(resource), comment)
    elif command in ['cl', 'close']:
        bot.close_ticket(int(resource), resolution=value, comment=comment)
    elif command in ['rop', 'reopen']:
        bot.reopen_ticket(int(resource), comment=comment)
    elif command in ['act', 'actions']:
        bot.show_actions(int(resource), verbose)
    elif command in ['crt', 'create']:
        bot.create_ticket(verbose=verbose)
    elif command in ['feedbackreport', 'fbr']:
        query_base = "order=id&col=id&col=summary&col=status&col=type&col=priority&col=milestone&col=component"
        query = query_base + "&type=idea&type=question&type=problem&type=praise"
        bot.show_ticket_report(query=query, verbose=verbose)
    elif command in ['deletefeedbackreport']:
        return
        
        #THIS is only for cleanup before the sprint release
        #actual delete has to be commented in in tracrpc
        from fabric.contrib import console
        from time import sleep
        query_base = "order=id&col=id&col=summary&col=status&col=type&col=priority&col=milestone&col=component"
        query = query_base + "&type=idea&type=question&type=problem&type=praise"
        
        bot.show_ticket_report(query=query, verbose=verbose)
        question = "Do you really want to delete all these tickets?"
        if console.confirm(question, default=False):
            allowed = False
            allowed,query = bot.delete_tickets_by_query(query=query, verbose=verbose)
            if allowed:
                print "Are you really really sure?"
                print "THINK...!"
                sleep(15)
                question = "Still sure?"
                if console.confirm(question, default=False):
                    bot.delete_tickets_by_query(query=query, verbose=verbose, doublecheck=allowed)
                    
    elif command in ['query', 'q']:
        bot.show_ticket_report(query=resource, verbose=verbose)
    else:
        abort("unknown command %s, see fab ticket:help for help" % command)
