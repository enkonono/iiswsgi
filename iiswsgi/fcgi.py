import os
import logging
import multiprocessing
import subprocess
import argparse

from xml.dom import minidom

logger = logging.getLogger('iiswsgi.fcgi')

app_attr_defaults_init = dict(
    fullPath='%SystemDrive%\\Python27\\python.exe',
    arguments='-u %SystemDrive%\\Python27\\Scripts\\iiswsgi-script.py',
    activityTimeout='600', requestTimeout='600', idleTimeout='604800',
    monitorChangesTo='{SystemDrive}\\Scripts\\iiswsgi-script.py',
    maxInstances=multiprocessing.cpu_count())


def get_web_config_apps(web_config):
    doc = minidom.parse(web_config)
    for fcgi in doc.getElementsByTagName("fastCgi"):
        for app in fcgi.getElementsByTagName("application"):
            yield dict((key, value) for key, value in app.attributes.items())


def install_fcgi_app(appcmd_exe=None,
                     web_config=None,
                     app_attr_defaults=app_attr_defaults_init,
                     **application_attrs):
    """
    Install an IIS FastCGI application.

    Since registering FastCGI applications doesn't work through
    `web.config`, this script will install the FastCGI app globally
    into IIS.  The attributes for the FCGI application may be given in
    a `web.config` file or through kwargs.

    If a `web.config` file is used, the `app_attr_defaults` will not
    be used but kwargs will still override `web.config` attributes.
    If a `web_config` argument is not passed, if the `os.getcwd()` or
    the directory in the `APPL_PHYSICAL_PATH` environment variable
    contains a `web.config` file, then that file will be used.  If the
    `web.config` file selected contains
    `configuration/system.webServer/fastCgi/application` elements,
    then IIS FCGI applications will be installed for all of them with
    attributes overridden by kwargs.  If the `web.config` file
    selected contains no such elements then the `app_attr_defaults`
    and kwargs will be used as described below.

    Pass `web_config=False` to disable using a `web.config` file and
    use `app_attr_defaults`.  In that case, kwargs override
    `app_attr_defaults`.

    http://www.iis.net/ConfigReference/system.webServer/fastCgi/application
    for more details on the valid attributes and their affects.
    """
    if appcmd_exe is None:
        appcmd_exe = '{WINDIR}\\System32\\inetsrv\\appcmd.exe'
        if 'IIS_BIN' in os.environ:
            # IIS Express
            # under WebPI at least, this is only set when using IIS Express
            appcmd_exe = '{PROGRAMFILES}\\IIS Express\\appcmd.exe'
    try:
        appcmd_exe = appcmd_exe.format(**os.environ)
    except KeyError:
        logger.exception('Could not find: {0}'.format(appcmd_exe))
        return

    if web_config is None:
        # Search for default web.config
        if os.path.exists('web.config'):
            web_config = 'web.config'
        elif 'APPL_PHYSICAL_PATH' in os.environ:
            web_config = os.path.join(
                os.environ['APPL_PHYSICAL_PATH'], 'web.config')

    if web_config:
        apps = get_web_config_apps(web_config)
    else:
        apps = [app_attr_defaults.copy()]

    for app_attrs in apps:
        # Override with kwargs
        app_attrs.update(application_attrs)
        # format attributes for appcmd.exe
        appcmd_args = ",".join(
            "{0}='{1}'".format(*item) for item in app_attrs.iteritems())

        appcmd_cmd = (
            appcmd_exe, "set", "config", "-section:system.webServer/fastCgi",
            '/+[{0}]'.format(appcmd_args), '/commit:apphost')
        logger.info('Installing IIS FastCGI application: {0!r}'.format(
            ' '.join(appcmd_cmd)))
        if os.path.exists(appcmd_exe):
            subprocess.check_call(appcmd_cmd)
        else:
            logger.info('IIS AppCmd.exe does not exist: {0}'.format(
                appcmd_exe))


def install_fcgi_app_console(args=None):
    """
    Install an IIS FastCGI application.

    Adds a FastCGI Application to the IIS global config.  Many of the
    options are used as attributes for the <fastCgi><application>
    element installed.  See
    http://www.iis.net/ConfigReference/system.webServer/fastCgi/application
    for more details on the valid attributes and their affects.
    """
    logging.basicConfig(level=logging.INFO)
    options, args = install_fcgi_app_parser.parse_args(args=args)
    install_fcgi_app(**options.__dict__)


install_fcgi_app_parser = argparse.ArgumentParser(
    description=install_fcgi_app_console.__doc__,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
install_fcgi_app_parser.add_argument(
    "-m", "--monitor-changes", metavar="PATH",
    default=app_attr_defaults_init['monitorChangesTo'], help="""\
The path to a file which IIS will monitor and restart the FastCGI \
process when the file is modified.""")
install_fcgi_app_parser.add_argument(
    "-n", "--max-instances", type=int,
    default=app_attr_defaults_init['maxInstances'], help="""\
The maximum number of FastCGI processes which IIS will launch.  For a \
production deployment, it's usually best to set this to \
%%NUMBER_OF_PROCESSORS%%.""")
install_fcgi_app_parser.add_argument(
    "-t", "--activity-timeout", type=int,
    default=app_attr_defaults_init['activityTimeout'], help="""\
Specifies the maximum time, in seconds, that a FastCGI process can \
take to process. Acceptable values are in the range from 10 through \
3600.""")
install_fcgi_app_parser.add_argument(
    "-i", "--idle-timeout", type=int,
    default=app_attr_defaults_init['idleTimeout'], help="""\
Specifies the maximum amount of time, in seconds, that a FastCGI \
process can be idle before the process is shut down. Acceptable values \
are in the range from 10 through 604800.""")
install_fcgi_app_parser.add_argument(
    "-r", "--request-timeout", type=int,
    default=app_attr_defaults_init['requestTimeout'],
    help="""\
Specifies the maximum time, in seconds, that a FastCGI process request \
can take. Acceptable values are in the range from 10 through 604800. \
[default: %(default)s]""")
install_fcgi_app_parser.add_argument(
    "-f", "--full-path", metavar="EXECUTABLE",
    default=app_attr_defaults_init['fullPath'], help="""\
The path to the executable to be launched as the FastCGI process by \
IIS.  This is usually the path to the Python executable.""")
install_fcgi_app_parser.add_argument(
    "-a", "--arguments", default=app_attr_defaults_init['arguments'],
    help="""\
The arguments to be given the executable when invoked as the FastCGI \
process by IIS.""")