from fastapi import FastAPI, Request, Body
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

import random, string
import socket
import re
import os
from sys import path
dirname, filename = os.path.split(os.path.abspath(__file__))
FILE_PATH = dirname.split("/")
FILE_PATH[-1]=""
BASE_PATH = "/".join(str(x) for x in FILE_PATH)

import asyncio
#from loguru import logger
from functools import wraps
from asyncio import ensure_future
from starlette.concurrency import run_in_threadpool
from typing import Any, Callable, Coroutine, Optional, Union
from time import sleep
import time,datetime
import urllib.request
import concurrent.futures
import psutil,math
import logging

import paramiko
import subprocess


####
#### Settings ###
####
## DEFAULT VALUE
DEFAULT_PORT = 8877
LOG_LEVEL = logging.INFO
#LOG_LEVEL = logging.DEBUG
LOG_FILE  = './server.log'
OS_USER  = "root"
OS_PASSWORD = "test"

# API SETTINGS
MY_EMAIL = "support@test.com"
MY_URL   = "http://test.com/"
MY_NAME  = "test "
MY_API_VERSION = "0.0.1"
MY_DESCRIPTION = "test api"
MY_TITLE = "test API"

## LOG 
# setup loggers
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
ch = logging.StreamHandler()
#fh = logging.FileHandler(filename='./server.log')
fh = logging.FileHandler(filename=LOG_FILE)
formatter = logging.Formatter(    "%(asctime)s - %(module)s - %(funcName)s - line:%(lineno)d - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(ch) # Show log on monitor
logger.addHandler(fh) # Save log to file

# UTIL
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
    
def checkRE(pats,txt):
    for pat in pats:
        txt = re.search(pat,str(txt))
        if(txt):
            txt = str(txt.group())
        else:
            txt = False
    return txt if txt else False

def space_str_to_list_format(l):
    l = l.split(" ")
    while '' in l:
        l.remove('')
    return l


def valid_ip(address):
    try:
        socket.inet_aton(address)
        return True
    except:
        return False

def run_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, shell=True, encoding='utf-8')
    return result.stdout


def ssh_and_exec_cmd(command, server, server_username, server_pass):
    # SSH to host and execut command
    try:
        LOCK=False
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, username=server_username, password=server_pass, timeout=10)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        ssh_stdin.write(server_pass + "\n")
        result = ssh_stdout.read().decode("utf-8")
        ssh_stdin.flush()
    except:
        print("SSH Connext error")
        result = "Error"
    finally :
        ssh.close()
    return result


async def ssh_twice_cmd(TEST_CMD,FIRST_IP, FIRST_USER, FIRST_PW, SECOND_IP, SECOND_USER, SECOND_PW):
    # SSH to host1 and ssh to host2 and execute command
    result = False
    try:
        first_host = paramiko.SSHClient()
        second_host = paramiko.SSHClient()
        first_host.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        first_host.connect(FIRST_IP, username=FIRST_USER, password=FIRST_PW, timeout=10)
        first_hosttransport = first_host.get_transport()
        dest_addr  = (SECOND_IP, 22) #edited#
        local_addr = (FIRST_IP, 22) #edited#
        first_hostchannel = first_hosttransport.open_channel("direct-tcpip", dest_addr, local_addr)
        second_host.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        second_host.connect(SECOND_IP, sock=first_hostchannel,  username=SECOND_USER, password=SECOND_PW,  timeout=10)

        stdin, stdout, stderr = second_host.exec_command(TEST_CMD)
        result = stdout.read()
    except:
        print("Error: ssh_twice_cmd ")
    finally :
        if second_host:
            second_host.close()
        if first_host:
            first_host.close()
        return result


####
#### task ### (for schedule task)
####
NoArgsNoReturnFuncT = Callable[[], None]
NoArgsNoReturnAsyncFuncT = Callable[[], Coroutine[Any, Any, None]]
NoArgsNoReturnDecorator = Callable[
    [Union[NoArgsNoReturnFuncT, NoArgsNoReturnAsyncFuncT]],
    NoArgsNoReturnAsyncFuncT
]
def repeat_task(
    *,
    seconds: float,
    wait_first: bool = False,
    raise_exceptions: bool = False,
    max_repetitions: Optional[int] = None,
) -> NoArgsNoReturnDecorator:

    def decorator(func: Union[NoArgsNoReturnAsyncFuncT, NoArgsNoReturnFuncT]) -> NoArgsNoReturnAsyncFuncT:
        is_coroutine = asyncio.iscoroutinefunction(func)
        had_run = False

        @wraps(func)
        async def wrapped() -> None:
            nonlocal had_run
            if had_run:
                return
            had_run = True
            repetitions = 0

            async def loop() -> None:
                nonlocal repetitions
                if wait_first:
                    await asyncio.sleep(seconds)
                while max_repetitions is None or repetitions < max_repetitions:
                    try:
                        if is_coroutine:
                            # 以协程方式执行
                            await func()  # type: ignore
                        else:
                            # 以线程方式执行
                            await run_in_threadpool(func)
                        repetitions += 1
                    except Exception as exc:
                        print('执行重复任务异常: {exc}')
                        if raise_exceptions:
                            raise exc
                    await asyncio.sleep(seconds)
            ensure_future(loop())
        return wrapped
    return decorator


