import os
import threading
import logging
from ftplib import FTP_TLS
import socket
import time


def setInterval(interval, times = -1):
    # This will be the actual decorator,
    # with fixed interval and times parameter
    def outer_wrap(function):
        # This will be the function to be
        # called
        def wrap(*args, **kwargs):
            stop = threading.Event()

            # This is another function to be executed
            # in a different thread to simulate setInterval
            def inner_wrap():
                i = 0
                while i != times and not stop.isSet():
                    stop.wait(interval)
                    function(*args, **kwargs)
                    i += 1

            t = threading.Timer(0, inner_wrap)
            t.daemon = True
            t.start()
            return stop
        return wrap
    return outer_wrap


class PyFTPclient:
    def __init__(self, host, port, login, passwd, monitor_interval = 30, directory = None):
        self.host = host
        self.port = port
        self.login = login
        self.passwd = passwd
        self.directory = directory
        self.monitor_interval = monitor_interval
        self.ptr = None
        self.max_attempts = 15
        self.waiting = True


    def DownloadFile(self, dst_filename, local_filename = None):
        res = ''
        if local_filename is None:
            local_filename = dst_filename

        with open(local_filename, 'w+b') as f:
            self.ptr = f.tell()

            @setInterval(self.monitor_interval)
            def monitor():
                if not self.waiting:
                    i = f.tell()
                    if self.ptr < i:
                        logging.debug("%d  -  %0.1f Kb/s" % (i, (i-self.ptr)/(1024*self.monitor_interval)))
                        self.ptr = i
                        os.system('clear')
                        print(str(int((float(i)/float(dst_filesize)) * 100)) + '%')
                    else:
                        ftp.close()


            def connect():
                ftp.connect(self.host, self.port)
                ftp.login(self.login, self.passwd)
                ftp.prot_p()
                if self.directory != None:
                    ftp.cwd(self.directory)
                # optimize socket params for download task
                ftp.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                ftp.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 75)
                ftp.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)

            ftp = FTP_TLS()
            ftp.set_pasv(True)

            connect()
            ftp.voidcmd('TYPE I')
            dst_filesize = ftp.size(dst_filename)

            mon = monitor()
            while dst_filesize > f.tell():
                try:
                    connect()
                    self.waiting = False
                    # retrieve file from position where we were disconnected
                    res = ftp.retrbinary('RETR %s' % dst_filename, f.write) if f.tell() == 0 else \
                              ftp.retrbinary('RETR %s' % dst_filename, f.write, rest=f.tell())

                except:
                    self.max_attempts -= 1
                    if self.max_attempts == 0:
                        mon.set()
                        logging.exception('')
                        raise
                    self.waiting = True
                    logging.info('waiting 30 sec...')
                    time.sleep(30)
                    logging.info('reconnect')


            mon.set() #stop monitor
            ftp.close()

            if not res.startswith('226 Transfer complete'):
                logging.error('Downloaded file {0} is not full.'.format(dst_filename))
                os.remove(local_filename)
                return None



            return 1