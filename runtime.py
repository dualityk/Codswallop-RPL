
# CODSWALLOP RPL (a zen garden)
# #####################################################
# Runtime

# This module includes popular features such as the ability
# to execute RPL code and manipulate the named store.

from trivia import *
from rtypes import typedir, typelst, typerem, typeint, typestr, typetag

# Interpreter flags and stuff, easier to have in its own namespace.
class rplruntime:
  def __init__(self, types):
    # Types object.  These can be shared between instances.
    self.Types = types

    # Some helpful type constants.
    self.symtypes = [self.Types.id['Symbol'], self.Types.id['Function']]
    self.dirtype = self.Types.id['Directory']
    
    # Error state.  The caller string is generally set by builtins, and
    # the error flag is generally only set when errorcont is true.
    self.Error = False
    self.Caller = ''

    # If true, errorcont won't stop a running program for errors.  Instead,
    # errors (other than parse errors) will be muted and the Error flag will
    # be set, along with the name of the offending function.
    self.Errorcont = False
    
    # Traceback depth, can be changed to keep the error handler out of the weeds.
    self.Tracedepth = 0

    # Calls is the call stack, Stack is the stack stack.
    self.Calls = []
    self.Stack = typelst([])
    
    # rs() will single step if SST is True.
    self.SST = False
    
    # Catch sigints with a bit more aplomb.
    self.Break = False
    self.dieanyway = False
    
    # Let sigints drop to single stepping instead of tracing back.
    self.BreakSST = False
    
    # An empty tag used as filler in directories.
    self.nulltag=typetag('', typerem('NIL'))
    
    # Make the self-referencing last entry for the named store.
    self.lastobj=typedir(self.nulltag, None)
    
    # Now that we have lastobj, we can make our firstobj.
    self.firstglobalobj = self.firstdir()
    self.firstobj = self.firstglobalobj

    # And for our opening act, populate our types within the named store.
    types.updatestore(self)


  # Runtime error handler.  If a traceback routine exists, called ERRTRACE,
  # it will call it with this frame:
  # Line 3: Caller string
  # Line 2: Reason string
  # Line 1: Call stack in the form of { { Code, IP } .. }
  # If ERRTRACE doesn't exist, execution will still stop, leaving the user
  # perplexed and mystified by the stack's contents.
  def ded(self, reason):
    self.Break = False
    if self.Errorcont:
      # If errors are being suppressed, just silently raise the error flag.
      self.Error = True
    else:
      # Otherwise, trace back but don't set the error flag, just the last call,
      # and clear SST so it's less confusing.
      self.Error = False
      self.SST = False
      
      # Let's make a core dump!
      self.Stack.push(typestr(self.Caller))
      self.Stack.push(typestr(reason))
      core = typelst()
      
      # Don't trace back deeper than our REPL.
      for i in self.Calls[self.Tracedepth:]:
        core.push(typelst([i[CALL_CODE], typeint(i[CALL_IP]-1)]))
      self.Stack.push(core)
        
      # ... and don't kill past it either.
      if len(self.Calls)>self.Tracedepth:
        # Reset our first object pointer and unwind back as far as we should.
        if len(self.Calls):
          self.firstobj = self.Calls[len(self.Calls)-1][CALL_CONTEXT]
        else:
          self.firstobj = self.firstglobalobj
      self.Calls = self.Calls[0:self.Tracedepth]
      
      # Try to evaluate ERRTRACE to print our traceback and error message.
      tracer = self.rcl(['ERRTRACE'])
      if tracer is not None: tracer.eval(self)

  # Code execution routine.  Basically, evaluating a program to the call stack
  # will cause execution to begin, and each object therein is evaluated (using
  # 'program rules'); if it's the last element, the program is dropped from
  # the call stack afterward.  If the last element is a new program, it will
  # push itself to the call stack.  The instruction pointer is maintained on
  # the call stack so reentrant routines are fine.  Each stack line is in the
  # form of [ip, object, first-named-object].

  # If single stepping is activated, it will try to call STEP with the frame:
  # Line 2: Stack depth as integer
  # Line 1: Object just evaluated 
  
  # rs = run/stop, in HP tradition.
  def rs(self):
    # Every time through, use retcall to see if there are more things
    # to evaluate.  It'll return False as soon as the call stack is empty.
    while self.retcall():
      # Fetch next object from current clutches.
      line = self.Calls[len(self.Calls)-1]
      nextobj = line[CALL_CODE].data[line[CALL_IP]]
      nexteval = nextobj.rteval

      # Increment IP for this context.
      line[CALL_IP] += 1
      
      # If we're in debug mode, call STEP after each thing we actually
      # evaluate; otherwise, just evaluate.
      if self.SST:
        # First we have to see if there even is a single stepper.
        ourstepper = self.rcl(['STEP'])
        
        # Then we click one forward.
        self.evalone(nexteval)
        
        # Now see if we're still single stepping.
        if self.SST and ourstepper != None:
          # And we clear SST so the single stepper can run unimpeded;
          # it'll set SST again on its own if it wants to keep stepping.
          self.SST = False
          self.Stack.push(typeint(len(self.Calls)))
          self.Stack.push(nextobj)
          ourstepper.eval(self)
        else:
          # Silently return to quick evaluation if there's no STEP.
          self.SST = False
      else:      
        # Some objects want to evaluate each other.  Instead of recursing,
        # they'll return the next object they want evaluated, and it'll be
        # taken care of in this loop.  This keeps us out of the Python call
        # stack somewhat and makes it possible for the user to break out of
        # certain corners they may creatively paint themselves into.
        while nexteval is not None:
          nexteval = nexteval(self)
          
          # Make sure we didn't die.  If we did, at least stop hitting ourselves.
          if self.Break:
            nexteval = None
            if self.BreakSST:
              self.SST = True
              self.Break = False
            else:
              self.Caller = 'a higher power'
              self.ded('Break')

  # Evaluate one thing until it returns None. rs()' single stepper uses this,
  # and it's identical to the free-running runtime above.  It might be useful
  # for internals in the future.  Thing should be object.eval or object.rteval.
  def evalone(self, thing):
    while thing is not None:
      thing = thing(self)
      if self.Break:
        nexteval = None
        if self.BreakSST:
          self.SST = True
          self.Break = False
        else:
          self.Caller = 'a higher power'
          self.ded('Break')


  # Queue a new context.  This will add a line to the call stack unless there
  # is a tail call to optimize.
  def newcall(self, obj):
      # Check to see if we're tail calling and replace instead of push if so.
      # This will retain the local variable context.
      spot = len(self.Calls)-1
      if len(self.Calls) and self.Calls[spot][CALL_IP] == len(self.Calls[spot][CALL_CODE].data):
        # When replacing a call, just replace the program and reset the IP.
        self.Calls[spot][CALL_IP] = 0
        self.Calls[spot][CALL_CODE] = obj
      else:
        if spot < CALLDEPTH:
          self.Calls.append([0, obj, self.firstobj])
        else:
          self.ded('You asked for '+str(CALLDEPTH)+' recursions and not a penny more')

  # New call with locals.
  def newlocall(self, obj, names):
      # Check to see if we're tail calling and replace instead of push if so.
      # This will retain the local variable context.
      spot = len(self.Calls)-1
      self.firstobj = self.firstdir(names)
      if len(self.Calls) and self.Calls[spot][CALL_IP] == len(self.Calls[spot][CALL_CODE].data):
        # When replacing a call, just reset the IP and update our directory.
        self.Calls[spot][CALL_IP] = 0
        self.Calls[spot][CALL_CODE] = obj      
        self.Calls[spot][CALL_CONTEXT] = self.firstobj
      else:
        if spot < CALLDEPTH:
          # When adding a call, make a new first directory object
          # and update our firstobj pointer.
          self.firstobj = self.firstdir(names)
          self.Calls.append([0, obj, self.firstobj])
        else:
          self.ded('You asked for '+str(CALLDEPTH)+' recursions and not a penny more')

  # Return until there is a context with stuff left in it (or nothing left).
  def retcall(self):
    if len(self.Calls):
      # If we're at the end of the list, drop it.  
      line = self.Calls[len(self.Calls)-1]
      if line[CALL_IP] == len(line[CALL_CODE].data):
        self.Calls.pop()
        # Update our first object pointer and see if we're done.
        if len(self.Calls):
          self.firstobj = self.Calls[len(self.Calls)-1][CALL_CONTEXT]
        else:
          # Call stack is empty, definitely done.
          self.firstobj = self.firstglobalobj
          return False
      return True
    else:
      # Call stack is empty, we're definitely done.
      return False


  # #####################################################
  # Hierarchical named store routines.

  # Prepare a new first directory entry.  Only one lastobj is required, but
  # first entries are all unique.
  def firstdir(self, obj=None):
    if obj == None:
      obj = self.lastobj
    # Nulltag is a null-named tag containing a null remark.
    return typedir(self.nulltag, obj)
  
  # Try to find an object.
  def rcl(self, namelist):
    # Start from the top.
    current = self.firstobj
    for i in namelist:
      # Make sure we're about to parade through an actual directory first.
      if current.typenum == self.dirtype:
        # Start the parade, and return nothing if we didn't find a match.
        while current.tag.name != i:
         current = current.next
         if current is self.lastobj:
           return
        # If we got here, we did find a match, so return the object in it.
        current = current.tag.obj
      else:
        return
    return current

  # Modified rcl, deref, which returns the tag and not the obj.
  def deref(self, namelist):
    # Start from the top.
    current = self.firstobj
    for i in range(len(namelist)):
      # Make sure we're about to parade through an actual directory first.
      if current.typenum == self.dirtype:
        # Start the parade, and return nothing if we didn't find a match.
        while current.tag.name != namelist[i]:
         current = current.next
         if current is self.lastobj:
           return
        # If we got here, we did find a match, so return the object in it.
        if i+1 == len(namelist):
          return current.tag
        else:
          current = current.tag.obj
      else:
        return

  # Try to store an object.
  def sto(self, namelist, value):
    # Counter
    counter = len(namelist)-1
    # Start from the top.
    current = self.firstobj
    for i in namelist:
      # Make sure we're about to parade through an actual directory first.
      if current.typenum == self.dirtype:
        # Start the parade.
        while current.tag.name != i:
          if current.next is self.lastobj:
            # If we failed to find a subdirectory somewhere, cheese it.
            if counter:
              return False
            # But if we got to the end of our name list, append a new entry.
            else:
              current.next = typedir(typetag(namelist[len(namelist)-1], value), self.lastobj)
              return True
          current = current.next
        # If we got here, we found a match, so decrement our counter.
        # But don't return the object unless we're still chasing down the tree.
        if counter:
          counter -= 1
          current = current.tag.obj
      # Walked out of the directory tree?  That's a big fat False.
      else:
        return False
    # If we got down here, we found an extant entry to update.
    current.tag.obj = value
    return True


  # Rummage through an already-stored directory tree and see if any symbols 
  # within it circulate.
  def circdir(self, dirtop):
    def recurse(prefix, dirtop):
      dirtop = dirtop.next
      while dirtop is not self.lastobj:
        # If we find a symbol, return true if circsym says it circulates.
        if dirtop.tag.obj.typenum in self.symtypes:
          if self.circsym(prefix+dirtop.tag.obj.data):
            return True
        # And if we find another directory, recurse and return true if
        # something further down the line claims to circulate.
        elif dirtop.tag.obj.typenum == self.dirtype:
          if recurse(prefix+[dirtop.tag.name], dirtop.tag.obj):
            return True
        dirtop = dirtop.next
      # After traversing the whole list, if we didn't return True before, we
      # made it.  
      return False
    return recurse([], dirtop)
    
  # Check if an already-stored item circulates.
  def circsym(self, proposedname):
    # Recall a symbol.
    names = [proposedname]
    symbol = self.rcl(proposedname)

    while True:
      if symbol == None:
        # If the thing our thing points to is nonexistent, no circulation.
        return False
      # If the object we recalled is a symbol, we'll check for circulation
      # and loop.  If we got to a non-symbolic object, there is no problem.
      if symbol.typenum in self.symtypes:
        # If the thing our thing points to is in this chain, something
        # is circulating, even if it isn't what we're storing.
        if symbol.data in names:
          return True
        else:
          names += [symbol.data]
          symbol = self.rcl(symbol.data)
      else:
        return False

  def rm(self, namelist):
    # Start from the top.
    current = self.firstobj
    for i in namelist:
      # Make sure we're about to parade through an actual directory first.
      # We also exempt empty directories here.
      if current.typenum == self.dirtype and \
         current.next is not self.lastobj:
        # Start the parade, and return False if we didn't find a match.
        # We check the next link's name to a) skip the null-named firstdir
        # and b) hang onto the current link to update its nextobj.
        while current.next.tag.name != i:
         current = current.next
         if current.next is self.lastobj:
           return False
        # If we got here, we did find a match, so return the object in it,
        # but keep our last link for the final event.
        last = current
        current = current.next.tag.obj
      else:
        return False
    # And if we got here, we don't care much about what the current object is;
    # we're just going to pop it out of the chain.
    last.next = last.next.next
    return True
