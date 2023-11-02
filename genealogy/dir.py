import os

def createDirIfNeeded(dir):
  if not os.path.exists(dir):
    os.makedirs(dir)
