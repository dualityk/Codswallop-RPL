
# CODSWALLOP RPL (a zen garden)
# #####################################################
# Internals

# This file contains something analogous to SysRPL functions.  They are
# just anonymous Python functions that receive the runtime as an argument,
# do what they gotta do, and return.  makebinprocs() builds a list of them,
# and stoprocs stores the list into a directory in a runtime's named store.

# The business of turning these internal functions into builtins, with 
# their user-level safety of argument checking and so forth, is done at boot
# with builtins.rpl.

from trivia import *
import rtypes, parse

import time, random, copy

# Windows doesn't include readline for some stupid reason
try:
  import readline
except:
  print("\n** Windows scrubs don't get nice editing keys **\n")


# Build a list of anonymous functions, each entry being [name, function].

# No, it is not ironic or contradictory for functions to be both named
# and anonymous.
def makebinprocs():
  bins = []
   
  ### Temporaries
  # Count up firstobjs in named store.
  def x(rt):
    nam = rt.firstobj
    count = 0
    while nam is not rt.lastobj:
      if not len(nam.tag.name):
        count += 1
      nam = nam.next
    rt.Stack.push(rtypes.typeint(count))
  bins += [['firsts', x]]
  

  ### Documentation  
  
  # List of global names,
  def x(rt):
    n = rtypes.typelst()
    nam = rt.firstobj.next
    while nam is not rt.lastobj:
      if len(nam.tag.name):
        n.push(rtypes.typeunq([nam.tag.name]))
      nam = nam.next
    rt.Stack.push(n)
  bins += [['names', x]]

  # List of names in a directory.
  def x(rt):
    n = rtypes.typelst()
    nam = rt.Stack.pop().next
    while nam != rt.lastobj:
      n.push(rtypes.typeunq([nam.tag.name]))
      nam = nam.next
    rt.Stack.push(n)
  bins += [['dir', x]]
  
  # Online help.
  def x(rt):
    sym = rt.Stack.pop()
    obj = rt.rcl(sym.data)
    if obj:
      obj.doc(rt)
    else:
      rt.Stack.push(sym)
      rt.ded('Nonexistent symbols have nonexistent documentation')
  bins += [['doc', x]]
  
  # Object type.
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().typenum))
  bins += [['type', x]]
  
  # Introspect
  def x(rt):
    if len(rt.Calls):
      rt.Stack.push(rt.Calls[len(rt.Calls)-1][CALL_CODE])
    else:
      rt.ded('You asked for context but there is none')
  bins += [['self', x]]
  
  
  ### Input/Output
  
  # Display.
  def x(rt):
    print(rt.Stack.pop().disp())
  bins += [['disp', x]]
  
  # Display;.
  def x(rt):
    print(rt.Stack.pop().disp(), end="")
  bins += [['dispn', x]]

  # Console input.
  def x(rt):
    rt.dieanyway = True
    x = rt.Stack.pop()
    try:
      rt.Stack.push(rtypes.typestr(input(x.data)))
    except:
      rt.Stack.push(x)
      rt.ded('The user has typed unforgivably')
    rt.dieanyway = False
  bins += [['prompt', x]]
  
  # Time.
  def x(rt):
    rt.Stack.push(rtypes.typefloat(time.time()))
  bins += [['epoch', x]]
 
 
  ### Stack manipulation
  
  # Return whole stack.
  def x(rt):
    rt.Stack.push(rt.Stack.dup())
  bins += [['stack', x]]
  
  # Drop line 1.
  def x(rt):
    rt.Stack.pop()
  bins += [['drop', x]]
  
  # Clear stacks.
  def x(rt):
    rt.Stack.data=[]
    rt.Calls = rt.Calls[0:rt.Tracedepth]
  bins += [['clr', x]]
  
  # Evaluate.
  def x(rt):
    rt.Stack.pop().eval(rt)
  bins += [['eval', x]]
  
  # Swap.
  def x(rt):
    x = rt.Stack.pop()
    y = rt.Stack.pop()
    rt.Stack.push(x)
    rt.Stack.push(y)
  bins += [['swap', x]]
  
  # Duplicate.
  def x(rt):
    x = rt.Stack.pop()
    rt.Stack.push(x)
    rt.Stack.push(x)
  bins += [['dup', x]]
  
  ### Disk store
  # Write object to disk.
  def x(rt):
    name = rt.Stack.pop()
    thing = rt.Stack.pop()
    try:
      with open(name.data, 'w') as file:
        if thing.typenum == rt.Types.id['Symbol']: 
          printable = rt.rcl(thing.data).unparse(maxdepth=-1)+" "+thing.unparse()+" STO\n"
        else:
          # Maxdepth of -1 ensures full recursion.
          printable = thing.unparse(maxdepth=-1)+'\n'
        file.write(printable)
        file.close()
    except:
      rt.Stack.push(thing)
      rt.ded('Whatever your plan was, it has failed to materialize')  
  bins += [['>dsk', x]]

  # Parse and evaluate from disk.
  def x(rt):
    name = rt.Stack.pop()
    try:
      with open(name.data, 'r') as file:
        text = file.read(MAXREAD)
        obj = parse.parse(rt, text)
        if obj == None:
          rt.ded('The parser did not care for your shenanigans')
        else:
          rtypes.typecode(obj).eval(rt)
    except:
      rt.Stack.push(name)
      rt.ded('The operating system says no')
  bins += [['dsk>', x]]
  

  ### Named storage
  # Recall symbol.
  def x(rt):
    sym = rt.Stack.pop()
    obj = rt.rcl(sym.data)
    if obj == None:
      rt.Stack.push(sym)
      rt.ded("What even is "+sym.unparse())
    else:
      rt.Stack.push(obj)
  bins += [['rcl', x]]
  
  # Pull object out of tag.
  def x(rt):
    tag = rt.Stack.pop()
    rt.Stack.push(tag.obj)
  bins += [['rclfrom', x]]
  
  # Store symbol.
  def x(rt):
    def usded(og, one, two, reason):
      rt.Stack.push(one)
      rt.Stack.push(two)
      # To unwind a failed store, we need to either write the original object
      # back to an extant name, or erase the name we added.
      if og != None:
        rt.sto(two.data, og)
      else:
        rt.rm(two.data)
      rt.ded(reason)

    name = rt.Stack.pop()
    obj = rt.Stack.pop()
    og = rt.rcl(name.data)

    # First try to store the object.  If that doesn't work, there was a
    # directory traverse failure.
    if not rt.sto(name.data, obj):
      usded(None,obj,name,'To store to a directory, first the directory must exist')
    else:
      # Now, if the thing we just stored is a directory, make sure it didn't
      # contain anything circulatory:
      if obj.typenum == rt.Types.id['Directory'] and rt.circdir(obj):
        usded(og,obj,name,'That directory contains circular references')
      elif obj.typenum in rt.symtypes and rt.circsym(obj.data):
        usded(og,obj,name,'cDonalds Theorem does not apply to symbolic references')
  bins += [['sto', x]]

  # Put object into tag.
  def x(rt):
    tag = rt.Stack.pop()
    thing = rt.Stack.pop()
    if thing.typenum in rt.symtypes:
      original = tag.obj
      tag.obj = thing
      if rt.circsym(thing.data):
        tag.obj = original
        rt.Stack.push(thing)
        rt.Stack.push(tag)
        rt.ded('A valiant effort to reference oneself, thwarted')
    else:
      tag.obj = thing
  bins += [['stoto', x]]
  
  # Dereference.
  def x(rt):
    sym = rt.Stack.pop()
    obj = rt.deref(sym.data)
    if obj == None:
      rt.Stack.push(sym)
      rt.ded('It is difficult to dereference what does not exist')
    else:
      rt.Stack.push(obj)        
  bins += [['deref', x]]

  # Does it exist?
  def x(rt):
    sym = rt.Stack.pop()
    if rt.rcl(sym.data) is None:
      rt.Stack.push(rtypes.typeint(0))
    else:
      rt.Stack.push(rtypes.typeint(1))
  bins += [['exists', x]]
  
  # Erase name.
  def x(rt):
    x=rt.Stack.pop()
    if not rt.rm(x.data):
      rt.Stack.push(x)
      rt.ded("You have failed to erase what isn't here!")
  bins += [['rm', x]]
  
  # Local variable context.
  def x(rt):
    # In case of emergency, pull this lever and return.
    def usded(reason):
      rt.firstobj = firstob
      rt.Stack.data = origstack
      rt.ded(reason)
      
    # Hang onto our whole stack and our current firstobj in case of errors.
    origstack = rt.Stack.data[:]
    firstob = rt.firstobj
        
    names = rt.Stack.pop().data
    prog = rt.Stack.pop()
    nextob = rt.firstobj
    
    dirtype = rt.Types.id['Directory']
    tagtype = rt.Types.id['Tag']
    symtypes = [rt.Types.id['Symbol'], rt.Types.id['Function']]
    
    for i in names:
      if i.typenum in symtypes:
        # If it's a symbol, verify it's a valid one.
        if len(i.data)>1:
          usded("Ain't no dots in local variable names")
          return
        # Try popping an object off the stack and assigning it to a name.
        thisob = rt.Stack.pop()
        if thisob is not None:
          nextob = rtypes.typedir(rtypes.typetag(i.data[0], thisob), nextob)
          circname = i.data
        else:
          usded('You gotta have '+str(len(names))+' things on the stack!')
          return
      elif i.typenum == tagtype:
        circname = [i.name]
        nextob = rtypes.typedir(i.dup(), nextob)
      else:
        usded("Only symbols and tags lead to success")
      # Check for circular references as we go.
      if nextob.tag.obj.typenum in symtypes:
        rt.firstobj = nextob
        if rt.circsym(circname):
          usded('Round and round the '+i.unparse()+' bush the '+
                i.unparse()+' chased the '+i.unparse())
          return
      elif nextob.tag.obj.typenum==dirtype:
        rt.firstobj = nextob
        if rt.circdir(nextob.tag.obj):
          usded('This directory circulates if you put it there')
          return
    # And queue a new local variable context.
    rt.newlocall(prog, nextob)
  bins += [['local', x]]
  
  
  ### Flow control
  # SST
  def x(rt):
    rt.SST = True
  bins += [['sst', x]]

  # No SST
  def x(rt):
    rt.SST = False
  bins += [['sstoff', x]]
  
  # Bail (pop one off the call stack)
  def x(rt):
    rt.retcall()
    if len(rt.Calls): rt.Calls.pop()
  bins += [['bail', x]]

  # BEVAL: bail and evaluate (goto)
  def x(rt):
    rt.retcall()
    if len(rt.Calls):
      rt.Calls.pop()
    rt.Stack.pop().eval(rt)
  bins += [['beval', x]]

  # If-then
  def x(rt):
    th = rt.Stack.pop()
    if rt.Stack.pop().data: th.eval(rt)
  bins += [['ift', x]]

  # If-then-else
  def x(rt):
    el = rt.Stack.pop()
    th = rt.Stack.pop()
    if rt.Stack.pop().data: th.eval(rt)
    else: el.eval(rt)
  bins += [['ifte', x]]


  ### Mathemagics
  # Accumulate (not >BIN'd for safety)
  def x(rt):
    x = rt.Stack.pop()
    rt.Stack.data[len(rt.Stack.data)-1].data += x.data
  bins += [['accum', x]]

  # Add
  def x(rt):
    rt.Stack.push(rtypes.typefloat(rt.Stack.pop().data+rt.Stack.pop().data))
  bins += [['+float', x]]
  
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().data+rt.Stack.pop().data))
  bins += [['+int', x]]
  
  def x(rt):
    x = rt.Stack.pop().disp()
    y = rt.Stack.pop().disp()
    rt.Stack.push(rtypes.typestr(y+x))
  bins += [['+str', x]]
  
  def x(rt):
    x = rt.Stack.pop()
    y = rt.Stack.pop().dup()
    y.push(x)
    rt.Stack.push(y)
  bins += [['+list', x]]

  def x(rt):
    x = rt.Stack.pop().data
    y = rt.Stack.pop().data
    rt.Stack.push(rtypes.typecode(y+x))
  bins += [['+code', x]]
 
  # Multiply
  def x(rt):
    rt.Stack.push(rtypes.typefloat(rt.Stack.pop().data*rt.Stack.pop().data))
  bins += [['*float', x]]
  
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().data*rt.Stack.pop().data))
  bins += [['*int', x]]
  
  def x(rt):
    x = rt.Stack.pop()
    y = rt.Stack.pop()
    if x.data >= 0:
      rt.Stack.push(rtypes.typestr(y.data*x.data))
    else:
      rt.Stack.push(y)
      rt.Stack.push(x)
      rt.ded('wat')
  bins += [['*str', x]]
  
  def x(rt):
    x = rt.Stack.pop()
    y = rt.Stack.pop()
    z = rt.Types.prototype[rt.Types.n[y.typenum]]()
    if x.data > 0:
      for i in range(x.data):
        for j in y.data: 
          z.push(j)
      rt.Stack.push(z)
    else:
      rt.Stack.push(y)
      rt.Stack.push(x)
      rt.ded('wat')
  bins += [['*composite', x]]

  # Subtract
  def x(rt):
    rt.Stack.push(rtypes.typefloat(-rt.Stack.pop().data+rt.Stack.pop().data))
  bins += [['-float', x]]
  
  def x(rt):
    rt.Stack.push(rtypes.typeint(-rt.Stack.pop().data+rt.Stack.pop().data))
  bins += [['-int', x]]
 
  # Divide
  def x(rt):
    x = rt.Stack.pop()
    y = rt.Stack.pop()
    if x.data:
      rt.Stack.push(rtypes.typefloat(y.data/x.data))
    else:
      rt.Stack.push(y)
      rt.Stack.push(x)
      rt.ded('Excuse you')
  bins += [['/float', x]]
  
  def x(rt):
    x = rt.Stack.pop()
    y = rt.Stack.pop()
    if x.data:
      rt.Stack.push(rtypes.typeint(y.data/x.data))
    else:
      rt.Stack.push(y)
      rt.Stack.push(x)
      rt.ded('Excuse you')
  bins += [['/int', x]]

  # Negate
  def x(rt):
    num = copy.copy(rt.Stack.pop())
    num.data = -num.data
    rt.Stack.push(num)
  bins += [['neg', x]]
 
  # Random
  def x(rt):
    rt.Stack.push(rtypes.typefloat(random.random()))
  bins += [['rnd', x]]
  
  # Integer portion
  def x(rt):
    rt.Stack.push(rtypes.typefloat(int(rt.Stack.pop().data)))
  bins += [['ip', x]]


  ### Conversions
  # to tag
  def x(rt):
    name = rt.Stack.pop()
    obj = rt.Stack.pop()
    if len(name.data)>1:
      rt.Stack.push(obj)
      rt.Stack.push(name)
      rt.ded("Tags don't have last names")
    else:
      rt.Stack.push(rtypes.typetag(name.data[0],obj))
  bins += [['>tag', x]]
  
  # to builtin
  def x(rt):
    def bailout(table, argct, hint, name):
      rt.Stack.push(table)
      rt.Stack.push(argct)
      rt.Stack.push(hint)
      rt.Stack.push(name)
    newbin = rtypes.typebin()
    newdata = rt.Stack.pop()
    newhint = rt.Stack.pop()
    newargct = rt.Stack.pop()
    patches = rt.Stack.pop()
    newbin.data = newdata.data[0]  # Don't let user get fresh with dotted names
    newbin.hint = newhint.data
    newbin.dispatches = []
    newbin.argct = newargct.data
    newbin.argck = [] 
    if newbin.argct < 0:
      rt.ded("It's hard to win a negative argument")
      bailout(patches, newargct, newhint, newdata)
      return
    # Try to add a new dispatch line for each one the user wants.
    for i in patches.data:
      if i.typenum == rt.Types.id['List']:
        if len(i)>newargct.data:
          # If we're handed an unquoted symbol, try to recall it first.
          if i.data[0].typenum == rt.Types.id['Function'] or i.data[0].typenum == rt.Types.id['Symbol']:
            tryin = rt.rcl(i.data[0].data)
            if tryin is not None:
              newbin.dispatches.append(tryin)
            else:
              newbin.dispatches.append(i.data[0])
          else:
            newbin.dispatches.append(i.data[0])
          argline = []
          for j in range(newbin.argct):
            if i.data[j+1].typenum != rt.Types.id['Integer'] or not i.data[j+1].typenum in rt.Types.id.values():
              bailout(patches, newargct, newhint, newdata)
              rt.ded("Type numbers have to be a number which represents a type")
              return
            else:          
              argline.append(i.data[j+1].data)
          newbin.argck.append(argline)
        else:
          bailout(patches, newargct, newhint, newdata)
          rt.ded("Next time try including the number of arguments you asked for")
          return
      else:
        bailout(patches, newargct, newhint, newdata)
        rt.ded("If you want a built-in, you should consider a less broken dispatch table")
        return
    # If the user sent us a null dispatch table, make it a NOP.
    if not len(newbin.dispatches):
      newbin.dispatches=[newbin.dispatch]
    # Assuming we got this far, we made it:
    rt.Stack.push(newbin)
  bins += [['>bin', x]]
  
  # Break apart a builtin.
  def x(rt):
    ourbin = rt.Stack.pop()
    table = rtypes.typelst([])
    for i in range(len(ourbin.argck)):
      #table.push(rtypes.typelst([ourbin.dispatches[i]]+ourbin.argck[i]))
      line = [ourbin.dispatches[i]]
      for j in range(ourbin.argct):
        line += [rtypes.typeint(ourbin.argck[i][j])]
      table.push(rtypes.typelst(line))
    rt.Stack.push(table)
    rt.Stack.push(rtypes.typeint(ourbin.argct))
    rt.Stack.push(rtypes.typestr(ourbin.hint))
    rt.Stack.push(rtypes.typesym([ourbin.data]))
  bins += [['bin>', x]]

  # Make empty directory
  def x(rt):
    rt.Stack.push(rt.firstdir(rt.lastobj))
  bins += [['mkdir', x]]

  # Number to integer
  def x(rt):
    rt.Stack.push(rtypes.typeint(int(rt.Stack.pop().data)))
  bins += [['num>int', x]]
  
  def x(rt):
    x = rt.Stack.pop()
    try:
      rt.Stack.push(rtypes.typeint(int(x.data)))
    except:
      rt.Stack.push(x)
      rt.ded('That will never be an integer, my friend')
  bins += [['str>int', x]]
  
  # Number to float
  def x(rt):
    rt.Stack.push(rtypes.typefloat(float(rt.Stack.pop().data)))
  bins += [['num>float', x]]
  
  def x(rt):
    x = rt.Stack.pop()
    try:
      rt.Stack.push(rtypes.typefloat(float(x.data)))
    except:
      rt.Stack.push(x)
      rt.ded("Sir/ma'am, this is a Wendy's")
  bins += [['str>float', x]]

  # Basic VAL
  def x(rt):
    x = rt.Stack.pop()
    try:
      rt.Stack.push(rtypes.typefloat(float(x.data)))
    except:
      rt.Stack.push(rtypes.typefloat(0))
  bins += [['basicval', x]]

  # Character to integer.  
  def x(rt):
    string = rt.Stack.pop()
    if len(string.data):
      rt.Stack.push(rtypes.typeint(ord(string.data[0])))
    else:
      rt.Stack.push(string)
      rt.ded('It would be 0 if it was anything at all')
  bins += [['asc>', x]]

  # Integer to character.
  def x(rt):
    string = rt.Stack.pop()
    if string.data >= 0 and string.data < 1114112:
      rt.Stack.push(rtypes.typestr(chr(string.data)))
    else:
      rt.Stack.push(string)
      rt.ded('This number could not possibly be a character')
  bins += [['>asc', x]]
  
  # String to objects.
  def x(rt):
    text = rt.Stack.pop().data
    x = parse.parse(rt, text)
    if x == None:
      rt.Stack.push(rtypes.typestr(text))
      rt.ded('This is no RPL that I can see')
    else:
      for i in x:
        rt.Stack.push(i)
  bins += [['>obj', x]]
  
  # To symbol.
  def x(rt):
    ourstring = rt.Stack.pop()
    if parse.validatename(ourstring.data):
      rt.Stack.push(rtypes.typesym(ourstring.data.split('.')))
    else:
      rt.Stack.push(ourstring)
      rt.ded("This can be a string, but it won't be a symbol")
  bins += [['str>sym', x]]
  
  def x(rt):
    rt.Stack.push(rtypes.typesym(rt.Stack.pop().data))
  bins += [['func>sym', x]]

  # To function.
  def x(rt):
    ourstring = rt.Stack.pop()
    if parse.validatename(ourstring.data):
      rt.Stack.push(rtypes.typeunq(ourstring.data.split('.')))
    else:
      rt.Stack.push(ourstring)
      rt.ded("This can be a string, but it won't be a symbol")
  bins += [['str>func', x]]

  def x(rt):
    rt.Stack.push(rtypes.typeunq(rt.Stack.pop().data))
  bins += [['sym>func', x]]

  # To string.
  def x(rt):
    rt.Stack.push(rtypes.typestr(rt.Stack.pop().unparse(maxdepth=-1)))
  bins += [['>str', x]]
  
  
  ### Comparisons

  # Equality
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().data==rt.Stack.pop().data))
  bins += [['==', x]]

  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().data!=rt.Stack.pop().data))
  bins += [['!=', x]]
  
  # Less than
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().data>rt.Stack.pop().data))
  bins += [['<', x]]

  # Greater than
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().data<rt.Stack.pop().data))
  bins += [['>', x]]

  # Less than or equal to
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().data>=rt.Stack.pop().data))
  bins += [['<=', x]]

  # Greater than or equal to
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Stack.pop().data<=rt.Stack.pop().data))
  bins += [['>=', x]]

  # Logical AND
  def x(rt):
    x = bool(rt.Stack.pop().data)
    y = bool(rt.Stack.pop().data)
    rt.Stack.push(rtypes.typeint(x and y))
  bins += [['and', x]]
  
  # Logical OR
  def x(rt):
    x = bool(rt.Stack.pop().data)
    y = bool(rt.Stack.pop().data)
    rt.Stack.push(rtypes.typeint(x or y))
  bins += [['or', x]]
  
  # Logical NOT
  def x(rt):
    x = bool(rt.Stack.pop().data)
    rt.Stack.push(rtypes.typeint(not x))
  bins += [['not', x]]
  
  
  ### List functions
  # Length of whatever.
  def x(rt):
    rt.Stack.push(rtypes.typeint(len(rt.Stack.pop().data)))
  bins += [['len', x]]
  
  # Pop
  def x(rt):
    list = rt.Stack.pop()
    if len(list.data):
      newlist = list.data[:]
      thing = newlist.pop()
      rt.Stack.push(rtypes.typelst(newlist))
      rt.Stack.push(thing)
    else:
      rt.Stack.push(list)
      rt.ded('Once you pop, you must eventually stop')
  bins += [['pop', x]]
  
  # Break up a composite and stuff.
  def x(rt):
    obj = rt.Stack.pop().data
    for i in obj:
      rt.Stack.push(i)
    rt.Stack.push(rtypes.typeint(len(obj)))
  bins += [['composite>', x]]
  
  def x(rt):
    obj = rt.Stack.pop()
    rt.Stack.push(obj.tag.obj)
    rt.Stack.push(rtypes.typesym([obj.tag.name]))
    rt.Stack.push(obj.next)
  bins += [['dir>', x]]
  
  def x(rt):
    obj = rt.Stack.pop()
    rt.Stack.push(obj.obj)
    rt.Stack.push(rtypes.typesym([obj.name]))
  bins += [['tag>', x]]
  
  # List subset from left
  def x(rt):
    j = rt.Stack.pop().data
    lst = rt.Stack.pop()
    if j >= 0:
      if lst.typenum == rt.Types.id['String']:
        rt.Stack.push(rtypes.typestr(lst.data[:j]))
      else:
        lst = lst.dup()
        lst.data = lst.data[:j]
        rt.Stack.push(lst)
    else:
      rt.Stack.push(lst)
      rt.Stack.push(rtypes.typeint(j))
      rt.ded('Ask at least for zero, maybe more')
  bins += [['left', x]]
  
  # List subset from right
  def x(rt):
    j = rt.Stack.pop().data
    lst = rt.Stack.pop()
    if j >= 0:
      start = len(lst.data)-j
      start *= (start>=0)
      if lst.typenum == rt.Types.id['String']:
        rt.Stack.push(rtypes.typestr(lst.data[start:]))
      else:
        lst = lst.dup()
        lst.data = lst.data[start:]
        rt.Stack.push(lst)
    else:
      rt.Stack.push(lst)
      rt.Stack.push(rtypes.typeint(j))
      rt.ded('Ask at least for zero, maybe more')
  bins += [['right', x]]

  # List subset
  def x(rt):
    j = rt.Stack.pop().data
    i = rt.Stack.pop().data
    lst = rt.Stack.pop()
    if i >= 0 and i < len(lst.data):
      if lst.typenum == rt.Types.id['String']:
        rt.Stack.push(rtypes.typestr(lst.data[i:j+1]))
      else:
        lst = lst.dup()
        lst.data = lst.data[i:j+1]
        rt.Stack.push(lst)
    else:
      rt.Stack.push(lst)
      rt.Stack.push(rtypes.typeint(j))
      rt.Stack.push(rtypes.typeint(i))
      rt.ded('It would help to have a valid starting subscript')
  bins += [['subs', x]]
  
  # Get from list
  def x(rt):
    i = rt.Stack.pop().data
    lst = rt.Stack.pop()
    if i >= 0 and i < len(lst.data):
      if lst.typenum == rt.Types.id['String']:
        rt.Stack.push(rtypes.typestr(lst.data[i]))
      else:
        rt.Stack.push(lst.data[i])
    else:
      rt.Stack.push(lst)
      rt.Stack.push(rtypes.typeint(i))
      rt.ded('This '+lst.typename+' deserves a better subscript')
  bins += [['get', x]]

  # Put to list
  def x(rt):
    i = rt.Stack.pop().data
    obj = rt.Stack.pop()
    lst = rt.Stack.pop()
    if i >= 0 and i < len(lst.data):
      lst = lst.dup()
      lst.data[i]=obj
      rt.Stack.push(lst)
    else:
      rt.Stack.push(lst)
      rt.Stack.push(obj)
      rt.Stack.push(rtypes.typeint(i))
      rt.ded('This '+lst.typename+' deserves a better subscript')
  bins += [['put', x]]
  
  # Make a list or convert code to list.
  def x(rt):
    items = rt.Stack.pop().data
    if len(rt.Stack)<items:
      rt.Stack.push(rtypes.typeint(items))
      rt.ded('If you want '+str(items)+' things in a list, maybe you should have '+str(items)+' things on the stack')
    else:
      lst = rt.Stack.data[len(rt.Stack.data)-items:]
      rt.Stack.data = rt.Stack.data[:len(rt.Stack)-items]+[rtypes.typelst(lst)]
  bins += [['>lst', x]]
  
  def x(rt):
    rt.Stack.push(rtypes.typelst(rt.Stack.pop().data))
  bins += [['composite>lst', x]]
  
  
  ### Error handling
  # Cause error
  def x(rt):
    rt.ded(rt.Stack.pop().data)
  bins += [['ded', x]]
  
  # Return current error state.
  def x(rt):
    rt.Stack.push(rtypes.typeint(rt.Error))
  bins += [['isded', x]]
  
  # Clear error state.
  def x(rt):
    rt.Error = False
  bins += [['unded', x]]
  
  # Set error continuation flag.
  def x(rt):
    rt.Errorcont = bool(rt.Stack.pop().data)
  bins += [['dedcont', x]]
  
  # Break to singlestep flag.
  def x(rt):
    rt.BreakSST = bool(rt.Stack.pop().data)
  bins += [['brksst', x]]
 
  # Traceback depth setting. 
  def x(rt):
    rt.Tracedepth = rt.Stack.pop().data
  bins += [['trace', x]]  

  return bins

# Store all the procedures we know how to make into an extant directory,
# in an extant runtime.
def stoprocs(rt, dir):
  #dir += '.'
  for i in makebinprocs():
    rt.sto([dir]+[i[0]], rtypes.typebinproc(i[1]))
