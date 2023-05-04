#!/usr/bin/python3

# CODSWALLOP RPL (a zen garden)
# #####################################################
# Main

# Once a proud ball of deeply interrelated code, rpl.py is
# now merely a stub that launches a copy of the interpreter.

# It's still mine. -kia

from trivia import *
import parse, runtime, rtypes, internals
    
import signal, sys

# Our simple little Ctrl-C handler.  In some cases we want to raise the
# error regardless, but usually we just want the interpreter to catch it
# between evals and trace back.

def catchsigint(signal, frame):
  print('^C')
  ourRT.Break = True
  if ourRT.dieanyway:
    raise KeyboardInterrupt


# Create a new runtime containing just our base types (extra types
# can be added whenever, but the runtime will roll with just these.)
ourtypes = rtypes.baseregistry()
ourRT = runtime.rplruntime(ourtypes)

# Store our internals where the language can get them.
ourRT.sto([INTERNALSDIR], ourRT.firstdir(ourRT.lastobj))
internals.stoprocs(ourRT, INTERNALSDIR)

# And store our version string and base directory.
ourRT.sto(['VERSION'], rtypes.typestr(VERSION))
ourRT.sto(['BASDIR'], rtypes.typestr(BASDIR))

# Drop our commandline argument on the stack as a string, if there is one.
if len(sys.argv)==2:
  ourRT.Stack.push(rtypes.typestr(sys.argv[1]))
else:
  ourRT.Stack.push(rtypes.typestr(""))

# Load and parse the RPL-side bootstrap.
parse.parse(ourRT, LAUNCHCODE)[0].eval(ourRT)

# Turn on Ctrl-C signal handling.
signal.signal(signal.SIGINT, catchsigint)

# And start running.
ourRT.rs()
