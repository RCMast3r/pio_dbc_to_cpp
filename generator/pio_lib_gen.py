
# TODO get dbc file from url or local file

Import("env")
import os


try:
    import docker
except ImportError:
    env.Execute("$PYTHONEXE -m pip install docker")
    import docker

try: 
    import validators
except ImportError:
    env.Execute("$PYTHONEXE -m pip install validators")
    import validators

try: 
    import requests
except ImportError:
    env.Execute("$PYTHONEXE -m pip install requests")
    import requests

try: 
    import cantools
except ImportError:
    env.Execute("$PYTHONEXE -m pip install cantools")
    import cantools


import SCons.Action

import tarfile
from platformio import fs

# based on https://github.com/nanopb/nanopb/blob/master/generator/platformio_generator.py


python_exe = env.subst("$PYTHONEXE")
project_dir = env.subst("$PROJECT_DIR")
build_dir = env.subst("$BUILD_DIR")

generated_src_dir = os.path.join(build_dir, "dbcppp", "generated-src")

if not os.path.isdir(generated_src_dir):
    os.makedirs(generated_src_dir)

generated_build_dir = os.path.join(build_dir, "dbcppp", "generated-build")

user_dbc_file = env.subst(env.GetProjectOption("user_dbc_or_sym", ""))
drvname = env.subst(env.GetProjectOption("drvname", ""))



valid_dbc_url = validators.url(user_dbc_file)

dbc_file_name = ""
abs_path_to_dbc = ""
if valid_dbc_url:
    response = requests.get(user_dbc_file)

    if response.status_code == 200:
        # Directory where you want to save the file
        abs_path_to_dbc = os.path.join(generated_src_dir, 'dbcs')
        # Create the directory if it doesn't exist
        os.makedirs(abs_path_to_dbc, exist_ok=True)

        # Extracting the file name from the URL
        dbc_file_name = user_dbc_file.split('/')[-1]

        # Full path to save the file
        abs_path_to_dbc = abs_path_to_dbc
        file_path = os.path.join(abs_path_to_dbc, dbc_file_name)

        if dbc_file_name.endswith('.dbc'):
            pass
        elif dbc_file_name.endswith('.sym'):
        
            db = cantools.database.load_file(os.path.join(abs_path_to_dbc, dbc_file_name))
            generated_dbc_file_dir = os.path.join(generated_src_dir, 'dbcs')
            
            dbc_file_name = os.path.splitext(os.path.basename(dbc_file_name))[0] + ".dbc"
            cantools.database.dump_file(db, os.path.join(generated_dbc_file_dir, dbc_file_name))
    
        # Write the file to the specified directory
        with open(file_path, 'wb') as file:
            file.write(response.content)
            print(f"dbc file '{dbc_file_name}' saved to '{abs_path_to_dbc}'")

    else:
        print("[dbcpio] ERROR: could not download dbc file from specified url")
        exit(1)
else:
    
    dbc_file = fs.match_src_files(project_dir, user_dbc_file)
    rel_dir_dbc_path = os.path.dirname(dbc_file[0])
    abs_path_to_dbc = os.path.join(project_dir, rel_dir_dbc_path)
    dbc_file_name = os.path.basename(dbc_file[0])
    if dbc_file_name.endswith('.dbc'):
        pass
    elif dbc_file_name.endswith('.sym'):
        
        db = cantools.database.load_file(os.path.join(abs_path_to_dbc, dbc_file_name))
        generated_dbc_file_dir = os.path.join(generated_src_dir, 'dbcs')
        os.makedirs(generated_dbc_file_dir, exist_ok=True)
        dbc_file_name = os.path.splitext(os.path.basename(dbc_file_name))[0] + ".dbc"
        cantools.database.dump_file(db, os.path.join(generated_dbc_file_dir, dbc_file_name))
        
    if not len(dbc_file):
        print("[dbcpio] ERROR: No file matched pattern:")
        print(f"user_dbcs: {user_dbc_file}")
        exit(1)



client = docker.from_env()


client.containers.run(
    "ghcr.io/rcmast3r/ccoderdbc:main",
    "./build/coderdbc -rw -dbc /data/"
    + dbc_file_name
    + " -out /out -drvname "
    + drvname,
    group_add=["1000"],
    user=1000,
    volumes=[abs_path_to_dbc + ":/data", generated_src_dir + ":/out"],
    working_dir="/app",
)

env.Append(
    CPPPATH=[
        generated_src_dir,
         os.path.join(generated_src_dir, "inc"),
         os.path.join(generated_src_dir, "lib"),
         os.path.join(generated_src_dir , "conf"),
    ]
)

env.BuildSources(generated_build_dir, generated_src_dir)
