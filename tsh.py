#!/usr/bin/env python
"""Usage:  tsh [options] [file]

Options:

    -h  --help      print this text and exit.
    
    -t  --test      perform some tests and exit.
    
    -v  --verbose   be verbose (mostly for debugging).

        --version   print version number and exit.
"""
__author__ = 'Ilan Schnell <ilanschnell@gmail.com>'
__copyright__ = '(c) Ilan Schnell, 2007'
__license__ = 'GNU GPL 2'
__version__ = '0.02'

import sys, os, os.path, glob, re, time, getpass,json,netifaces
import subprocess
import netifaces as ni



# The variables can be changed by the command line options:
VERBOSE = False

# Location of main configuration file:
CONFIG = '/etc/config.conf'

allowExec = []
allowSubShell = False

dir = subprocess.call('dir', shell=True)

def readConfig():
    if os.access(CONFIG, os.R_OK):
        exec file(CONFIG) in globals()
    else:
        print "tsh: Warning: Could not open `%s' for reading." % CONFIG


def lineSplit(line):
    """
    Splits a line into its command and options.

    >>> lineSplit(' ls  -l /usr ')
    ('ls', '-l /usr')
    >>> lineSplit(' ls  ')
    ('ls', '')
    >>> lineSplit('  # comment')
    ('', '')
    """
    line = line.strip()
    if not line or line[0]=='#':
        return '', ''
    tmp = line.split(None, 1)
    if tmp:
        return tmp[0], '' if len(tmp)==1 else tmp[1].strip()


class Shell:
    def __init__(self):
        self.alias = {}

    def do_alias(self, args):
        """
        >>> s = Shell()
        >>> s.do_alias("ls='ls -l'")
        >>> s.alias
        {'ls': 'ls -l'}
        >>> s.do_alias('')
        alias ls='ls -l'
        >>> s.do_alias("ls=ls -l")
        tsh: Usage: alias [name='value']
        >>> s.do_unalias("ls")
        >>> s.alias
        {}
        >>> s.do_unalias("ls -l")
        tsh: Usage: unalias name
        """
        m = re.match(r"((\S+)='([^']+)')?$", args)
        if m:
            if m.group(2):
                self.alias[m.group(2)] = m.group(3)
            else:
                for kv in self.alias.iteritems():
                    print "alias %s='%s'" % kv
        else:
            print "tsh: Usage: alias [name='value']"
            
    def do_unalias(self, args):
        m = re.match(r"(\S+)?$", args)
        if m:
            del self.alias[m.group(1)]
        else:
            print "tsh: Usage: unalias name"
            
    def do_show_commands(self, args):
        if args=='':
            for kv in sorted(self.commands().items()):
                print "    %-15s %s " % kv
        else:
            print "tsh: Usage: commands"

    def do_dt(self,args):
        m = re.match(r"((\S+)='([^']+)')?$", args)
        print(time.strftime("%Y%m%d%H%M%S"))


    def do_ud(self, args):
        m = re.match(r"((\S+)='([^']+)')?$", args)
        uname = getpass.getuser()
        print 'User =' ,uname
        os.system("id")
        os.system("ls -li /usr/local/bin")
    def do_groups(self,args):
        m = re.match(r"((\S+)='([^']+)')?$", args)


    def do_pwd(self,args):
        m = re.match(r"((\S+)='([^']+)')?$", args)
        print(os.getcwd())


    def do_ifconfig(self, args):
        m = re.match(r"((\S+)='([^']+)')?$", args)
        ifconfig = """
            eth0      Link encap:Ethernet  HWaddr 08:00:27:3a:ab:47
                      inet addr:192.168.98.157  Bcast:192.168.98.255  Mask:255.255.255.0
                      inet6 addr: fe80::a00:27ff:fe3a:ab47/64 Scope:Link
                      UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
                      RX packets:189059 errors:0 dropped:0 overruns:0 frame:0
                      TX packets:104380 errors:0 dropped:0 overruns:0 carrier:0
                      collisions:0 txqueuelen:1000
                      RX bytes:74213981 (74.2 MB)  TX bytes:15350131 (15.3 MB)"""

        info = {
            'eth_port': '',
            'ip_address': '',
            'broadcast_address': '',
            'mac_address': '',
            'net_mask': '',
            'up': False,
            'running': False,
            'broadcast': False,
            'multicast': False,
        }

        print info




    def do_cd(self, args):
        """
        >>> s = Shell()
        >>> s.do_cd('/')
        >>> os.getcwd()
        '/'
        >>> s.do_cd('a b')
        tsh: Usage: cd [path]
        """
        m = re.match(r"(\S+)?$", args)
        if m:
            path = m.group(1) if m.group(1) else '~'
            try: os.chdir(os.path.expanduser(path))
            except: print "tsh: cd: `%s' No such directory" % path
        else:
            print "tsh: Usage: cd [path]"



    def execute_file(self, filename):
        if VERBOSE: print "tsh: executing file `%s':" % filename
        for line in file(filename):
            self.execute(line)
            
    def execute(self, line):
        line = line.strip()
        cmd, args = lineSplit(line)
        if not cmd:
            return
        f = self.rawExec
        if self.alias.has_key(cmd):
            alias = self.alias[cmd]
            line = alias+' '+args
            if lineSplit(alias)[0] != cmd:
                f = self.execute
        f(line)
            
    def rawExec(self, line):
        if VERBOSE: print "tsh: executing: %s   " % line,
        cmd, args = lineSplit(line)
        funcname = "do_" + cmd
        if hasattr(self, funcname):
            if VERBOSE: print "(shell builtin)"
            func = getattr(self, funcname)
            try:
                func(args)
            except:
                print "tsh: Error in line `%s'." % line
        elif cmd in allowExec:
            if VERBOSE: print "(os.spawn)"
            os.spawnvp(os.P_WAIT, cmd, line.split())
        else:
            if VERBOSE: print "(on subshell)"
            if allowSubShell:
                os.system(line)
            else:
                print "tsh: `%s' Permission denied." % line

    def commands(self):
        """
        >>> s = Shell()
        >>> s.commands()['cd']
        'builtin'
        """
        res={'exit': 'builtin'}
        for var in vars(self.__class__):
            if var.startswith('do_'):
                res[var[3:]] = 'builtin'
        for c in allowExec:
            res[c] = 'OS'
        for k, v in self.alias.items():
            tmp = "aliased '%s'" % v
            if res.has_key(k): res[k] += ", "+tmp
            else: res[k] = tmp
        return res
    
    def completions(self):
        res = self.commands()
        for f in glob.glob('*'):
            res[f] = True
        return res


