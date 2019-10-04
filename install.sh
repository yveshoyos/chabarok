#!/bin/bash

PYPI_INDEX=""
BUILDOUT_INDEX=""

HELP=0

#
# We need bash
#
if [ -z "$BASH_VERSION" ]; then
    echo -e "Error: BASH shell is required !"
    exit 1
fi

#
# Create buildout.cfg
#
function check_and_create_buildout_cfg {
    # create a basic buildout.cfg if none is found
    if [ ! -f buildout.cfg ]; then
        if [ -f buildout.cfg.example ]; then
            cp buildout.cfg.example buildout.cfg
        else
            cat >> buildout.cfg <<EOT
[buildout]
extends = buildout.cfg.template

[odoo]
options.admin_passwd = admin
options.db_user = dbuser
options.db_password = dbpassword
options.db_host = 127.0.0.1
EOT
        fi
    fi
}

#
# Install Odoo
#
function install_odoo {
    # TODO: Rework this test
    if [ -d py36 ]; then
        echo "install.sh has already been launched."
        echo "So you must either use bin/buildout to update or launch \"install.sh reset\" to remove all buildout installed items."
        exit -1
    fi
    if [ ! -f bootstrap.py ]; then
        wget https://raw.github.com/buildout/buildout/master/bootstrap/bootstrap.py
    fi

    # create a basic buildout.cfg if none is found
    check_and_create_buildout_cfg

    virtualenv -p python3 py36
    py36/bin/pip install setuptools
    py36/bin/python bootstrap.py
    
    # We install pyusb here it fails with buildout
    py36/bin/pip install $PYPI_INDEX pyusb==1.0.0
    py36/bin/pip install $PYPI_INDEX num2words==0.5.4

    bin/buildout install

    echo
    echo "Your commands should now be available in ./bin"
    echo "Python is in ./py36"
    echo
}

function remove_buildout_files {
    echo "Removing all buidout generated items..."
    echo "    Not removing downloads/ and eggs/ for performance reason."
    rm -rf .installed.cfg
    rm -rf bin/
    rm -rf develop-eggs/
    rm -rf develop-src/
    rm -rf etc/
    rm -rf py36/
    echo "    Done."
}

#
# install project required dependencies
#
function install_dependencies {
    if [ -f install_dependencies.sh ]; then
        sh install_dependencies.sh
    else
        echo "No project specific 'install_dependencies.sh' script found."
    fi
}


#
# Process command line options
#
while getopts "i:h" opt; do
    case $opt in
        i)
            PYPI_INDEX="-i ${OPTARG}"
            BUILDOUT_INDEX="index = ${OPTARG}"
            ;;

        h)
            HELP=1
            ;;

        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;

        :)
            echo "Option -$OPTARG requires an argument." >&2
            exit 1
            ;;
    esac
done

COMMAND=${@:$OPTIND:1}

echo
echo "install.sh - Odoo Installer"
echo "(c) 2013, 2014, 2015, 2016 @cmorisse"
echo "Updated and simplified by Yves HOYOS"

if [[ $COMMAND == "help"  ||  $HELP == 1 ]]; then
    echo "Available commands:"
    echo "  ./install.sh help           Prints this message."
    echo "  ./install.sh [-i ...] odoo  Install Odoo using buildout (prerequisites must be installed)."
    echo "  ./install.sh dependencies   Install dependencies specific to this server."
    echo "  ./install.sh reset          Remove all buildout installed files."
    echo
    echo "Available options:"
    echo "  -i   Pypi Index to use (default=""). See pip install --help"
    echo "  -h   Prints this message"
    echo
    exit
fi

if [[ $COMMAND == "reset" ]]; then
    remove_buildout_files
    exit
elif [[ $COMMAND == "odoo" ]]; then
    install_odoo
    exit
elif [[ $COMMAND == "dependencies" ]]; then
    install_dependencies
    exit
fi

echo "use ./install.sh -h for usage instructions."

