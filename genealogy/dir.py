import os

def createDirIfNeeded(dir):
  if not os.path.exists(dir):
    os.makedirs(dir)

def createFileIfNeeded(dir, filename):
  createDirIfNeeded(dir)
  open(os.path.join(dir, filename), 'a').close() # make sure it exists