def repl():
    try:
        import readline
        has_readline = True
    except ImportError:
        has_readline = False
    
    if has_readline:
        historyFile = os.path.expanduser('~/.tsh-history')
        if os.access(historyFile, os.W_OK):
            readline.read_history_file(historyFile)
            readline.set_history_length(100)
        else:
            print "tsh: Could not open `%s' for writing." % historyFile
            try:
                file(historyFile, 'w').close()
                print "`%s' created." % historyFile
            except IOError:
                print "tsh: Warning: Creating `%s' failed." % historyFile
                historyFile = None

        readline.parse_and_bind("tab: complete")

        words = {}
        def completer(prefix, index):
            try:
                return [w for w in words if w.startswith(prefix)][index]
            except IndexError:
                return None

        readline.set_completer(completer)
    
    shell = Shell()

    rcFile = os.path.expanduser('~/.tshrc')
    if os.access(rcFile, os.R_OK):
        shell.execute_file(rcFile)
    
    while True:
        words = shell.completions()
        try:
            line = raw_input(os.getcwd()+' tsh> ')
            if line.strip() == 'exit':
                break
            if has_readline and historyFile:
                readline.write_history_file(historyFile)
        except EOFError:
            print 'exit'
            break
        shell.execute(line)


def usage():
    print __doc__
    sys.exit(0)


def test():
    print 'tsh: Performing tests ...'
    import doctest
    doctest.testmod()
    sys.exit(0)
    

if __name__ == '__main__':
    import getopt
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'htv',
                                   ['help', 'test', 'verbose', 'version'])
    except getopt.GetoptError:
        usage()
        
    for o, v in opts:
        if o in ('-h', '--help'): usage()
        if o in ('-t', '--test'): test()
        if o in ('-v', '--verbose'): VERBOSE = True
        if o=='--version':
            print 'tsh: version', __version__
            sys.exit(0)
    
    readConfig()
    if VERBOSE:
        print "tsh: allowExec = %r" % allowExec
        print "tsh: allowSubShell = %r" % allowSubShell

    if len(args)==0:
        # Run interactively
        repl()
    elif len(args)==1:
        # Interpret file
        filename = args[0]
        if os.access(filename, os.R_OK):
            Shell().execute_file(args[0])
        else:
            print "tsh: Could not open `%s' for reading." % filename
    else:
        usage()


# Local Variables:
# mode:python
# End:
