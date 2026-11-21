import os
import pyghidra
pyghidra.start()
from ghidra.base.project import GhidraProject
from ghidra.framework.model import ProjectLocator
from java.io import File

PROJ_LOC = os.path.join(os.environ["GMINFO_REPO_ROOT"], "evidence/ghidra-projects")
PROJ_NAME = "85759599_rh850"

loc = ProjectLocator(PROJ_LOC, PROJ_NAME)
print("exists:", loc.exists())
project = GhidraProject.openProject(PROJ_LOC, PROJ_NAME, True)
root = project.getRootFolder()
print("root files:", list(root.getFiles()))
for f in root.getFiles():
    print(" -", f.getName(), f.getContentType())