#### modules ####
##
## SystemInformation Class
##
class SystemInformation:
    def __init__(self):
        self.info = {}
        self.info['cpu'] = {}
        self.info['memory'] = {}
        self.info['disk'] = {}
        self.info['network'] = {}

    def update(self):
        self.info['boot_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(psutil.boot_time()))
        self.info['cpu']['count'] = psutil.cpu_count(logical=False)
        self.info['cpu']['percent'] = psutil.cpu_percent()
        self.info['cpu']['idle'] = psutil.cpu_times().idle

        memory_info = psutil.virtual_memory()
        self.info['memory']['total'] = self.bytes_to_human_readable(memory_info.total)
        self.info['memory']['available'] = self.bytes_to_human_readable(memory_info.available)
        self.info['memory']['used'] = self.bytes_to_human_readable(memory_info.used)
        self.info['memory']['percent'] = memory_info.percent

        disk_info = psutil.disk_usage('/')
        self.info['disk']['total'] = self.bytes_to_human_readable(disk_info.total)
        self.info['disk']['used'] = self.bytes_to_human_readable(disk_info.used)
        self.info['disk']['free'] = self.bytes_to_human_readable(disk_info.free)
        self.info['disk']['percent'] = disk_info.percent

        io_counters = psutil.net_io_counters()
        self.info['network']['bytes_sent'] = self.bytes_to_human_readable(io_counters.bytes_sent)
        self.info['network']['bytes_recv'] = self.bytes_to_human_readable(io_counters.bytes_recv)

    def bytes_to_human_readable(self, num_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if num_bytes < 1024.0:
                return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024.0

##
## BMC Class
##
class bmc(object):
    def __init__(self,server_ip='172.32.3.155'):
        self.server_ip  = server_ip
        self.sdr = {"TOTAL_PWR":0.0,'CPU0_TEMP': 0.0, 'CPU1_TEMP': 0.0,
                    'FAN0': 0.0, 'FAN1': 0.0, 'FAN2': 0.0, 'FAN3': 0.0, 'FAN4':0.0,'FAN5': 0.0,'FAN6': 0.0}

    def __ipmi_sdr_to_dict(self, ipmi_sdr):
        result={}
        sdr_lines = ipmi_sdr.split("\n")
        for sdr in sdr_lines:
            ss = sdr.replace(" ","")
            ssdr= ss.split('|')
            if(len(ssdr)>= 3):
                result[ssdr[0].upper()]=  float(checkRE(['-*\d+\.*\d*'],ssdr[1]) )# "status":ssdr[2]
        return result

    def update_sdr(self):
        cmd = "ipmitool sdr"
        try:
            ipmi_sdr = ssh_and_exec_cmd(cmd,  self.server_ip, OS_USER, OS_PASSWORD)
            self.sdr = self.__ipmi_sdr_to_dict(ipmi_sdr)
        except:
            print("ERROR, UPDATE SDR ERROR!!")

    def update(self):
        self.update_sdr()


##
## Server Class
##
class my_server(object):

    def __init__(self,ip='172.32.3.155'):
        print("Server IP:",ip)
        self.ip  = ip
        self.bmc = bmc(ip)
        self.last_update = 0
        self.sys_info = SystemInformation()


    ## Public Function
    # ALL
    def get(self):
        result = {}
        result["IP"] = self.ip
        result["BMC"] = self.get_bmc()
        result["LAST_UPDATE"] = self.last_update
        result["SYSTEM"] = self.sys_info.info
        return result

    def update(self):
        self.update_bmc()
        self.update_sys_info()
        self.last_update = time.time()
        return True

    # BMC
    def get_bmc(self):
        return self.bmc.sdr

    def update_bmc(self):
        return self.bmc.update()

    # Sys Info
    def get_sys_info(self):
        return self.sys_info.info

    def update_sys_info(self):
        self.sys_info.update()
        return True


####            ####
#### Fast API   ####
####            ####
RESULT_NOT_FOUND = {"message":"Error , result not found"}
server_ip = get_ip()
serverObj = my_server(server_ip)

## Start APP Service
app = FastAPI(
    title = MY_TITLE,
    description = MY_DESCRIPTION,
    version = MY_API_VERSION,
    contact = {
        "name":  MY_NAME,
        "url":   MY_URL,
        "email": MY_EMAIL,
    },
)
#app.mount("/static", StaticFiles(directory="static"), name="static")

# log
@app.middleware("http")
async def log_requests(request, call_next):
    idem = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    logger.info(f"rid={idem} start request path={request.url.path}")
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}")
    return response

# GET   /
@app.get("/status")
async def status():
    return {"status": "alive"}

# GET /docs
@app.get("/docs", include_in_schema=False)
async def overridden_swagger():
    icon = "https://ebg.test.com/resources/_img/favicon.ico"
    return get_swagger_ui_html(openapi_url="/openapi.json", title="test API", swagger_favicon_url= icon )

##
## Schedule Task
##
# POST  trigger to update datas
@app.on_event('startup')
@repeat_task(seconds=45, wait_first=True)
def repeat_task_aggregate_request_records() -> None:
    # Every 45 sec to update  informations.
    serverObj.update()
    logger.debug(f'== Schedule Task1: Update ',time.time())

@app.on_event('startup')
@repeat_task(seconds=5, wait_first=True)
def schedule_task2() -> None:   # 5 sec schedule task
    serverObj.update_sys_info()
    print('== Schedule Task2: Update ',time.time())

##
## APIs
##
@app.put("/update", tags=["SERVER"])
async def update():
    serverObj.update()
    return True

# GET BMC
@app.get("/bmc", tags=["SERVER"])
def bmc():
    return serverObj.get_bmc()

# GET sys_info
@app.get("/sys_info", tags=["SERVER"])
def sys_info():
    return serverObj.get_sys_info()



if __name__ == "__main__":
    import uvicorn
    logger.debug(f"== API SERVICE START ==")
    logger.info(f"== API SERVICE START ==")
    logger.warning("== API SERVICE START ==")
    uvicorn.run(app='api:app', host="0.0.0.0", port=DEFAULT_PORT, reload=False)
    # http://172.32.3.216:8087/docs
    # http://172.32.3.216:8087
